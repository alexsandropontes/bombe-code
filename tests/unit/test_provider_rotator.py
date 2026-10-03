"""Unit tests for ProviderFailoverRouter and automated recovery timer policies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bombe_code.llm.provider_rotator import (
    ProviderFailoverConfig,
    ProviderFailoverRouter,
    ProviderSlot,
)
from bombe_code.llm.quota_detector import QuotaResetInfo


def test_provider_router_selects_highest_priority():
    slot1 = ProviderSlot(name="zai", model="glm-5.3-flash", priority=1)
    slot2 = ProviderSlot(name="groq", model="llama-3.3-70b-versatile", priority=2)
    slot3 = ProviderSlot(name="llama.cpp", model="mimo-qwen-9b", priority=3)

    router = ProviderFailoverRouter(slots=[slot3, slot1, slot2])
    active = router.get_active_slot()

    assert active is not None
    assert active.name == "zai"
    assert active.priority == 1


def test_provider_router_fails_over_on_quota_exhausted():
    slot1 = ProviderSlot(name="zai", model="glm-5.3-flash", priority=1)
    slot2 = ProviderSlot(name="groq", model="llama-3.3-70b-versatile", priority=2)

    router = ProviderFailoverRouter(slots=[slot1, slot2])

    now = datetime(2026, 10, 3, 10, 0, 0, tzinfo=timezone.utc)
    quota_info = QuotaResetInfo(
        is_exhausted=True,
        retry_after_seconds=300.0,
        reset_at_utc=now + timedelta(seconds=300),
        human_message="Reset expected in 5 minutes",
    )

    next_slot = router.report_quota_exhausted(slot1, quota_info, current_time=now)

    assert next_slot is not None
    assert next_slot.name == "groq"
    assert next_slot.priority == 2
    assert slot1.is_available(now) is False
    assert slot2.is_available(now) is True


def test_provider_router_restores_primary_after_cooldown():
    now = datetime(2026, 10, 3, 10, 0, 0, tzinfo=timezone.utc)
    slot1 = ProviderSlot(
        name="zai",
        model="glm-5.3-flash",
        priority=1,
        exhausted_until_utc=now + timedelta(seconds=60),
    )
    slot2 = ProviderSlot(name="groq", model="llama-3.3-70b-versatile", priority=2)

    router = ProviderFailoverRouter(slots=[slot1, slot2])

    assert router.get_active_slot(current_time=now).name == "groq"

    future = now + timedelta(seconds=61)
    assert router.get_active_slot(current_time=future).name == "zai"


def test_provider_router_timer_evaluation():
    now = datetime(2026, 10, 3, 10, 0, 0, tzinfo=timezone.utc)
    slot1 = ProviderSlot(
        name="zai",
        model="glm-5.3-flash",
        priority=1,
        exhausted_until_utc=now + timedelta(seconds=120),
    )

    # 1. Automated timer disabled
    router_no_timer = ProviderFailoverRouter(
        slots=[slot1], config=ProviderFailoverConfig(auto_timer=False)
    )
    should_wait, wait_secs, msg = router_no_timer.should_wait_timer(current_time=now)
    assert should_wait is False
    assert "disabled" in msg.lower()

    # 2. Automated timer authorized
    router_timer = ProviderFailoverRouter(
        slots=[slot1],
        config=ProviderFailoverConfig(auto_timer=True, max_timer_wait_seconds=900),
    )
    should_wait, wait_secs, msg = router_timer.should_wait_timer(current_time=now)
    assert should_wait is True
    assert wait_secs == 120.0
    assert "Timer authorized" in msg

    # 3. Exceeds max wait threshold
    slot1.exhausted_until_utc = now + timedelta(seconds=1200)
    should_wait, wait_secs, msg = router_timer.should_wait_timer(current_time=now)
    assert should_wait is False
    assert "exceeds" in msg.lower()
