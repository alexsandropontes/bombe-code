"""Gate de Revisão e Auditoria de Downstream do Turing (ST-028).

Verifica os pareceres de @aniche (qualidade de testes) e @unclebob (Clean Code/SOLID),
além da execução verde da suíte automatizada de testes do projeto.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TuringReviewGate:
    """Fiscaliza a aprovação conjunta de @aniche e @unclebob no ciclo de entrega."""

    def evaluate(
        self,
        aniche_verdict: dict[str, Any] | None,
        unclebob_verdict: dict[str, Any] | None,
        test_run_success: bool = True,
    ) -> dict[str, Any]:
        veto_reasons: list[str] = []

        # 1. Validação de testes automatizados
        if not test_run_success:
            veto_reasons.append("Suíte de testes automatizados falhou.")

        # 2. Parecer de @aniche (Test Architect)
        if not aniche_verdict or not aniche_verdict.get("approved"):
            notes = aniche_verdict.get("notes") if aniche_verdict else "Parecer ausente"
            veto_reasons.append(f"@aniche reprovou a entrega: {notes}")

        # 3. Parecer de @unclebob (Tech Lead & Clean Code)
        if not unclebob_verdict or not unclebob_verdict.get("approved"):
            notes = unclebob_verdict.get("notes") if unclebob_verdict else "Parecer ausente"
            veto_reasons.append(f"@unclebob reprovou a entrega: {notes}")

        approved = len(veto_reasons) == 0

        return {
            "approved": approved,
            "gate": "TuringReviewGate",
            "veto_reasons": veto_reasons,
            "message": (
                "Entrega homologada por @aniche e @unclebob com testes verdes."
                if approved
                else f"Entrega vetada pelo Turing: {' | '.join(veto_reasons)}"
            ),
        }
