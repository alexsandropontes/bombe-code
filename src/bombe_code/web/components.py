"""Componentes da Web UI construídos com Reflex."""

from __future__ import annotations

import reflex as rx

from .state import WebState
from .theme import THEME


def sidebar() -> rx.Component:
    """Barra lateral com histórico de sessões."""
    return rx.vstack(
        rx.heading("Bombe Code", size="5", color=THEME["primary"]),
        rx.text("Sessões Recentes", size="2", color=THEME["text_muted"]),
        rx.divider(),
        width="260px",
        height="100vh",
        background_color=THEME["surface"],
        padding="1rem",
        border_right=f"1px solid {THEME['border']}",
    )


def chat_area() -> rx.Component:
    """Área central de mensagens e streaming."""
    return rx.vstack(
        rx.scroll_area(
            rx.vstack(
                rx.text("Bem-vindo ao Bombe Code Web", color=THEME["text_muted"]),
                spacing="3",
                padding="1rem",
            ),
            height="calc(100vh - 120px)",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def prompt_bar() -> rx.Component:
    """Barra inferior para entrada de prompt."""
    return rx.hstack(
        rx.input(
            placeholder="Digite uma instrução para o Bombe Code...",
            value=WebState.prompt_text,
            on_change=WebState.set_prompt,
            width="100%",
            background_color=THEME["surface"],
            color=THEME["text"],
            border=f"1px solid {THEME['border']}",
        ),
        rx.button("Enviar", background_color=THEME["primary"], color=THEME["bg"]),
        width="100%",
        padding="1rem",
        border_top=f"1px solid {THEME['border']}",
        background_color=THEME["surface"],
    )
