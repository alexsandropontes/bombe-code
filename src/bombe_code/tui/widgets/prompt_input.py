"""Widget PromptInput com autocompletar dinâmico, histórico e envio de comandos."""

from __future__ import annotations

import os
from typing import Any, ClassVar

from textual.binding import Binding
from textual.suggester import Suggester
from textual.widgets import Input

from ..tokens import TOKENS

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


class PromptInput(Input):
    """Input de prompt para envio de mensagens com autocompletar e histórico."""

    DEFAULT_CSS = f"""
    PromptInput {{
        dock: bottom;
        background: {TOKENS["surface"]};
        color: {TOKENS["text"]};
        border: tall {TOKENS["primary"]};
        padding: 0 1;
        margin: 1;
        height: 3;
    }}
    PromptInput:focus {{
        border: tall {TOKENS["secondary"]};
    }}
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("up", "history_prev", "Histórico Anterior", show=False),
        Binding("down", "history_next", "Histórico Próximo", show=False),
        Binding("tab", "complete", "Autocompletar", show=False),
    ]

    def __init__(self, project_dir: str = ".", **kwargs: Any) -> None:
        self.project_dir = os.path.abspath(project_dir)
        self._suggester = PromptSuggester(self.project_dir)
        self.history: list[str] = []
        self._history_index: int = -1
        self._current_buffer: str = ""
        self._tab_candidates: list[str] = []
        self._tab_index: int = -1

        super().__init__(
            placeholder="Digite uma instrução ou comando (/help, @arquivo)...",
            suggester=self._suggester,
            **kwargs,
        )

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

        # Se houver sugestão ativa inline, aceita-a
        if self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)

    def action_history_prev(self) -> None:
        if not self.history:
            return
        if self._history_index == -1:
            self._current_buffer = self.value
            self._history_index = len(self.history) - 1
        elif self._history_index > 0:
            self._history_index -= 1

        if 0 <= self._history_index < len(self.history):
            self.value = self.history[self._history_index]
            self.cursor_position = len(self.value)

    def action_history_next(self) -> None:
        if self._history_index == -1:
            return
        if self._history_index < len(self.history) - 1:
            self._history_index += 1
            self.value = self.history[self._history_index]
        else:
            self._history_index = -1
            self.value = self._current_buffer
        self.cursor_position = len(self.value)

    def record_history(self, val: str) -> None:
        self.history.append(val)
        self._history_index = -1
        self._current_buffer = ""
        self._tab_candidates = []
        self._tab_index = -1
        self.value = ""
