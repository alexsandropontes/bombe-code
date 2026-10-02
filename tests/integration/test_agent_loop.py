"""Integration F6 agent-loop — loop/harness em storage REAL + adaptador injetado.

Cobre PRD F4 (agent-loop): CA1-CA4, RN1 (loop/maxSteps/tasks), RN2 (persistência
incremental), RN3 (doom-loop), RN4 (retry/abort), RN5 (compact/fork/revert).
"""

import threading
from pathlib import Path

import pytest

from bombe_code.permissions.rules import PermissionService, Rule
from bombe_code.session import crud
from bombe_code.session.lifecycle import compact_session, fork_session, revert_session
from bombe_code.session.loop import run_prompt, tool_signature
from bombe_code.session.models import TextPart, ToolPart
from bombe_code.tools.registry import builtin_registry

pytestmark = pytest.mark.integration


class ScriptedAdapter:
    provider = "openai"
    model = "scripted/test"

    def __init__(self, steps):
        self.steps = [list(step) for step in steps]
        self.calls: list[dict] = []
        self.stream_calls = 0

    def stream(self, messages, tools, system):
        self.stream_calls += 1
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        if not self.steps:
            raise AssertionError("passo de stream inesperado")
        return iter(self.steps.pop(0))


class FlakyAdapter(ScriptedAdapter):
    def __init__(self, steps, failures=1):
        super().__init__(steps)
        self.failures = failures

    def stream(self, messages, tools, system):
        if self.failures > 0:
            self.failures -= 1
            self.stream_calls += 1
            raise ConnectionError("transitoria")
        return super().stream(messages, tools, system)


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    session = crud.create_session(title="loop", directory=str(tmp_path))
    return session


def test_ca1_prompt_sem_tools_finaliza_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    session = _setup(tmp_path, monkeypatch)
    adapter = ScriptedAdapter(
        [[{"type": "text-delta", "text": "Ola!"}, {"type": "finish", "reason": "stop"}]]
    )

    # Act
    out = run_prompt(session, "oi", adapter=adapter, registry=builtin_registry())

    # Assert
    assert out == "Ola!"
    assistants = [m for m in crud.load_messages(session.id) if m.role == "assistant"]
    assert len(assistants) == 1
    text_parts = [
        p
        for p in crud.load_parts(session.id)
        if isinstance(p, TextPart) and p.message_id == assistants[0].id
    ]
    assert len(text_parts) == 1
    assert text_parts[0].text == "Ola!"


def test_ca2_tool_call_continua_ate_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    session = _setup(tmp_path, monkeypatch)
    alvo = tmp_path / "arquivo.txt"
    alvo.write_text("conteudo aqui", encoding="utf-8")
    adapter = ScriptedAdapter(
        [
            [
                {
                    "type": "tool-call",
                    "id": "call_1",
                    "name": "read",
                    "arguments": {"path": str(alvo)},
                },
                {"type": "finish", "reason": "tool-calls"},
            ],
            [{"type": "text-delta", "text": "lido!"}, {"type": "finish", "reason": "stop"}],
        ]
    )

    # Act
    out = run_prompt(session, "leia", adapter=adapter, registry=builtin_registry())

    # Assert
    assert out == "lido!"
    tool_parts = [p for p in crud.load_parts(session.id) if isinstance(p, ToolPart)]
    assert len(tool_parts) == 1
    assert tool_parts[0].state == "completed"
    assert "conteudo aqui" in tool_parts[0].output
    # 2º turno recebe histórico com resultado da tool (formato openai)
    assert any(m.get("role") == "tool" for m in adapter.calls[1]["messages"])


