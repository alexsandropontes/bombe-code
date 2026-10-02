"""Estado reativo da Web UI com Reflex."""

from __future__ import annotations

from typing import Any

import reflex as rx


class WebState(rx.State):
    """Estado global da interface Web."""

    session_id: str = ""
    prompt_text: str = ""
    is_streaming: bool = False
    messages: list[dict[str, Any]] = rx.field([])
    sessions: list[dict[str, Any]] = rx.field([])

    def set_prompt(self, text: str) -> None:
        self.prompt_text = text

    def clear_prompt(self) -> None:
        self.prompt_text = ""
