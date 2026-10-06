"""Catálogo de temas para a TUI Textual."""

from __future__ import annotations

from .tokens import TOKENS

THEMES: dict[str, dict[str, str]] = {
    "catppuccin": {
        **TOKENS,
    },
    "dracula": {
        "bg": "#282a36",
        "surface": "#21222c",
        "surface_alt": "#44475a",
        "text": "#f8f8f2",
        "text_muted": "#6272a4",
        "primary": "#bd93f9",
        "secondary": "#ff79c6",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "error": "#ff5555",
        "border": "#6272a4",
    },
    "tokyonight": {
        "bg": "#1a1b26",
        "surface": "#16161e",
        "surface_alt": "#24283b",
        "text": "#c0caf5",
        "text_muted": "#565f89",
        "primary": "#7aa2f7",
        "secondary": "#bb9af7",
        "success": "#9ece6a",
        "warning": "#e0af68",
        "error": "#f7768e",
        "border": "#414868",
    },
    "github_dark": {
        "bg": "#0d1117",
        "surface": "#161b22",
        "surface_alt": "#21262d",
        "text": "#c9d1d9",
        "text_muted": "#8b949e",
        "primary": "#58a6ff",
        "secondary": "#bc8cff",
        "success": "#3fb950",
        "warning": "#d29922",
        "error": "#f85149",
        "border": "#30363d",
    },
}


def get_theme(name: str) -> dict[str, str]:
    """Retorna os tokens de cores do tema solicitado ou Catppuccin por padrão."""
    return THEMES.get(name.lower().replace("-", "_"), THEMES["catppuccin"])
