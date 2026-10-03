"""Multi-Provider Failover & Rotation Engine — Enterprise LLM Resilience.

Provides prioritized multi-provider fallback routing (e.g. Z.ai, Groq, OpenRouter, OpenAI, local llama.cpp).
When a provider exhausts its rate limit or quota window, the router tracks its recovery time (with timezone awareness),
gracefully fails over to the next available provider in priority order, and optionally triggers automated wait timers
when all upstream endpoints are cooling down.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from bombe_code.llm.quota_detector import QuotaResetInfo

logger = logging.getLogger(__name__)


@dataclass
class ProviderSlot:
    """Configured provider endpoint inside the resilience pool."""

    name: str
    model: str
    priority: int = 1
    enabled: bool = True
    exhausted_until_utc: datetime | None = None
    last_error: str | None = None
    total_calls: int = 0
    total_exhausted_events: int = 0

    def is_available(self, current_time: datetime | None = None) -> bool:
        """Determines if the provider is currently active and out of cooldown/exhaustion window."""
        if not self.enabled:
            return False
        if self.exhausted_until_utc is None:
            return True
        now = current_time or datetime.now(timezone.utc)
        return now >= self.exhausted_until_utc

    def seconds_until_available(self, current_time: datetime | None = None) -> float:
        """Returns the number of seconds remaining until provider recovery (0.0 if already available)."""
        if self.is_available(current_time):
            return 0.0
        if self.exhausted_until_utc is None:
            return 0.0
        now = current_time or datetime.now(timezone.utc)
        diff = (self.exhausted_until_utc - now).total_seconds()
        return max(0.0, diff)


@dataclass
class ProviderFailoverConfig:
    """Configuration policies for provider failover and recovery timers."""

    enabled: bool = True
    auto_timer: bool = False
    max_timer_wait_seconds: float = 900.0  # Maximum 15 minutes of automated timer wait


class ProviderFailoverRouter:
    """Enterprise router responsible for provider prioritization, failover, and cooldown management."""

    def __init__(
        self,
        slots: list[ProviderSlot] | None = None,
        config: ProviderFailoverConfig | None = None,
    ) -> None:
        self.slots: list[ProviderSlot] = sorted(slots or [], key=lambda s: s.priority)
        self.config = config or ProviderFailoverConfig()

    def add_slot(self, slot: ProviderSlot) -> None:
        """Adds a provider slot to the pool and maintains priority ordering."""
        self.slots.append(slot)
        self.slots.sort(key=lambda s: s.priority)

    def get_active_slot(self, current_time: datetime | None = None) -> ProviderSlot | None:
        """Returns the highest priority provider currently available."""
        if not self.slots:
            return None

        for slot in self.slots:
            if slot.is_available(current_time):
                return slot

        return None

    def report_quota_exhausted(
        self,
        slot: ProviderSlot,
        quota_info: QuotaResetInfo,
        current_time: datetime | None = None,
    ) -> ProviderSlot | None:
        """Marks the exhausted provider slot with its cooldown deadline and routes to the next available endpoint."""
        slot.total_exhausted_events += 1
        slot.last_error = quota_info.human_message or quota_info.raw_message

        # Calculate recovery deadline
        if quota_info.reset_at_utc:
            slot.exhausted_until_utc = quota_info.reset_at_utc
        elif quota_info.retry_after_seconds:
            now = current_time or datetime.now(timezone.utc)
            slot.exhausted_until_utc = now + quota_info.retry_after_seconds  # type: ignore[operator]
        else:
            from datetime import timedelta
            now = current_time or datetime.now(timezone.utc)
            slot.exhausted_until_utc = now + timedelta(seconds=60)

        logger.warning(
            "[PROVIDER FAILOVER] Provider '%s' (%s) exhausted quota limit. %s",
            slot.name,
            slot.model,
            quota_info.human_message,
        )

        next_slot = self.get_active_slot(current_time)
        if next_slot and next_slot != slot:
            logger.info(
                "[PROVIDER FAILOVER] Routing traffic to next available provider '%s' (%s) [Priority %d].",
                next_slot.name,
                next_slot.model,
                next_slot.priority,
            )
            return next_slot

        logger.warning(
            "[PROVIDER FAILOVER] All %d configured providers are currently exhausted or in cooldown.",
            len(self.slots),
        )
        return None

    def get_min_wait_seconds(self, current_time: datetime | None = None) -> float:
        """Calculates the minimum wait duration across all cooling-down providers."""
        if not self.slots:
            return 0.0
        waits = [s.seconds_until_available(current_time) for s in self.slots if s.enabled]
        if not waits:
            return 0.0
        return min(waits)

    def should_wait_timer(self, current_time: datetime | None = None) -> tuple[bool, float, str]:
        """Evaluates whether policy permits an automated countdown wait timer.

        Returns (should_wait, wait_seconds, reason).
        """
        if not self.config.auto_timer:
            return False, 0.0, "Automated timer disabled in configuration."

        min_wait = self.get_min_wait_seconds(current_time)
        if min_wait <= 0.0:
            return False, 0.0, "Provider available; no wait needed."

        if min_wait > self.config.max_timer_wait_seconds:
            mins = round(min_wait / 60, 1)
            max_mins = round(self.config.max_timer_wait_seconds / 60, 1)
            return (
                False,
                min_wait,
                f"Wait duration ({mins}m) exceeds configured threshold ({max_mins}m).",
            )

        mins = round(min_wait / 60, 1)
        return True, min_wait, f"Timer authorized: waiting {min_wait:.0f}s ({mins}m) for provider recovery."