def test_ca3_doom_loop_exige_permissao_e_nega(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange — 4 chamadas idênticas; permissão rejeitada na 3ª
    session = _setup(tmp_path, monkeypatch)
    evento = {
        "type": "tool-call",
        "id": "call_x",
        "name": "shell",
        "arguments": {"command": "echo doom"},
    }
    passo = [evento, {"type": "finish", "reason": "tool-calls"}]
    adapter = ScriptedAdapter([passo, passo, passo, passo])
    service = PermissionService(
        rules=[Rule(permission="bash", pattern="*", action="allow")], approved=[]
    )
    sig = tool_signature(evento)
    threading.Timer(0.05, lambda: service.reply("loop", sig, "reject")).start()

    # Act
    run_prompt(
        session,
        "repita",
        adapter=adapter,
        registry=builtin_registry(),
        permissions=service,
    )

    # Assert — apenas 2 execuções reais; a 3ª foi bloqueada por permissão
    tool_parts = [
        p
        for p in crud.load_parts(session.id)
        if isinstance(p, ToolPart) and p.state == "completed"
    ]
    assert len(tool_parts) == 2
    assert adapter.steps, "nao devia consumir o 4º turno"


def test_ca4_abort_sem_part_running_orfao(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    session = _setup(tmp_path, monkeypatch)
    adapter = ScriptedAdapter(
        [
            [
                {"type": "text-delta", "text": "parcial"},
                {
                    "type": "tool-call",
                    "id": "call_a",
                    "name": "shell",
                    "arguments": {"command": "echo nunca"},
                },
                {"type": "finish", "reason": "stop"},
            ]
        ]
    )
    contador = {"n": 0}

    def abort() -> bool:
        contador["n"] += 1
        return contador["n"] >= 3

    # Act
    run_prompt(
        session,
        "x",
        adapter=adapter,
        registry=builtin_registry(),
        abort=abort,
    )

    # Assert
    parts = crud.load_parts(session.id)
    assert any(isinstance(p, TextPart) and p.text == "parcial" for p in parts)
    assert not any(
        isinstance(p, ToolPart) and p.state == "running" for p in parts
    ), "nenhum running orfao apos abort"


def test_rn4_retry_em_erro_transitorio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    session = _setup(tmp_path, monkeypatch)
    adapter = FlakyAdapter(
        [[{"type": "text-delta", "text": "ok"}, {"type": "finish", "reason": "stop"}]],
        failures=1,
    )

    # Act
    out = run_prompt(session, "oi", adapter=adapter, registry=builtin_registry())

    # Assert
    assert out == "ok"
    assert adapter.stream_calls == 2


def test_rn1_subtask_cria_sessao_filha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    session = _setup(tmp_path, monkeypatch)
    adapter = ScriptedAdapter(
        [
            [
                {
                    "type": "tool-call",
                    "id": "call_t",
                    "name": "task",
                    "arguments": {"prompt": "faz a parte 2"},
                },
                {"type": "finish", "reason": "tool-calls"},
            ],
            [{"type": "text-delta", "text": "feito!"}, {"type": "finish", "reason": "stop"}],
            [{"type": "text-delta", "text": "tudo pronto"}, {"type": "finish", "reason": "stop"}],
        ]
    )

    # Act
    out = run_prompt(session, "delega", adapter=adapter, registry=builtin_registry())

    # Assert
    assert out == "tudo pronto"
    filhas = [s for s in crud.list_sessions() if s.parent_id == session.id]
    assert len(filhas) == 1
    tool_parts = [p for p in crud.load_parts(session.id) if isinstance(p, ToolPart)]
    assert tool_parts[0].state == "completed"
    assert "feito!" in tool_parts[0].output


def test_rn1_max_steps_limita_turnos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange — adaptador sempre pede tool; nunca dá stop
    session = _setup(tmp_path, monkeypatch)
    arquivo = tmp_path / "x.txt"
    arquivo.write_text("1", encoding="utf-8")
    passo = [
        {
            "type": "tool-call",
            "id": "c",
            "name": "read",
            "arguments": {"path": str(arquivo)},
        },
        {"type": "finish", "reason": "tool-calls"},
    ]
    adapter = ScriptedAdapter([passo, passo, passo, passo, passo])

    # Act
    run_prompt(
        session,
        "loop infinito",
        adapter=adapter,
        registry=builtin_registry(),
        max_steps=3,
    )

    # Assert — parou exatamente em 3 turnos, sem consumir o resto
    assert len(adapter.calls) == 3
    assert len(adapter.steps) == 2


def test_rn5_revert_fork_compact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Arrange
    session = _setup(tmp_path, monkeypatch)
    mids = []
    for i in range(3):
        from bombe_code.session.models import Message

        msg = Message(session_id=session.id, role="user")
        crud.save_message(msg)
        crud.save_part(session.id, TextPart(message_id=msg.id, text=f"m{i}"))
        mids.append(msg.id)

    # Act — revert para a 1ª mensagem
    revert_session(session.id, mids[0])
    restantes = crud.load_messages(session.id)
    # Assert
    assert [m.id for m in restantes] == [mids[0]]

    # Act — fork
    filha = fork_session(session.id, at_message_id=mids[0])
    assert filha.parent_id == session.id
    assert [m.id for m in crud.load_messages(filha.id)] == [mids[0]]

    # Act — compact
    compact_session(session.id, "resumo da conversa")
    partes = crud.load_parts(session.id)
    assert any(getattr(p, "type", "") == "compaction" for p in partes)
