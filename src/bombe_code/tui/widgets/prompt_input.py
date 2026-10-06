"""Widget PromptInput multiline com autocompletar dinâmico, histórico e suporte a paste de múltiplas linhas."""

from __future__ import annotations

import logging
import os
from typing import Any, ClassVar

from textual.binding import Binding
from textual.events import Key, Paste
from textual.message import Message
from textual.suggester import Suggester
from textual.widgets import TextArea

from ..tokens import TOKENS

logger = logging.getLogger(__name__)

SLASH_COMMANDS: list[str] = [
    "/connect",
    "/models",
    "/model",
    "/sessions",
    "/resume",
    "/continue",
    "/new",
    "/clear",
    "/compact",
    "/summarize",
    "/undo",
    "/redo",
    "/fork",
    "/share",
    "/unshare",
    "/export",
    "/copy",
    "/rename",
    "/timeline",
    "/help",
    "/init",
    "/review",
    "/themes",
    "/theme",
    "/thinking",
    "/toggle-thinking",
    "/timestamps",
    "/toggle-timestamps",
    "/details",
    "/editor",
    "/sidebar",
    "/agent",
    "/mcp",
    "/lsp",
    "/workspace",
    "/dir",
    "/exit",
    "/quit",
    "/q",
]

SUBAGENT_CHOICES = ["build", "plan", "explore", "review", "general"]
THEME_CHOICES = ["catppuccin", "dracula", "tokyonight", "nord", "monokai"]


def get_matching_files(project_dir: str, query: str, limit: int = 15) -> list[str]:
    """Busca arquivos e pastas no workspace correspondentes à busca."""
    matches: list[str] = []
    q = query.lower()
    try:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ("node_modules", "__pycache__", ".venv", ".git", "build", "dist")
            ]
            rel_root = os.path.relpath(root, project_dir)
            for d in dirs:
                rel = (d if rel_root == "." else os.path.join(rel_root, d)) + "/"
                if rel.lower().startswith(q) or (q and q in rel.lower()):
                    matches.append(rel)
                    if len(matches) >= limit:
                        return matches
            for f in files:
                rel = f if rel_root == "." else os.path.join(rel_root, f)
                if rel.lower().startswith(q) or (q and q in rel.lower()):
                    matches.append(rel)
                    if len(matches) >= limit:
                        return matches
    except (OSError, RuntimeError):
        pass
    return matches


class PromptSuggester(Suggester):
    """Suggester em tempo real para comandos de barra (/) e menções a arquivos (@)."""

    def __init__(self, project_dir: str = ".") -> None:
        super().__init__(use_cache=False, case_sensitive=False)
        self.project_dir = os.path.abspath(project_dir)

    async def get_suggestion(self, value: str) -> str | None:
        if not value:
            return None

        # Sugestão de comandos iniciados com /
        if value.startswith("/"):
            lower_val = value.lower()
            if lower_val.startswith("/agent "):
                for a in SUBAGENT_CHOICES:
                    cand = f"/agent {a}"
                    if cand.lower().startswith(lower_val) and len(cand) > len(value):
                        return cand
            elif lower_val.startswith(("/themes ", "/theme ")):
                prefix = lower_val.split()[0]
                for t in THEME_CHOICES:
                    cand = f"{prefix} {t}"
                    if cand.lower().startswith(lower_val) and len(cand) > len(value):
                        return cand
            else:
                from ...commands.loader import load_custom_commands

                all_cmds = list(SLASH_COMMANDS)
                try:
                    for c in load_custom_commands(self.project_dir):
                        all_cmds.append(f"/{c}")
                except (OSError, ValueError):
                    pass
                for cmd in all_cmds:
                    if cmd.lower().startswith(lower_val) and len(cmd) > len(value):
                        return cmd
            return None

        # Sugestão de menções a arquivos iniciadas com @
        if "@" in value:
            at_idx = value.rfind("@")
            prefix = value[: at_idx + 1]
            query = value[at_idx + 1 :]
            files = get_matching_files(self.project_dir, query, limit=1)
            if files and len(prefix + files[0]) > len(value):
                return prefix + files[0]

        return None


