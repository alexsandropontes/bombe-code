"""Roda de Samba dos Providers — Sistema Enterprise de Rotação e Failover de Provedores LLM.

Permite configurar múltiplos provedores com ordem de prioridade (Z.ai, Groq, OpenRouter, OpenAI, llama.cpp).
Quando um provedor estoura cota ou atinge rate limit, a Roda de Samba registra o horário exato de retorno
(com cálculo de fuso horário), migra dinamicamente para o próximo provedor disponível e, opcionalmente,
aciona um timer de espera inteligente quando todos os provedores estão em resfriamento.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from bombe_code.llm.quota_detector import QuotaResetInfo

logger = logging.getLogger(__name__)


@dataclass
class ProviderSlot:
    """Representa um slot de provedor configurado na Roda de Samba."""

    name: str
    model: str
    priority: int = 1
    enabled: bool = True
    exhausted_until_utc: datetime | None = None
    last_error: str | None = None
    total_calls: int = 0
    total_exhausted_events: int = 0

    def is_available(self, current_time: datetime | None = None) -> bool:
        """Verifica se o provedor está habilitado e não está em período de esgotamento/cooldown."""
        if not self.enabled:
            return False
        if self.exhausted_until_utc is None:
            return True
        now = current_time or datetime.now(timezone.utc)
        return now >= self.exhausted_until_utc

    def seconds_until_available(self, current_time: datetime | None = None) -> float:
        """Retorna quantos segundos faltam para o provedor voltar a estar disponível (ou 0 se já disponível)."""
        if self.is_available(current_time):
            return 0.0
        if self.exhausted_until_utc is None:
            return 0.0
        now = current_time or datetime.now(timezone.utc)
        diff = (self.exhausted_until_utc - now).total_seconds()
        return max(0.0, diff)


@dataclass
class RodaDeSambaConfig:
    """Configuração da governança de rotação e timer."""

    enabled: bool = True
    auto_timer: bool = False
    max_timer_wait_seconds: float = 900.0  # Máximo de 15 minutos de espera automática


class RodaDeSamba:
    """Orquestrador da Roda de Samba de Provedores LLM."""

    def __init__(
        self,
        slots: list[ProviderSlot] | None = None,
        config: RodaDeSambaConfig | None = None,
    ) -> None:
        self.slots: list[ProviderSlot] = sorted(slots or [], key=lambda s: s.priority)
        self.config = config or RodaDeSambaConfig()
        self.current_slot_index: int = 0

    def add_slot(self, slot: ProviderSlot) -> None:
        """Adiciona um provedor à Roda de Samba e reordena por prioridade."""
        self.slots.append(slot)
        self.slots.sort(key=lambda s: s.priority)

    def get_active_slot(self, current_time: datetime | None = None) -> ProviderSlot | None:
        """Retorna o provedor de maior prioridade atualmente disponível."""
        if not self.slots:
            return None

        # 1. Procura primeiro na ordem natural de prioridade
        for slot in self.slots:
            if slot.is_available(current_time):
                return slot

        return None

    def report_quota_exhausted(
        self,
        slot: ProviderSlot,
        quota_info: QuotaResetInfo,
        current_time: datetime | None = None,
    ) -> ProviderSlot | None:
        """Registra o esgotamento do slot e roda o samba para o próximo disponível."""
        slot.total_exhausted_events += 1
        slot.last_error = quota_info.human_message or quota_info.raw_message

        # Define a data/hora de recuperação
        if quota_info.reset_at_utc:
            slot.exhausted_until_utc = quota_info.reset_at_utc
        elif quota_info.retry_after_seconds:
            now = current_time or datetime.now(timezone.utc)
            slot.exhausted_until_utc = now + quota_info.retry_after_seconds  # type: ignore[operator]
        else:
            # Fallback padrão de cooldown: 60 segundos
            from datetime import timedelta
            now = current_time or datetime.now(timezone.utc)
            slot.exhausted_until_utc = now + timedelta(seconds=60)

        logger.warning(
            "🪘 [RODA DE SAMBA] Provedor '%s' (%s) esgotou cota. %s",
            slot.name,
            slot.model,
            quota_info.human_message,
        )

        # Procura o próximo disponível
        next_slot = self.get_active_slot(current_time)
        if next_slot and next_slot != slot:
            logger.info(
                "🪘 [RODA DE SAMBA] Migrando execução para o provedor '%s' (%s) [Prioridade %d].",
                next_slot.name,
                next_slot.model,
                next_slot.priority,
            )
            return next_slot

        logger.warning(
            "🪘 [RODA DE SAMBA] Todos os %d provedores configurados estão temporariamente em resfriamento/esgotados.",
            len(self.slots),
        )
        return None

    def get_min_wait_seconds(self, current_time: datetime | None = None) -> float:
        """Calcula o menor tempo de espera entre todos os provedores em resfriamento."""
        if not self.slots:
            return 0.0
        waits = [s.seconds_until_available(current_time) for s in self.slots if s.enabled]
        if not waits:
            return 0.0
        return min(waits)

    def should_wait_timer(self, current_time: datetime | None = None) -> tuple[bool, float, str]:
        """Avalia se a política permite disparar o timer de espera automática.

        Retorna (deve_esperar, segundos_espera, motivo).
        """
        if not self.config.auto_timer:
            return False, 0.0, "Timer automático desabilitado na configuração."

        min_wait = self.get_min_wait_seconds(current_time)
        if min_wait <= 0.0:
            return False, 0.0, "Provedor já disponível, não é necessário aguardar."

        if min_wait > self.config.max_timer_wait_seconds:
            mins = round(min_wait / 60, 1)
            max_mins = round(self.config.max_timer_wait_seconds / 60, 1)
            return (
                False,
                min_wait,
                f"Tempo de espera ({mins}m) excede o limite máximo configurado ({max_mins}m).",
            )

        mins = round(min_wait / 60, 1)
        return True, min_wait, f"Timer autorizado: aguardando {min_wait:.0f}s ({mins}m) para recuperação do provedor."
