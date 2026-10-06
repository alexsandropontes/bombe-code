"""Entidades e Value Objects do Domínio de Intenções (Intent Domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentTier(str, Enum):
    """Níveis de resolução do despachante determinístico."""

    TIER_1_SLASH = "tier_1_slash"
    TIER_2_NLU_LOCAL = "tier_2_nlu_local"
    TIER_3_PROBABILISTIC = "tier_3_probabilistic"


@dataclass
class IntentResult:
    """Resultado da classificação de intenção do usuário."""

    intention: str
    confidence: float
    command: str | None = None
    stage: str | None = None
    tier: IntentTier = IntentTier.TIER_2_NLU_LOCAL
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TuringAction:
    """Ação determinística decidida pelo Turing Waiter."""

    action_type: str  # "command", "auto_advance", "clarify", "normal_prompt"
    command: str | None = None
    intention: str = "general"
    reason: str = ""
    target_stage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
