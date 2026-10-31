"""Quota manager and circuit breaker for cloud LLM providers."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bombe_code.llm.quota_detector import parse_quota_reset_info

logger = logging.getLogger(__name__)


class QuotaExhaustedError(RuntimeError):
    """Raised when a cloud provider returns HTTP 429 or quota is exhausted."""


class ProviderQuotaStatus(BaseModel):
    """Audit status of a specific provider's quota."""

    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "exhausted"] = "healthy"
    consecutive_failures: int = 0
    last_error_code: int | None = None
    last_error_message: str | None = None
    locked_until: datetime | None = None


class QuotaState(BaseModel):
    """Persisted root schema for provider quota states."""

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    providers: dict[str, ProviderQuotaStatus] = Field(default_factory=dict)


def _default_state_path() -> Path:
    return Path.home() / ".local" / "share" / "bombe-code" / "quota_state.json"


class QuotaManager:
    """Manages cloud quota status, circuit breaking, and persistent locks."""

    def __init__(self, state_path: Path | str | None = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else _default_state_path()
        self._state = self._load_state()

    def _load_state(self) -> QuotaState:
        if not self.state_path.exists():
            return QuotaState()
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return QuotaState.model_validate(data)
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning(
                "Corrupted or unreadable quota state at %s: %s; resetting to empty state",
                self.state_path,
                exc,
            )
            return QuotaState()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state.updated_at = datetime.now(UTC)
        payload = self._state.model_dump(mode="json")

        dir_path = self.state_path.parent
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_path, delete=False, encoding="utf-8"
        ) as tmp_file:
            json.dump(payload, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_name = tmp_file.name

        os.replace(tmp_name, self.state_path)

    def is_available(self, provider: str) -> bool:
        """Return True if provider is healthy or if its lock has expired."""
        status = self.get_provider_status(provider)
        if status.status != "exhausted":
            return True

        if status.locked_until is None:
            return False

        now = datetime.now(UTC)
        # Handle naive vs aware comparison safely
        locked_time = status.locked_until
        if locked_time.tzinfo is None:
            locked_time = locked_time.replace(tzinfo=UTC)

        return now >= locked_time

    def get_provider_status(self, provider: str) -> ProviderQuotaStatus:
        """Get current audit status for a provider."""
        return self._state.providers.get(provider, ProviderQuotaStatus())

    def record_exhausted(
        self,
        provider: str,
        lock_duration_seconds: int = 10800,
        error_code: int = 429,
        error_message: str = "Rate limit or quota exhausted",
        locked_until: datetime | None = None,
    ) -> None:
        """Mark provider as exhausted and lock for lock_duration_seconds (default 3 hours)."""
        current = self.get_provider_status(provider)
        now = datetime.now(UTC)

        if locked_until is None:
            if error_message:
                info = parse_quota_reset_info(error_message, provider_hint=provider)
                if info.reset_at_utc and info.reset_at_utc > now:
                    locked_until = info.reset_at_utc
                else:
                    locked_until = now + timedelta(seconds=lock_duration_seconds)
            else:
                locked_until = now + timedelta(seconds=lock_duration_seconds)

        new_status = ProviderQuotaStatus(
            status="exhausted",
            consecutive_failures=current.consecutive_failures + 1,
            last_error_code=error_code,
            last_error_message=error_message,
            locked_until=locked_until,
        )
        self._state.providers[provider] = new_status
        self._save_state()

    def reset(self, provider: str) -> None:
        """Reset provider status to healthy and clear lock."""
        self._state.providers[provider] = ProviderQuotaStatus(status="healthy")
        self._save_state()
