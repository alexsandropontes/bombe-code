"""Contracts, enums, and domain exceptions for Mission Lifecycle."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MissionStatus(str, Enum):
    """Lifecycle status states for a mission."""

    OPEN = "open"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OpenMissionBlockedError(RuntimeError):
    """Raised when an operation is blocked because another mission is currently open."""


class PendingDoDError(RuntimeError):
    """Raised when mission cannot be completed due to pending Definition of Done items."""


class NoActiveMissionError(RuntimeError):
    """Raised when an operation requires an active mission but none is open."""


class MissionMetadata(BaseModel):
    """Metadata describing a mission manifest."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    demand: str
    status: MissionStatus = MissionStatus.OPEN
    created_at: str
    completed_at: str | None = None


class MissionState(BaseModel):
    """Full in-memory representation of an existing mission on disk."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    demand: str
    status: MissionStatus
    path: Path
    created_at: str
    completed_at: str | None = None
    rounds: dict[str, Any] = Field(default_factory=dict)
    current_round: int | None = None
    total_rounds: int = 0
