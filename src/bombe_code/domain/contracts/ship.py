"""Domain contracts for git promotion and ship engine."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ShipTarget(str, Enum):
    """Target environments for git promotion."""

    DEV = "dev"
    HML = "hml"
    PRD = "prd"


class PromotionResult(BaseModel):
    """Result model for git promotion operations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    source_commit: str
    target_branch: str
    message: str
    tests_passed: bool
    details: list[str] = Field(default_factory=list)
