"""Testes unitários para o ThinkingWidget animado da TUI."""

from __future__ import annotations

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
