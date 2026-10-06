"""Aplicação Reflex da Web UI do Bombe Code."""

from __future__ import annotations

import reflex as rx

from .components import chat_area, prompt_bar, sidebar
from .theme import THEME


def index() -> rx.Component:
    """Página principal da Web UI."""
    return rx.hstack(
        sidebar(),
        rx.vstack(
            chat_area(),
            prompt_bar(),
            width="calc(100vw - 260px)",
            height="100vh",
            background_color=THEME["bg"],
            spacing="0",
        ),
        spacing="0",
        width="100vw",
        height="100vh",
        background_color=THEME["bg"],
    )


app = rx.App(
    theme=rx.theme(appearance="dark"),
)
app.add_page(index, route="/")
