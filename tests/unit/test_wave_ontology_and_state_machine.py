"""Testes TDD para a Story ST-035: Ontologia de Ondas (WaveType e State Machine)."""

import pytest
from bombe_code.turing.state_machine import (
    InvalidTransitionError,
    TuringStateMachine,
    WavePhase,
    WaveState,
    WaveType,
)


def test_wave_zero_detected_from_id():
    sm = TuringStateMachine(wave_id="ONDA-000")
    assert sm.wave_type == WaveType.WAVE_ZERO
    assert sm.current_phase == WavePhase.UPSTREAM


def test_delivery_wave_detected_from_id():
    sm = TuringStateMachine(wave_id="ONDA-001")
    assert sm.wave_type == WaveType.DELIVERY_WAVE


def test_wave_zero_only_permits_upstream_transitions():
    sm = TuringStateMachine(wave_id="ONDA-000", initial_state=WaveState.DISCUSS)
    # DISCUSS -> PLAN é válido na Onda Zero
    sm.transition_to(WaveState.PLAN)
    assert sm.current_state == WaveState.PLAN
    assert sm.current_phase == WavePhase.UPSTREAM

    # PLAN -> COMPLETED é válido para encerrar a Onda Zero (apenas planejamento)
    assert sm.can_transition_to(WaveState.COMPLETED) is True

    # PLAN -> EXECUTE é terminantemente PROIBIDO na Onda Zero!
    assert sm.can_transition_to(WaveState.EXECUTE) is False
    with pytest.raises(InvalidTransitionError, match="PROIBID"):
        sm.transition_to(WaveState.EXECUTE)


def test_delivery_wave_supports_refinement_stage():
    sm = TuringStateMachine(wave_id="ONDA-001", initial_state=WaveState.PLAN)
    assert sm.wave_type == WaveType.DELIVERY_WAVE

    # PLAN -> REFINEMENT (PBB)
    assert sm.can_transition_to(WaveState.REFINEMENT) is True
    sm.transition_to(WaveState.REFINEMENT)
    assert sm.current_state == WaveState.REFINEMENT
    assert sm.current_phase == WavePhase.UPSTREAM

    # REFINEMENT -> EXECUTE
    assert sm.can_transition_to(WaveState.EXECUTE) is True
    sm.transition_to(WaveState.EXECUTE)
    assert sm.current_state == WaveState.EXECUTE
    assert sm.current_phase == WavePhase.DOWNSTREAM

    # EXECUTE -> VALIDATE
    sm.transition_to(WaveState.VALIDATE)
    assert sm.current_state == WaveState.VALIDATE
    assert sm.current_phase == WavePhase.DOWNSTREAM

    # VALIDATE -> COMPLETED
    sm.transition_to(WaveState.COMPLETED)
    assert sm.current_state == WaveState.COMPLETED
