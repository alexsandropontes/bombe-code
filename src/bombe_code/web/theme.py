"""Design tokens e estilos para a Web UI (Reflex)."""

from ..tui.tokens import TOKENS

THEME = {
    **TOKENS,
    "font_mono": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    "font_sans": "Inter, system-ui, -apple-system, sans-serif",
}
