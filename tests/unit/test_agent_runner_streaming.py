"""Testes do modo verboso do AgentRunner — streaming de eventos no TuringProgressBus."""

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, Self

import pytest

from bombe_code.agents.models import AgentDefinition
from bombe_code.agents.runner import AgentRunner
from bombe_code.turing.progress import BUS, ProgressEvent


class _FakeEventsCM:
    def __init__(self, events: list[Any]) -> None:
        self._events = events

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    def __aiter__(self) -> AsyncIterator[Any]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[Any]:
        for ev in self._events:
            yield ev


class FakeStreamAgent:
    """Agente falso com API de streaming de eventos do pydantic-ai 2.x."""

    def __init__(self, events: list[Any]) -> None:
        self._events = events

    def run_stream_events(self, prompt: str, usage_limits: Any = None) -> _FakeEventsCM:
        return _FakeEventsCM(self._events)


class FakeFactory:
    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def create_agent(self, **kwargs: Any) -> Any:
        return self._agent


def _make_definition() -> AgentDefinition:
    return AgentDefinition(
        handle="@meira",
        name="Silvio Meira",
        role="Viability Analyst",
        country="Brasil",
        origin="BRAZIL",
        historical_homage="test",
        primary_stage="DISCUSS",
        phase="UPSTREAM",
        required_inputs=[],
        expected_outputs=[],
        skills_allowed=[],
        system_prompt="teste",
    )


async def _consumir(destino: list[ProgressEvent], esperados: int | None) -> None:
    async for evento in BUS.stream():
        destino.append(evento)
        if esperados is not None and len(destino) >= esperados:
            break


def _rodar_em_thread(fn, *args):
    import anyio

    return anyio.to_thread.run_sync(lambda: fn(*args))


@pytest.fixture(autouse=True)
def _modo_verboso():
    BUS.set_verbosity("verbose")
    yield
    BUS.set_verbosity("verbose")


def test_runner_verboso_publica_texto_pensamento_e_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_ai import AgentRunResultEvent
    from pydantic_ai.messages import (
        FunctionToolCallEvent,
        FunctionToolResultEvent,
        PartDeltaEvent,
        TextPartDelta,
        ThinkingPartDelta,
        ToolCallPart,
    )

    monkeypatch.delenv("BOMBE_TUI_RUNNING", raising=False)

    fake_result = SimpleNamespace(output="Parecer final APROVADO", usage=lambda: None)
    eventos = [
        PartDeltaEvent(index=0, delta=ThinkingPartDelta(content_delta="pensando na viabilidade")),
        PartDeltaEvent(index=1, delta=TextPartDelta(content_delta="Analisando ")),
        PartDeltaEvent(index=1, delta=TextPartDelta(content_delta="a demanda")),
        FunctionToolCallEvent(
            part=ToolCallPart(
                tool_name="write_file",
                args='{"path": "docs/saida.md", "content": "# conteudo"}',
                tool_call_id="t1",
            )
        ),
        FunctionToolResultEvent(
            part=ToolCallPart(
                tool_name="write_file",
                args='{"path": "docs/saida.md", "content": "# conteudo"}',
                tool_call_id="t1",
            ),
            content="arquivo gravado com sucesso",
        ),
        AgentRunResultEvent(result=fake_result),
    ]
    runner = AgentRunner(_make_definition(), FakeFactory(FakeStreamAgent(eventos)))
    recebidos: list[ProgressEvent] = []

    async def cenario() -> None:
        task = asyncio.create_task(_consumir(recebidos, esperados=7))
        await asyncio.sleep(0.05)
        res = await _rodar_em_thread(runner.run, "avalie a demanda")
        assert res.success
        assert res.output == "Parecer final APROVADO"
        await asyncio.wait_for(task, timeout=5)

    asyncio.run(cenario())

    tipos = [e.type for e in recebidos]
    assert "thinking_delta" in tipos
    assert "text_delta" in tipos
    assert "tool_call" in tipos
    assert "tool_result" in tipos
    # Tool de gravação ganha evento dedicado com o arquivo alvo
    assert "file_write" in tipos
    fw = next(e for e in recebidos if e.type == "file_write")
    assert "docs/saida.md" in fw.text
    texto = "".join(e.text for e in recebidos if e.type == "text_delta")
    assert texto == "Analisando a demanda"
    assert any(e.type == "thinking_delta" and "viabilidade" in e.text for e in recebidos)


def test_runner_quiet_publica_apenas_anuncios(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic_ai import AgentRunResultEvent
    from pydantic_ai.messages import PartDeltaEvent, TextPartDelta

    monkeypatch.delenv("BOMBE_TUI_RUNNING", raising=False)
    BUS.set_verbosity("quiet")

    fake_result = SimpleNamespace(output="done", usage=lambda: None)
    eventos = [
        PartDeltaEvent(index=0, delta=TextPartDelta(content_delta="delta ignorado no quiet")),
        AgentRunResultEvent(result=fake_result),
    ]
    runner = AgentRunner(_make_definition(), FakeFactory(FakeStreamAgent(eventos)))
    recebidos: list[ProgressEvent] = []

    async def cenario() -> None:
        task = asyncio.create_task(_consumir(recebidos, esperados=None))
        await asyncio.sleep(0.05)
        res = await _rodar_em_thread(runner.run, "executa")
        assert res.success
        await asyncio.sleep(0.1)
        task.cancel()

    asyncio.run(cenario())
    assert all(e.type not in ("text_delta", "thinking_delta") for e in recebidos)


def test_runner_faz_fallback_sincrono_sem_api_de_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOMBE_TUI_RUNNING", raising=False)

    class SyncOnlyAgent:
        def run_sync(self, prompt: str, usage_limits: Any = None) -> Any:
            return SimpleNamespace(output="resposta síncrona", usage=lambda: None)

    runner = AgentRunner(_make_definition(), FakeFactory(SyncOnlyAgent()))
    res = runner.run("prompt")
    assert res.success
    assert res.output == "resposta síncrona"


def test_tool_result_do_pydantic_real_extrai_de_part_content(monkeypatch):
    """pydantic-ai real: ev.content vem None e o conteúdo vive em ev.part.content
    (o bug do '← None' no make-books)."""
    from bombe_code.agents.runner import AgentRunner

    monkeypatch.delenv("BOMBE_TUI_RUNNING", raising=False)

    from pydantic_ai import AgentRunResultEvent
    from pydantic_ai.messages import FunctionToolResultEvent, ToolReturnPart

    fake_result = SimpleNamespace(output="ok", usage=lambda: None)
    eventos = [
        FunctionToolResultEvent(
            part=ToolReturnPart(
                tool_name="read_project_file",
                content="conteúdo REAL do arquivo",
                tool_call_id="t1",
            ),
            content=None,  # pydantic-ai real: None aqui!
        ),
        AgentRunResultEvent(result=fake_result),
    ]
    runner = AgentRunner(_make_definition(), FakeFactory(FakeStreamAgent(eventos)))
    recebidos: list[ProgressEvent] = []

    async def cenario() -> None:
        task = asyncio.create_task(_consumir(recebidos, esperados=2))
        await asyncio.sleep(0.05)
        res = await _rodar_em_thread(runner.run, "prompt")
        assert res.success
        await asyncio.wait_for(task, timeout=5)

    asyncio.run(cenario())
    resultados = [e for e in recebidos if e.type == "tool_result"]
    assert resultados, "resultado da tool não foi publicado"
    assert "conteúdo REAL do arquivo" in resultados[0].text
    assert resultados[0].text != "None"
