"""Testes do _run_orchestrator_with_stream — transcript ao vivo da TUI consumindo o bus."""

import asyncio
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
