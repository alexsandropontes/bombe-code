"""Porta de persistência do domínio da ONDA (Wave Repository Interface)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import StoryCard, Wave, WaveId


class WaveRepositoryInterface(ABC):
    """Contrato que qualquer adaptador de persistência da ONDA deve implementar."""

    @abstractmethod
    def save_wave(self, wave: Wave) -> None:
        """Persiste ou atualiza o estado de uma ONDA."""

    @abstractmethod
    def load_wave(self, wave_id: WaveId | str | None = None) -> Wave | None:
        """Carrega a ONDA ativa ou especificada."""

    @abstractmethod
    def save_card(self, wave_id: WaveId | str, card: StoryCard) -> None:
        """Persiste um cartão de história técnica."""

    @abstractmethod
    def list_cards(self, wave_id: WaveId | str) -> list[StoryCard]:
        """Lista os cartões associados a uma ONDA."""

    @abstractmethod
    def save_gate_evaluation(
        self, wave_id: WaveId | str, gate_name: str, evaluation: dict[str, Any]
    ) -> None:
        """Registra auditoria de passagem por um Quality Gate."""
