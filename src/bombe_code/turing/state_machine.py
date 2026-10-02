"""Máquina de Estados da ONDA no Turing Runtime (ST-002)."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import ClassVar


class WaveState(str, Enum):
    DISCUSS = "DISCUSS"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    COMPLETED = "COMPLETED"


class AutonomyMode(str, Enum):
    AUTO = "AUTO"
    SEMI_AUTO = "SEMI_AUTO"
    MANUAL = "MANUAL"


class EngineeringMode(str, Enum):
    TDD_CODE = "tdd-code"
    VIBE_CODE = "vibe-code"


class InvalidTransitionError(ValueError):
    """Exceção levantada quando uma transição ilegal de estado da ONDA é solicitada."""


class TuringStateMachine:
    """Máquina de estados finita determinística que rege o ciclo de vida da ONDA."""

    VALID_TRANSITIONS: ClassVar[dict[WaveState, list[WaveState]]] = {
        WaveState.DISCUSS: [WaveState.PLAN],
        WaveState.PLAN: [WaveState.EXECUTE, WaveState.DISCUSS],
        WaveState.EXECUTE: [WaveState.VALIDATE, WaveState.PLAN],
        WaveState.VALIDATE: [WaveState.COMPLETED, WaveState.EXECUTE],
        WaveState.COMPLETED: [],
    }

    def __init__(
        self,
        wave_id: str,
        initial_state: WaveState = WaveState.DISCUSS,
        autonomy_mode: AutonomyMode = AutonomyMode.AUTO,
        engineering_mode: EngineeringMode = EngineeringMode.TDD_CODE,
        on_state_change: Callable[[WaveState, WaveState], None] | None = None,
    ) -> None:
        self.wave_id = wave_id
        self._current_state = initial_state
        self._autonomy_mode = autonomy_mode
        self._engineering_mode = engineering_mode
        self._on_state_change = on_state_change

    @property
    def current_state(self) -> WaveState:
        return self._current_state

    @property
    def autonomy_mode(self) -> AutonomyMode:
        return self._autonomy_mode

    @property
    def engineering_mode(self) -> EngineeringMode:
        return self._engineering_mode

    def set_autonomy_mode(self, mode: AutonomyMode) -> None:
        self._autonomy_mode = mode

    def set_engineering_mode(self, mode: EngineeringMode) -> None:
        self._engineering_mode = mode

    def can_transition_to(self, target_state: WaveState) -> bool:
        return target_state in self.VALID_TRANSITIONS.get(self._current_state, [])

    def transition_to(self, target_state: WaveState) -> None:
        if not self.can_transition_to(target_state):
            raise InvalidTransitionError(
                f"Transição inválida de {self._current_state.value} para {target_state.value} na onda {self.wave_id}."
            )

        old_state = self._current_state
        self._current_state = target_state

        if self._on_state_change:
            self._on_state_change(old_state, target_state)
