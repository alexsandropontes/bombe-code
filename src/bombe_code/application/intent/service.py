"""Serviço de Aplicação para Despacho e Classificação de Intenções (Intent Application Service)."""

from __future__ import annotations

import logging
from typing import Any

from bombe_code.domain.intent.models import TuringAction
from bombe_code.turing.waiter import TuringWaiter

logger = logging.getLogger(__name__)


class IntentApplicationService:
    """Caso de uso de alto nível para recepção determinística de mensagens e intenções."""

    def __init__(self, waiter: TuringWaiter | None = None) -> None:
        self.waiter = waiter or TuringWaiter()

    async def attend(
        self,
        text: str,
        stage: str = "DISCUSS",
        is_greenfield: bool = False,
        context: dict[str, Any] | None = None,
    ) -> TuringAction:
        """Processa a mensagem do usuário via motor de 3 tiers e retorna a ação determinística."""
        raw_action = await self.waiter.attend(
            user_input=text,
            stage=stage,
            is_greenfield=is_greenfield,
        )
        return TuringAction(
            action_type=getattr(raw_action, "action_type", "command"),
            command=raw_action.command,
            intention=raw_action.intention,
            reason=getattr(raw_action, "reason", ""),
            target_stage=getattr(raw_action, "target_stage", None),
            metadata=getattr(raw_action, "metadata", {}),
        )
