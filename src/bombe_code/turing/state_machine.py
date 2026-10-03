"""Máquina de Estados da ONDA no Turing Runtime (ST-002)."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import ClassVar


class WavePhase(str, Enum):
    """Fases canônicas do Bombe Code (exatamente duas)."""

    UPSTREAM = "UPSTREAM"
    DOWNSTREAM = "DOWNSTREAM"


class DiscussSubStage(str, Enum):
    """Sub-etapas determinísticas de DISCUSS."""

    RESEARCH = "research"
    ELICITATION = "elicitation"
    SPEC = "spec"


class PlanSubStage(str, Enum):
    """Sub-etapas determinísticas de PLAN."""

    EPICS = "epics"
    JOURNEY = "journey"
    ARCHITECTURE = "architecture"
    DATABASE = "database"
    STORIES = "stories"


class WaveType(str, Enum):
    """Classificação ontológica da ONDA."""

    WAVE_ZERO = "WAVE_ZERO"  # Greenfield Lean Inception Macro (estritamente UPSTREAM)
    DELIVERY_WAVE = "DELIVERY_WAVE"  # Ondas de Entrega 1..N e Brownfield (PLAN ➔ REFINEMENT ➔ EXECUTE ➔ VALIDATE)


class WaveState(str, Enum):
    DISCOVERY = "DISCOVERY"
    INCEPTION = "INCEPTION"
    DISCUSS = "DISCUSS"
    PLAN = "PLAN"
    REFINEMENT = "REFINEMENT"
    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    COMPLETED = "COMPLETED"


# Alias para a terminologia oficial de Etapa da ONDA
TuringStage = WaveState


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

    # Transições padrão para Ondas de Entrega (1..N e Brownfield)
    DELIVERY_TRANSITIONS: ClassVar[dict[WaveState, list[WaveState]]] = {
        WaveState.DISCUSS: [WaveState.PLAN],
        WaveState.DISCOVERY: [WaveState.PLAN],
        WaveState.PLAN: [WaveState.REFINEMENT, WaveState.EXECUTE, WaveState.DISCUSS],
        WaveState.REFINEMENT: [WaveState.EXECUTE, WaveState.PLAN],
        WaveState.EXECUTE: [WaveState.VALIDATE, WaveState.REFINEMENT, WaveState.PLAN],
        WaveState.VALIDATE: [WaveState.COMPLETED, WaveState.EXECUTE],
        WaveState.COMPLETED: [],
    }

    # Transições exclusivas para Onda Zero (estritamente UPSTREAM: DISCOVERY ➔ INCEPTION)
    WAVE_ZERO_TRANSITIONS: ClassVar[dict[WaveState, list[WaveState]]] = {
        WaveState.DISCOVERY: [WaveState.INCEPTION, WaveState.PLAN],
        WaveState.INCEPTION: [WaveState.COMPLETED, WaveState.DISCOVERY],
        WaveState.DISCUSS: [WaveState.PLAN, WaveState.INCEPTION],
        WaveState.PLAN: [WaveState.COMPLETED, WaveState.DISCUSS, WaveState.DISCOVERY],
        WaveState.COMPLETED: [],
    }

    VALID_TRANSITIONS = DELIVERY_TRANSITIONS

    def __init__(
        self,
        wave_id: str,
        initial_state: WaveState = WaveState.DISCUSS,
        autonomy_mode: AutonomyMode = AutonomyMode.AUTO,
        engineering_mode: EngineeringMode = EngineeringMode.TDD_CODE,
        on_state_change: Callable[[WaveState, WaveState], None] | None = None,
        wave_type: WaveType | None = None,
    ) -> None:
        self.wave_id = wave_id
        norm_id = wave_id.upper().strip()
        if wave_type is not None:
            self._wave_type = wave_type
        elif norm_id in (
            "ONDA-0",
            "ONDA-00",
            "ONDA-000",
            "WAVE-0",
            "WAVE-00",
            "WAVE-000",
        ) or norm_id.startswith(("ONDA-000-", "WAVE-000-", "ONDA-0-", "WAVE-0-")):
            self._wave_type = WaveType.WAVE_ZERO
        else:
            self._wave_type = WaveType.DELIVERY_WAVE

        self._current_state = initial_state
        self._autonomy_mode = autonomy_mode
        self._engineering_mode = engineering_mode
        self._on_state_change = on_state_change

    @property
    def wave_type(self) -> WaveType:
        return self._wave_type

    @property
    def current_state(self) -> WaveState:
        return self._current_state

    @property
    def current_phase(self) -> WavePhase:
        """Retorna a Fase ativa (UPSTREAM ou DOWNSTREAM)."""
        if self._current_state in (
            WaveState.DISCOVERY,
            WaveState.INCEPTION,
            WaveState.DISCUSS,
            WaveState.PLAN,
            WaveState.REFINEMENT,
        ):
            return WavePhase.UPSTREAM
        return WavePhase.DOWNSTREAM

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

    def _get_transitions(self) -> dict[WaveState, list[WaveState]]:
        if self._wave_type == WaveType.WAVE_ZERO:
            return self.WAVE_ZERO_TRANSITIONS
        return self.DELIVERY_TRANSITIONS

    def can_transition_to(self, target_state: WaveState) -> bool:
        transitions = self._get_transitions()
        return target_state in transitions.get(self._current_state, [])

    def transition_to(self, target_state: WaveState) -> None:
        if not self.can_transition_to(target_state):
            if self._wave_type == WaveType.WAVE_ZERO and target_state in (
                WaveState.EXECUTE,
                WaveState.VALIDATE,
            ):
                raise InvalidTransitionError(
                    f"Transição para {target_state.value} é terminantemente PROIBIDA na Onda Zero ({self.wave_id}). "
                    f"A Onda Zero é estritamente UPSTREAM (Lean Inception Macro: DISCOVERY ➔ INCEPTION)."
                )
            raise InvalidTransitionError(
                f"Transição inválida de {self._current_state.value} para {target_state.value} na onda {self.wave_id} (tipo: {self._wave_type.value})."
            )

        old_state = self._current_state
        self._current_state = target_state

        if self._on_state_change:
            self._on_state_change(old_state, target_state)
