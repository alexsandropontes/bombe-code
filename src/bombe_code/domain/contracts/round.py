"""Contracts, enums, and domain models for Round execution lifecycle."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RoundStatus(str, Enum):
    """Lifecycle states for a Round."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DOR_READY = "dor_ready"
    BURNING = "burning"
    REVIEWING = "reviewing"
    VALIDATED = "validated"


class SliceType(str, Enum):
    """Specification of slice engineering layer."""

    BACKEND_TDD = "backend_tdd"
    FRONTEND_CONSTRUCTION = "frontend_construction"


class SliceState(BaseModel):
    """State model for vertical slices within a round."""

    model_config = ConfigDict(extra="forbid")

    slice_id: str
    name: str
    type: SliceType
    status: str = "pending"


class RoundState(BaseModel):
    """State model representing a round lifecycle checkpoint."""

    model_config = ConfigDict(extra="ignore")

    round_number: int
    story_id: str
    status: RoundStatus
    slices: list[SliceState] = Field(default_factory=list)
    dor_ready: bool = False
    dod_validated: bool = False
    message: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    next_round_auto_advanced: bool = False

    def __getitem__(self, item: str) -> Any:
        """Allow backwards-compatible dict-like item access."""
        if item == "round":
            return self.round_number
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        """Allow backwards-compatible dict-like get method."""
        try:
            return self[item]
        except KeyError:
            return default


class RoundNotReadyError(RuntimeError):
    """Raised when an operation requires a round to be at DoR or burned before proceeding."""


class InvalidRoundStateError(ValueError):
    """Raised when an operation is invalid for the current state of the round."""
