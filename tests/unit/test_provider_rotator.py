"""Testes unitários para a Roda de Samba de Provedores e Política de Timer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bombe_code.llm.provider_rotator import (
    ProviderSlot,
    RodaDeSamba,
    RodaDeSambaConfig,
)
from bombe_code.llm.quota_detector import QuotaResetInfo


def test_roda_de_samba_selects_highest_priority():
    slot1 = ProviderSlot(name="zai", model="glm-5.3-flash", priority=1)
    slot2 = ProviderSlot(name="groq", model="llama-3.3-70b-versatile", priority=2)
    slot3 = ProviderSlot(name="llama.cpp", model="mimo-qwen-9b", priority=3)

    roda = RodaDeSamba(slots=[slot3, slot1, slot2])
    active = roda.get_active_slot()

    assert active is not None
    assert active.name == "zai"
    assert active.priority == 1


def test_roda_de_samba_rotates_on_quota_exhausted():
    slot1 = ProviderSlot(name="zai", model="glm-5.3-flash", priority=1)
    slot2 = ProviderSlot(name="groq", model="llama-3.3-70b-versatile", priority=2)

    roda = RodaDeSamba(slots=[slot1, slot2])

    now = datetime(2026, 10, 3, 10, 0, 0, tzinfo=timezone.utc)
    quota_info = QuotaResetInfo(
        is_exhausted=True,
        retry_after_seconds=300.0,
        reset_at_utc=now + timedelta(seconds=300),
        human_message="Reset em 5 minutos",
    )

    # Reporta estouro no slot1
    next_slot = roda.report_quota_exhausted(slot1, quota_info, current_time=now)

    assert next_slot is not None
    assert next_slot.name == "groq"
    assert next_slot.priority == 2
    assert slot1.is_available(now) is False
    assert slot2.is_available(now) is True


def test_roda_de_samba_returns_to_primary_when_quota_resets():
    now = datetime(2026, 10, 3, 10, 0, 0, tzinfo=timezone.utc)
    slot1 = ProviderSlot(
        name="zai",
        model="glm-5.3-flash",
        priority=1,
        exhausted_until_utc=now + timedelta(seconds=60),
    )
    slot2 = ProviderSlot(name="groq", model="llama-3.3-70b-versatile", priority=2)

    roda = RodaDeSamba(slots=[slot1, slot2])

    # No momento now, slot1 está em resfriamento -> groq é ativo
    assert roda.get_active_slot(current_time=now).name == "groq"

    # 61 segundos depois, slot1 já resetou -> volta para zai
    future = now + timedelta(seconds=61)
    assert roda.get_active_slot(current_time=future).name == "zai"


def test_roda_de_samba_auto_timer_evaluation():
    now = datetime(2026, 10, 3, 10, 0, 0, tzinfo=timezone.utc)
    slot1 = ProviderSlot(
        name="zai",
        model="glm-5.3-flash",
        priority=1,
        exhausted_until_utc=now + timedelta(seconds=120),
    )

    # 1. Timer desabilitado por padrão
    roda_no_timer = RodaDeSamba(slots=[slot1], config=RodaDeSambaConfig(auto_timer=False))
    should_wait, wait_secs, msg = roda_no_timer.should_wait_timer(current_time=now)
    assert should_wait is False
    assert "desabilitado" in msg

    # 2. Timer habilitado e tempo viável (120s <= 900s)
    roda_timer = RodaDeSamba(
        slots=[slot1], config=RodaDeSambaConfig(auto_timer=True, max_timer_wait_seconds=900)
    )
    should_wait, wait_secs, msg = roda_timer.should_wait_timer(current_time=now)
    assert should_wait is True
    assert wait_secs == 120.0
    assert "Timer autorizado" in msg

    # 3. Tempo excede o limite configurado (1200s > 900s)
    slot1.exhausted_until_utc = now + timedelta(seconds=1200)
    should_wait, wait_secs, msg = roda_timer.should_wait_timer(current_time=now)
    assert should_wait is False
    assert "excede o limite" in msg
