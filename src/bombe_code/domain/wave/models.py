"""Modelos, Entidades e Value Objects do Domínio da ONDA (Wave Domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class WaveState(str, Enum):
    """Estágios determinísticos do ciclo de vida da ONDA."""

    # Onda Zero (Upstream Greenfield)
    DISCOVERY = "DISCOVERY"
    INCEPTION = "INCEPTION"

    # Ondas de Entrega (1..N e Brownfield)
    PLAN = "PLAN"
    REFINEMENT = "REFINEMENT"
    EXECUTE = "EXECUTE"
    VALIDATE = "VALIDATE"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

    # Aliases de compatibilidade
    DISCUSS = "DISCUSS"
    CYCLE = "CYCLE"
    REVIEW = "REVIEW"

    @classmethod
    def from_str(cls, val: str) -> WaveState:
        v = (val or "").strip().upper()
        if v in ("DISCOVERY", "DISCUSS"):
            return cls.DISCOVERY if v == "DISCOVERY" else cls.DISCUSS
        if v == "INCEPTION":
            return cls.INCEPTION
        if v == "REFINEMENT":
            return cls.REFINEMENT
        if v == "PLAN":
            return cls.PLAN
        if v in ("EXECUTE", "CYCLE"):
            return cls.EXECUTE
        if v in ("VALIDATE", "REVIEW"):
            return cls.VALIDATE
        if v in ("END", "DONE", "COMPLETED"):
            return cls.COMPLETED
        return cls.DISCOVERY


class AutonomyMode(str, Enum):
    """Modos de autonomia operacional da ONDA."""

    AUTO = "AUTO"
    SEMI_AUTO = "SEMI_AUTO"
    MANUAL = "MANUAL"

    @classmethod
    def from_str(cls, val: str) -> AutonomyMode:
        v = (val or "").strip().upper().replace("-", "_")
        if "SEMI" in v:
            return cls.SEMI_AUTO
        if "MANUAL" in v:
            return cls.MANUAL
        return cls.AUTO


class EngineeringMode(str, Enum):
    """Modo de disciplina de engenharia."""

    TDD = "tdd-code"
    VIBE = "vibe-code"
    SPEC = "spec-code"

    @classmethod
    def from_str(cls, val: str) -> EngineeringMode:
        v = (val or "").strip().lower()
        if "vibe" in v:
            return cls.VIBE
        if "spec" in v:
            return cls.SPEC
        return cls.TDD


class DeliveryTarget(str, Enum):
    """Alvo de profundidade de entrega da ONDA."""

    POC = "poc"
    MVP = "mvp"
    PRODUCTION = "production"

    @classmethod
    def from_str(cls, val: str) -> DeliveryTarget:
        v = (val or "").strip().lower()
        if v in ("poc", "prototipo"):
            return cls.POC
        if v in ("prod", "production", "enterprise"):
            return cls.PRODUCTION
        return cls.MVP


@dataclass(frozen=True)
class WaveId:
    """Value Object representando o identificador de uma ONDA."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not isinstance(self.value, str):
            object.__setattr__(self, "value", "ONDA-001")
        else:
            cleaned = self.value.strip().upper()
            if not cleaned.startswith(("ONDA-", "WAVE-")):
                cleaned = f"ONDA-{cleaned}"
            object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass
class StoryCard:
    """Entidade representando um cartão de história técnica no Kanban da ONDA."""

    story_id: str
    title: str
    status: str = "BACKLOG"
    assigned_to: str = "@barbara"
    blocked_by: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_blocked(self) -> bool:
        return self.status == "BLOCKED" or bool(self.blocked_by)

    def block(self, reason: str, agent: str = "@turing") -> None:
        self.status = "BLOCKED"
        self.blocked_by = f"{agent}: {reason}"

    def unblock(self) -> None:
        self.status = "IN_PROGRESS"
        self.blocked_by = None


@dataclass
class GateEvaluationResult:
    """Value object contendo o resultado da avaliação de um Quality Gate."""

    gate_name: str
    passed: bool
    reason: str = ""
    veto_reasons: list[str] = field(default_factory=list)
    score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Wave:
    """Agregado Raiz (Aggregate Root) do ciclo de vida da ONDA."""

    wave_id: WaveId
    state: WaveState = WaveState.DISCUSS
    autonomy_mode: AutonomyMode = AutonomyMode.AUTO
    engineering_mode: EngineeringMode = EngineeringMode.TDD
    delivery_target: DeliveryTarget = DeliveryTarget.MVP
    project_dir: str = "."
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    telemetry: dict[str, Any] = field(default_factory=dict)

    def can_transition_to(self, target_state: WaveState) -> bool:
        # Suporta tanto o fluxo da Onda Zero (DISCOVERY -> INCEPTION -> COMPLETED)
        # quanto o fluxo das Ondas de Entrega (PLAN -> REFINEMENT -> EXECUTE -> VALIDATE -> COMPLETED)
        allowed_transitions: dict[WaveState, set[WaveState]] = {
            WaveState.DISCOVERY: {
                WaveState.INCEPTION,
                WaveState.PLAN,
                WaveState.COMPLETED,
                WaveState.BLOCKED,
            },
            WaveState.DISCUSS: {
                WaveState.PLAN,
                WaveState.INCEPTION,
                WaveState.COMPLETED,
                WaveState.BLOCKED,
            },
            WaveState.INCEPTION: {
                WaveState.COMPLETED,
                WaveState.DISCOVERY,
                WaveState.PLAN,
                WaveState.BLOCKED,
            },
            WaveState.PLAN: {
                WaveState.REFINEMENT,
                WaveState.EXECUTE,
                WaveState.COMPLETED,
                WaveState.DISCUSS,
                WaveState.BLOCKED,
            },
            WaveState.REFINEMENT: {WaveState.EXECUTE, WaveState.PLAN, WaveState.BLOCKED},
            WaveState.EXECUTE: {
                WaveState.VALIDATE,
                WaveState.REFINEMENT,
                WaveState.PLAN,
                WaveState.BLOCKED,
                WaveState.COMPLETED,
            },
            WaveState.VALIDATE: {WaveState.COMPLETED, WaveState.EXECUTE, WaveState.BLOCKED},
            WaveState.COMPLETED: {
                WaveState.DISCOVERY,
                WaveState.DISCUSS,
                WaveState.PLAN,
                WaveState.EXECUTE,
            },
            WaveState.BLOCKED: {
                WaveState.DISCOVERY,
                WaveState.INCEPTION,
                WaveState.PLAN,
                WaveState.REFINEMENT,
                WaveState.EXECUTE,
                WaveState.VALIDATE,
            },
        }
        return target_state in allowed_transitions.get(self.state, set())

    def transition_to(self, target_state: WaveState) -> None:
        if not self.can_transition_to(target_state):
            raise ValueError(
                f"Transição ilegal no domínio da ONDA: {self.state.value} -> {target_state.value}"
            )
        self.state = target_state
        if target_state == WaveState.COMPLETED:
            self.completed_at = datetime.now(UTC).isoformat()
