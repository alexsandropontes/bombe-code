"""Testes do _run_orchestrator_with_stream — transcript ao vivo da TUI consumindo o bus."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from bombe_code.tui.commands import _run_orchestrator_with_stream
from bombe_code.turing.progress import BUS


class FakeStatic:
    """Stub imune a ausência de App: registra o conteúdo para inspeção."""

    def __init__(self, conteudo: Any) -> None:
        self.content = conteudo

    def update(self, conteudo: Any) -> None:
        self.content = conteudo


class FakeChat:
    def __init__(self) -> None:
        self.mounted: list[Any] = []

    async def mount(self, widget: Any) -> None:
        self.mounted.append(widget)

    def criar_static(self, conteudo: Any) -> FakeStatic:
        return FakeStatic(conteudo)

    def atualizar_widget(self, widget: Any, conteudo: Any) -> None:
        widget.content = conteudo


@pytest.fixture(autouse=True)
def _modo_verboso():
    BUS.set_verbosity("verbose")
    yield
    BUS.set_verbosity("verbose")


def test_stream_verboso_renderiza_anuncios_e_transcrição():
    chat = FakeChat()

    def orchestrator_fake() -> dict[str, Any]:
        BUS.publish("stage_start", text="🎬 Etapa DISCUSS iniciada")
        BUS.publish("thinking_delta", agent="@meira", text="analisando viabilidade")
        BUS.publish("text_delta", agent="@meira", text="Parecer: ")
        BUS.publish("text_delta", agent="@meira", text="viável")
        BUS.publish("tool_call", agent="@meira", text="write_file")
        BUS.publish("stage_end", text="✓ Etapa DISCUSS concluída")
        return {"success": True}

    async def cenario() -> None:
        res = await _run_orchestrator_with_stream(chat, orchestrator_fake)
        assert res == {"success": True}

    asyncio.run(cenario())

    textos = [
        str(getattr(w, "renderable", None) or getattr(w, "content", "")) for w in chat.mounted
    ]
    joined = "\n".join(str(t) for t in textos)
    assert "Etapa DISCUSS iniciada" in joined
    assert "Etapa DISCUSS concluída" in joined
    # Transcript do agente com deltas acumulados
    assert any("Parecer: viável" in str(t) for t in textos)
    assert any("analisando viabilidade" in str(t) for t in textos)
    assert any("write_file" in str(t) for t in textos)


def test_stream_quiet_nao_renderiza_deltas_apenas_anuncios():
    chat = FakeChat()
    BUS.set_verbosity("quiet")

    def orchestrator_fake() -> dict[str, Any]:
        BUS.publish("text_delta", agent="@meira", text="delta oculto")
        BUS.publish("veto_rework", text="🔁 Retrabalho 1/2 com @edith")
        BUS.publish("stage_end", text="✓ Etapa concluída")
        return {"success": False, "error": "x"}

    async def cenario() -> None:
        await _run_orchestrator_with_stream(chat, orchestrator_fake)

    asyncio.run(cenario())

    joined = "\n".join(str(getattr(w, "content", "")) for w in chat.mounted)
    assert "delta oculto" not in joined
    assert "Retrabalho 1/2" in joined
    assert "Etapa concluída" in joined


def test_resultado_do_orquestrador_e_integrado_mesmo_com_erro():
    chat = FakeChat()

    def orchestrator_fake() -> dict[str, Any]:
        BUS.publish("stage_failed", text="✗ falhou")
        return {"success": False, "error": "boom"}

    async def cenario() -> None:
        res = await _run_orchestrator_with_stream(chat, orchestrator_fake)
        assert res["success"] is False
        assert res["error"] == "boom"

    asyncio.run(cenario())


def test_conteudo_llm_com_markup_nao_quebra_renderizacao():
    """Regressão do crash do make-books: LLM emitindo '[magenta]'/'[/magenta]'
    no stream/args/resultado NÃO pode derrubar o render (Rich Text é imune)."""
    chat = FakeChat()

    def orchestrator_fake() -> dict[str, Any]:
        BUS.publish("text_delta", agent="@valim", text="veja [magenta]cor[/magenta] e ")
        BUS.publish(
            "tool_call",
            agent="@valim",
            text="write_file",
            args='{"content": "[/magenta] injetado"}',
        )
        BUS.publish("tool_result", agent="@valim", text="[/magenta] saída estranha")
        BUS.publish("stage_end", text="✓ concluído sem explosão")
        return {"success": True}

    async def cenario() -> None:
        res = await _run_orchestrator_with_stream(chat, orchestrator_fake)
        assert res["success"] is True

    asyncio.run(cenario())
    joined = "\n".join(
        str(getattr(w, "renderable", None) or getattr(w, "content", "")) for w in chat.mounted
    )
    assert "[magenta]cor" in joined  # literal preservado, não interpretado
    assert "[/magenta] injetado" in joined
    assert "saída estranha" in joined


def test_linearidade_pensamento_nunca_volta_atras():
    """REGRA DA TELA LINEAR: pensar → agir → pensar de novo abre um bloco NOVO
    abaixo da última ação. NUNCA reescreve o pensamento anterior lá em cima."""
    chat = FakeChat()

    def orchestrator_fake() -> dict[str, Any]:
        BUS.publish("thinking_delta", agent="@unclebob", text="pensamento ANTIGO do review ")
        BUS.publish(
            "tool_call", agent="@unclebob", text="read_project_file", args='{"path":"x.py"}'
        )
        BUS.publish("tool_result", agent="@unclebob", text="código lido")
        BUS.publish("thinking_delta", agent="@unclebob", text="pensamento NOVO após agir")
        return {"success": True}

    async def cenario() -> None:
        await _run_orchestrator_with_stream(chat, orchestrator_fake)

    asyncio.run(cenario())

    textos = [
        str(getattr(w, "renderable", None) or getattr(w, "content", "")) for w in chat.mounted
    ]
    # Ordem linear: pensamento antigo → ferramenta → resultado → pensamento novo
    idx_antigo = next(i for i, t in enumerate(textos) if "ANTIGO" in t)
    idx_tool = next(i for i, t in enumerate(textos) if "read_project_file" in t)
    idx_result = next(i for i, t in enumerate(textos) if "código lido" in t)
    idx_novo = next(i for i, t in enumerate(textos) if "NOVO após agir" in t)
    assert idx_antigo < idx_tool < idx_result < idx_novo, f"tela não-linear: {textos}"
    # O bloco novo NÃO contém o pensamento antigo (cada bloco é só seu)
    assert "ANTIGO" not in textos[idx_novo]


class FakeAppSidebar:
    """App falso com sidebar registrável (sem Textual)."""

    def __init__(self) -> None:
        self.sidebar = SimpleNamespace()
        self.sidebar.update_metrics = self._registrar  # type: ignore[attr-defined]
        self.chamadas: list[dict] = []

    def _registrar(self, **kw: Any) -> None:
        self.chamadas.append(kw)

    def query_one(self, _id: str, _tipo: Any = None) -> Any:
        # A sidebar É o objeto com update_metrics (a view é o próprio app falso)
        return self.sidebar


def test_agent_usage_alimenta_sidebar_custo_oculto():
    """Tokens da ONDA chegam à sidebar via agent_usage; custo acumula oculto."""
    chat = FakeChat()
    app_falso = FakeAppSidebar()

    def orchestrator_fake() -> dict[str, Any]:
        BUS.publish(
            "agent_usage",
            agent="@valim",
            total_tokens=5_000,
            input_tokens=4_000,
            output_tokens=1_000,
            cost=0.012,
        )
        BUS.publish(
            "agent_usage",
            agent="@aniche",
            total_tokens=3_000,
            input_tokens=2_500,
            output_tokens=500,
            cost=0.008,
        )
        return {"success": True}

    async def cenario() -> None:
        await _run_orchestrator_with_stream(chat, orchestrator_fake, app=app_falso)

    asyncio.run(cenario())

    assert app_falso.chamadas, "sidebar nunca atualizada"
    final = app_falso.chamadas[-1]
    assert final["tokens"] == 8_000  # acumulado dos dois agentes
    assert final["percent"] == int(8_000 / 128_000 * 100)
    assert final["cost"] == 0.02  # custo medido (exibição é oculta na sidebar)


def test_copiar_tela_envia_transcricao_ao_clipboard(monkeypatch):
    """Ctrl+C / Ctrl+Shift+C copiam a transcrição — nunca interrompem."""
    import pyperclip

    from bombe_code.tui.app import BombeTuiApp
    from bombe_code.tui.client import BombeClient

    copiado = {}
    monkeypatch.setattr(pyperclip, "copy", lambda t: copiado.update(texto=t))

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_copy")
    chat = type(
        "FakeChatView",
        (),
        {
            "children": [
                type("W", (), {"content": "mensagem 1"})(),
                type("W", (), {"content": "mensagem 2"})(),
            ]
        },
    )()
    monkeypatch.setattr(
        type(app),
        "query_one",
        lambda self, _sel, _t=None: chat,
        raising=False,
    )

    app.action_copiar_tela()

    assert "mensagem 1" in copiado["texto"]
    assert "mensagem 2" in copiado["texto"]