class PromptInput(TextArea):
    """Input de prompt multiline para envio de mensagens com autocompletar e histórico."""

    class Submitted(Message):
        """Evento emitido ao submeter o prompt com Enter."""

        def __init__(self, input: PromptInput, value: str) -> None:
            super().__init__()
            self.input = input
            self.value = value

    DEFAULT_CSS = f"""
    PromptInput {{
        dock: bottom;
        background: {TOKENS["surface"]};
        color: {TOKENS["text"]};
        border: tall {TOKENS["primary"]};
        padding: 0 1;
        margin: 1;
        height: 3;
        min-height: 3;
        max-height: 8;
        scrollbar-size-vertical: 1;
        scrollbar-size-horizontal: 0;
    }}
    PromptInput:focus {{
        border: tall {TOKENS["secondary"]};
    }}
    PromptInput > .text-area--cursor-line {{
        background: transparent;
    }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("tab", "complete", "Autocompletar", show=False, priority=True),
        Binding(
            "shift+tab", "toggle_vibe_mode", "Alternar Modo VIBE/TDD", show=False, priority=True
        ),
    ]

    def __init__(self, project_dir: str = ".", **kwargs: Any) -> None:
        self.project_dir = os.path.abspath(project_dir)
        self._suggester = PromptSuggester(self.project_dir)
        self.prompt_history: list[str] = []
        self._history_index: int = -1
        self._current_buffer: str = ""
        self._tab_candidates: list[str] = []
        self._tab_index: int = -1

        # Limpa parâmetros herdados de Input que não existem em TextArea
        kwargs.pop("suggester", None)

        super().__init__(
            text="",
            placeholder="Digite uma instrução ou comando (/help, @arquivo)... (Shift+Enter para nova linha)",
            show_line_numbers=False,
            soft_wrap=True,
            tab_behavior="focus",
            **kwargs,
        )
        self._update_height()

    @property
    def value(self) -> str:
        return self.text

    @value.setter
    def value(self, val: str) -> None:
        self.load_text(val)
        self.cursor_location = (max(0, self.document.line_count - 1), len(self.document.lines[-1]))
        self._update_height()

    @property
    def cursor_position(self) -> int:
        row, col = self.cursor_location
        pos = 0
        for r in range(row):
            pos += len(self.document.get_line(r)) + 1
        return pos + col

    @cursor_position.setter
    def cursor_position(self, pos: int) -> None:
        accum = 0
        for r, line in enumerate(self.document.lines):
            line_len = len(line)
            if accum + line_len >= pos:
                self.cursor_location = (r, pos - accum)
                return
            accum += line_len + 1
        self.cursor_location = (max(0, self.document.line_count - 1), len(self.document.lines[-1]))

    def _update_height(self) -> None:
        """Ajusta a altura dinamicamente entre 3 e 8 linhas conforme a quantidade de texto."""
        lines = self.document.line_count
        new_height = max(3, min(8, lines + 2))
        self.styles.height = new_height

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._update_height()

    def action_paste(self) -> None:
        """Cola do clipboard do sistema operacional ou do clipboard interno com suporte a textos grandes."""
        if self.read_only:
            return
        text = ""
        try:
            import pyperclip

            text = pyperclip.paste()
        except Exception as exc:  # noqa: BLE001 — clipboard pode estar indisponível
            logger.debug("Área de transferência indisponível: %s", exc)
        if not text:
            text = self.app.clipboard
        if text:
            clean_text = text.replace("\r\n", "\n").replace("\r", "\n")
            if result := self._replace_via_keyboard(clean_text, *self.selection):
                self.move_cursor(result.end_location)
                self.focus()
                self._update_height()

    async def _on_paste(self, event: Paste) -> None:
        event.stop()
        event.prevent_default()
        if self.read_only or not event.text:
            return
        clean_text = event.text.replace("\r\n", "\n").replace("\r", "\n")
        if result := self._replace_via_keyboard(clean_text, *self.selection):
            self.move_cursor(result.end_location)
            self.focus()
            self._update_height()

    def set_project_dir(self, path: str) -> None:
        """Atualiza a pasta do workspace para autocompletar de arquivos."""
        self.project_dir = os.path.abspath(path)
        self._suggester.project_dir = self.project_dir

    def action_complete(self) -> None:
        """Autocompleta a sugestão atual ou cicla entre opções correspondentes (Tab)."""
        # Se já estiver ciclando entre candidatos e o valor atual for um dos candidatos
        if self._tab_candidates and self.value in self._tab_candidates:
            self._tab_index = (self._tab_index + 1) % len(self._tab_candidates)
            self.value = self._tab_candidates[self._tab_index]
            self.cursor_position = len(self.value)
            return

        val = self.value.strip()

        # Comandos de barra (/)
        if val.startswith("/"):
            lower_val = val.lower()
            if lower_val.startswith("/agent "):
                matches = [
                    f"/agent {a}"
                    for a in SUBAGENT_CHOICES
                    if f"/agent {a}".lower().startswith(lower_val)
                ]
            elif lower_val.startswith(("/themes ", "/theme ")):
                prefix = val.split()[0]
                matches = [
                    f"{prefix} {t}"
                    for t in THEME_CHOICES
                    if f"{prefix} {t}".lower().startswith(lower_val)
                ]
            else:
                from ...commands.loader import load_custom_commands

                all_cmds = list(SLASH_COMMANDS)
                try:
                    for c in load_custom_commands(self.project_dir):
                        all_cmds.append(f"/{c}")
                except (OSError, ValueError):
                    pass
                matches = [c for c in all_cmds if c.lower().startswith(lower_val)]

            if matches:
                self._tab_candidates = matches
                self._tab_index = 0
                self.value = matches[0]
                self.cursor_position = len(self.value)
                return

        # Menções a arquivos (@)
        if "@" in self.value:
            at_idx = self.value.rfind("@")
            prefix = self.value[: at_idx + 1]
            query = self.value[at_idx + 1 :]
            files = get_matching_files(self.project_dir, query)
            if files:
                matches = [prefix + f for f in files]
                self._tab_candidates = matches
                self._tab_index = 0
                self.value = matches[0]
                self.cursor_position = len(self.value)
                return

        # Sem autocomplete aplicável: o Tab atua ciclando a etapa da ONDA exclusivamente no modo TDD
        try:
            app = self.app
            # No modo VIBE, o Tab não cicla etapas (só existe VIBE, navegado via Shift+Tab)
            if getattr(app, "mode", "TDD") == "VIBE":
                return
            if hasattr(app, "action_cycle_stage"):
                app.action_cycle_stage()
        except (AttributeError, RuntimeError):  # pragma: no cover
            pass

    def action_toggle_vibe_mode(self) -> None:
        """Alterna entre Modo VIBE e Modo TDD via Shift+Tab."""
        try:
            app = self.app
            if hasattr(app, "action_toggle_vibe_mode"):
                app.action_toggle_vibe_mode()
        except (AttributeError, RuntimeError):  # pragma: no cover
            pass

    def action_history_prev(self) -> None:
        if not self.prompt_history:
            return
        if self._history_index == -1:
            self._current_buffer = self.value
            self._history_index = len(self.prompt_history) - 1
        elif self._history_index > 0:
            self._history_index -= 1

        if 0 <= self._history_index < len(self.prompt_history):
            self.value = self.prompt_history[self._history_index]

    def action_history_next(self) -> None:
        if self._history_index == -1:
            return
        if self._history_index < len(self.prompt_history) - 1:
            self._history_index += 1
            self.value = self.prompt_history[self._history_index]
        else:
            self._history_index = -1
            self.value = self._current_buffer

    def record_history(self, val: str) -> None:
        self.prompt_history.append(val)
        self._history_index = -1
        self._current_buffer = ""
        self._tab_candidates = []
        self._tab_index = -1
        self.value = ""
        self._update_height()

    async def _on_key(self, event: Key) -> None:
        # 1. Enter sem modificadores: submete o prompt
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            val = self.value.strip()
            if val:
                self.post_message(self.Submitted(self, self.value))
            return

        # 2. Shift+Enter, Ctrl+J ou Alt+Enter: insere quebra de linha manual
        if event.key in ("shift+enter", "ctrl+j", "alt+enter"):
            event.stop()
            event.prevent_default()
            start, end = self.selection
            self._replace_via_keyboard("\n", start, end)
            self._update_height()
            return

        # 3. Up: navega no histórico se estiver na primeira linha
        if event.key == "up" and (self.cursor_location[0] == 0 or self.document.line_count <= 1):
            event.stop()
            event.prevent_default()
            self.action_history_prev()
            return

        # 4. Down: navega no histórico se estiver na última linha
        if event.key == "down" and (
            self.cursor_location[0] >= self.document.line_count - 1 or self.document.line_count <= 1
        ):
            event.stop()
            event.prevent_default()
            self.action_history_next()
            return

        await super()._on_key(event)
