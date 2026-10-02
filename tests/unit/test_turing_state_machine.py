"""Testes unitários para a TuringStateMachine (ST-002)."""

from __future__ import annotations

import pytest

from bombe_code.turing.state_machine import (
    AutonomyMode,
    EngineeringMode,
    InvalidTransitionError,
    TuringStateMachine,
    WaveState,
)


def test_initial_state_and_defaults():
    sm = TuringStateMachine(wave_id="ONDA-002")
    assert sm.wave_id == "ONDA-002"
    assert sm.current_state == WaveState.DISCUSS
    assert sm.autonomy_mode == AutonomyMode.AUTO
    assert sm.engineering_mode == EngineeringMode.TDD_CODE


def test_valid_transitions_in_auto_mode():
    sm = TuringStateMachine(wave_id="ONDA-002")
    # DISCUSS -> PLAN
    sm.transition_to(WaveState.PLAN)
    assert sm.current_state == WaveState.PLAN

    # PLAN -> EXECUTE
    sm.transition_to(WaveState.EXECUTE)
    assert sm.current_state == WaveState.EXECUTE

    # EXECUTE -> VALIDATE
    sm.transition_to(WaveState.VALIDATE)
    assert sm.current_state == WaveState.VALIDATE

    # VALIDATE -> COMPLETED
    sm.transition_to(WaveState.COMPLETED)
    assert sm.current_state == WaveState.COMPLETED


def test_invalid_skip_transition_raises_error():
    sm = TuringStateMachine(wave_id="ONDA-002")
    # Tentativa de pular de DISCUSS direto para VALIDATE
    with pytest.raises(InvalidTransitionError):
        sm.transition_to(WaveState.VALIDATE)


def test_transition_listener_callback():
    events: list[tuple[WaveState, WaveState]] = []

    def on_change(old_state: WaveState, new_state: WaveState):
        events.append((old_state, new_state))

    sm = TuringStateMachine(wave_id="ONDA-002", on_state_change=on_change)
    sm.transition_to(WaveState.PLAN)

    assert len(events) == 1
    assert events[0] == (WaveState.DISCUSS, WaveState.PLAN)


def test_toggle_autonomy_mode():
    sm = TuringStateMachine(wave_id="ONDA-002")
    sm.set_autonomy_mode(AutonomyMode.MANUAL)
    assert sm.autonomy_mode == AutonomyMode.MANUAL


def test_toggle_engineering_mode():
    sm = TuringStateMachine(wave_id="ONDA-002")
    sm.set_engineering_mode(EngineeringMode.VIBE_CODE)
    assert sm.engineering_mode == EngineeringMode.VIBE_CODE
