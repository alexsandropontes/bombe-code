"""Adaptador para o Agent Client Protocol (ACP)."""

from __future__ import annotations

from typing import Any


class ACPAdapter:
    """Implementa o protocolo de mensagens ACP para interoperabilidade com clientes e agentes."""

    def format_message(self, role: str, content: str) -> dict[str, Any]:
        return {
            "role": role,
            "content": content,
            "protocol": "acp/1.0",
        }

    def parse_event(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": raw_event.get("type", "unknown"),
            "data": raw_event,
        }
