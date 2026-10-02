"""Paleta de comandos interativa para a TUI."""

from __future__ import annotations

from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static

from ..tokens import TOKENS


class CommandPalette(ModalScreen[str | None]):
    """Paleta modal para busca e execução de comandos rápidos."""

    DEFAULT_CSS = f"""
    CommandPalette {{
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }}

    #palette-container {{
        width: 70;
        height: auto;
        max-height: 20;
        border: thick {TOKENS['primary']};
        background: {TOKENS['surface']};
        padding: 1;
    }}

    #palette-input {{
        margin-bottom: 1;
    }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Fechar"),
    ]

    COMMANDS: ClassVar[list[dict[str, str]]] = [
        {"name": "help", "desc": "Exibe ajuda e atalhos"},
        {"name": "clear", "desc": "Limpa o histórico de chat da tela"},
        {"name": "theme", "desc": "Alterna o tema visual claro/escuro"},
        {"name": "sidebar", "desc": "Alterna exibição da barra lateral"},
        {"name": "quit", "desc": "Encerra a aplicação"},
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Input(placeholder="Digite um comando (ex: help, clear, theme)...", id="palette-input")
            with ListView(id="palette-list"):
                for cmd in self.COMMANDS:
                    yield ListItem(Static(f"[bold]{cmd['name']}[/bold] - {cmd['desc']}"), id=f"cmd-{cmd['name']}")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filtra comandos conforme a digitação sem recriar nós."""
        query = event.value.strip().lower().lstrip("/")
        list_view = self.query_one("#palette-list", ListView)
        for idx, cmd in enumerate(self.COMMANDS):
            if idx < len(list_view.children):
                matches = not query or query in cmd["name"].lower() or query in cmd["desc"].lower()
                list_view.children[idx].display = matches

    def on_key(self, event: events.Key) -> None:
        """Navega para a lista ao pressionar seta para baixo no input."""
        if event.key == "down":
            inp = self.query_one("#palette-input", Input)
            if inp.has_focus:
                self.query_one("#palette-list", ListView).focus()
                event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip().lstrip("/")
        if not val:
            self.dismiss(None)
            return

        for cmd in self.COMMANDS:
            if cmd["name"] == val.lower():
                self.dismiss(cmd["name"])
                return

        list_view = self.query_one("#palette-list", ListView)
        for child in list_view.children:
            if child.display and child.id:
                self.dismiss(child.id.replace("cmd-", ""))
                return

        self.dismiss(val)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.id:
            cmd_name = event.item.id.replace("cmd-", "")
            self.dismiss(cmd_name)

    def action_cancel(self) -> None:
        self.dismiss(None)
