"""Integration tests for F15 tui-complete (Command Palette, Themes, Help Dialog)."""

import pytest

from bombe_code.tui.themes import THEMES, get_theme
from bombe_code.tui.widgets.command_palette import CommandPalette
from bombe_code.tui.widgets.help_dialog import HelpDialog

pytestmark = pytest.mark.integration


def test_tui_themes_registry():
    assert "catppuccin" in THEMES
    assert "dracula" in THEMES
    assert "tokyonight" in THEMES

    dracula = get_theme("dracula")
    assert dracula["bg"] == "#282a36"

    catp = get_theme("catppuccin")
    assert catp["bg"] == "#1e1e2e"


def test_tui_command_palette_modal():
    palette = CommandPalette()
    assert len(palette.COMMANDS) >= 4
    assert any(cmd["name"] == "help" for cmd in palette.COMMANDS)


def test_tui_help_dialog():
    dialog = HelpDialog()
    assert dialog is not None
