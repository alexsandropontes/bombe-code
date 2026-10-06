"""Testes unitários para a CommandPalette modal."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, ListView

from bombe_code.tui.widgets.command_palette import CommandPalette


class PaletteTestApp(App[str | None]):
    def compose(self) -> ComposeResult:
        yield Input(id="dummy")

    def action_open_palette(self) -> None:
        self.push_screen(CommandPalette(), self._handle_result)

    def _handle_result(self, res: str | None) -> None:
        self.result = res


@pytest.mark.anyio
async def test_command_palette_escape() -> None:
    app = PaletteTestApp()
    async with app.run_test() as pilot:
        app.action_open_palette()
        await pilot.pause()
        assert isinstance(app.screen, CommandPalette)

        # Pressiona escape para cancelar
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, CommandPalette)
        assert getattr(app, "result", None) is None


@pytest.mark.anyio
async def test_command_palette_filter_and_submit() -> None:
    app = PaletteTestApp()
    async with app.run_test() as pilot:
        app.action_open_palette()
        await pilot.pause()
        assert isinstance(app.screen, CommandPalette)

        # Digita 'help' e dá enter
        inp = app.screen.query_one("#palette-input", Input)
        inp.value = "help"
        await pilot.press("enter")
        await pilot.pause()
        assert not isinstance(app.screen, CommandPalette)
        assert app.result == "help"


@pytest.mark.anyio
async def test_command_palette_filter_list() -> None:
    app = PaletteTestApp()
    async with app.run_test() as pilot:
        app.action_open_palette()
        await pilot.pause()
        palette = app.screen
        assert isinstance(palette, CommandPalette)

        # Digita filtro inexistente
        inp = palette.query_one("#palette-input", Input)
        inp.value = "nonexistent_command_xyz"
        await pilot.pause()

        list_view = palette.query_one("#palette-list", ListView)
        visible_items = [c for c in list_view.children if c.display]
        assert len(visible_items) == 0

        # Digita 'the' (deve casar com 'theme')
        inp.value = "the"
        await pilot.pause()
        visible_items = [c for c in list_view.children if c.display]
        assert len(visible_items) == 1
        assert visible_items[0].id == "cmd-theme"
