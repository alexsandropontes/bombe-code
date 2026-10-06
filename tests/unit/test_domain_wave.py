"""Testes unitários do Domínio da ONDA (DDD Domain Layer)."""

import pytest

from bombe_code.domain.wave.models import (
    StoryCard,
    Wave,
    WaveId,
    WaveState,
)


def test_wave_id_normalization():
    wid1 = WaveId("001")
    assert str(wid1) == "ONDA-001"

    wid2 = WaveId("onda-042")
    assert str(wid2) == "ONDA-042"

    wid3 = WaveId("WAVE-003")
    assert str(wid3) == "WAVE-003"


def test_story_card_lifecycle():
    card = StoryCard(story_id="ST-101", title="Implementar Auth")
    assert card.status == "BACKLOG"
    assert not card.is_blocked()

    card.block("Falta schema", agent="@hoare")
    assert card.is_blocked()
    assert card.status == "BLOCKED"
    assert "@hoare: Falta schema" in (card.blocked_by or "")

    card.unblock()
    assert not card.is_blocked()
    assert card.status == "IN_PROGRESS"


def test_wave_state_transitions():
    wave = Wave(wave_id=WaveId("001"), state=WaveState.DISCUSS)
    assert wave.can_transition_to(WaveState.PLAN)
    assert not wave.can_transition_to(WaveState.VALIDATE)

    wave.transition_to(WaveState.PLAN)
    assert wave.state == WaveState.PLAN
    assert wave.can_transition_to(WaveState.EXECUTE)

    wave.transition_to(WaveState.EXECUTE)
    assert wave.state == WaveState.EXECUTE

    with pytest.raises(ValueError, match="Transição ilegal"):
        wave.transition_to(WaveState.DISCUSS)
