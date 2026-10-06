"""Modelos e Entidades do Domínio de Sessão (Session Domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class Part:
    """Parte constituinte de uma mensagem (texto, reasoning, tool-call, tool-result, file)."""

    id: str
    message_id: str
    type: str  # "text", "reasoning", "tool-call", "tool-result", "file", "image"
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Message:
    """Entidade representando uma mensagem trocada em um turno de conversa."""

    id: str
    session_id: str
    role: str  # "user", "assistant", "system"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Agregado Raiz representando uma sessão de interação com o Bombe Code."""

    id: str
    title: str = ""
    directory: str = "."
    project_id: str = ""
    parent_id: str | None = None
    agent: str = "build"
    model: str = "padrão"
    stage: str = "DISCOVERY"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
