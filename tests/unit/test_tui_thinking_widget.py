"""Testes unitários para o ThinkingWidget animado da TUI."""

from __future__ import annotations

import asyncio

import pytest
from textual.app import App, ComposeResult

from bombe_code.tui.widgets.thinking_widget import ThinkingWidget


class MockThinkingApp(App):
    def compose(self) -> ComposeResult:
        yield ThinkingWidget(message="Aguardando modelo", id="test-thinking")


@pytest.mark.anyio
async def test_thinking_widget_animation_and_unmount():
    """Valida que o ThinkingWidget alterna frames e pontinhos e limpa o timer ao desmontar."""
    app = MockThinkingApp()
    async with app.run_test() as pilot:
        th = app.query_one("#test-thinking", ThinkingWidget)
        initial_render = str(th.render())

        # Deve conter o ícone inicial e mensagem
        assert "⏳" in initial_render
        assert "Aguardando modelo" in initial_render

        # Avança tempo para o timer disparar o tick
        await pilot.pause(0.4)
        second_render = str(th.render())

        # No segundo frame, a ampulheta virou e os pontinhos aumentaram
        assert "⌛" in second_render
        assert second_render != initial_render

        # Terceiro tick
        await pilot.pause(0.4)
        third_render = str(th.render())
        assert "⏳" in third_render
        assert third_render != second_render

        # Ao remover o widget, o timer é desativado sem erro
        await th.remove()
        await pilot.pause(0.05)
        assert len(app.query("#test-thinking")) == 0


@pytest.mark.anyio
async def test_fixed_processing_status_bar_in_app():
    """Garante que a barra de processamento é fixa acima do input e nunca polui o chat."""
    from unittest.mock import AsyncMock, MagicMock

    from bombe_code.tui.app import BombeTuiApp

    async def mock_stream_events(*args, **kwargs):
        while True:
            await asyncio.sleep(1)
            if False:
                yield {}

    client = MagicMock()
    client.create_session = AsyncMock(return_value={"id": "sess-test"})
    client.list_messages = AsyncMock(return_value=[])
    client.get_history = AsyncMock(return_value=[])
    client.stream_events = mock_stream_events
    client.set_stage = AsyncMock()

    app = BombeTuiApp(client=client)
    async with app.run_test() as pilot:
        await pilot.pause()
        bar = app.query_one("#processing-status-bar", ThinkingWidget)
        assert bar.active is False

        await app._handle_event({"type": "prompt.started"})
        assert bar.active is True
        assert "Processando contexto" in bar.message

        await app._handle_event({"type": "reasoning-delta", "text": "Pensando..."})
        assert "Raciocinando" in bar.message

        await app._handle_event({"type": "text-delta", "text": "Resposta"})
        assert "Recebendo resposta" in bar.message

        await app._handle_event({"type": "tool-call", "tool": "read_file"})
        assert "read_file" in bar.message

        await app._handle_event({"type": "prompt.finished"})
        assert bar.active is False

        chat = app.query_one("#chat-view")
        assert not any(isinstance(c, ThinkingWidget) for c in chat.children)
