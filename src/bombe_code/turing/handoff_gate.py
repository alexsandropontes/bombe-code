"""Portão de Handoff Semântico entre Agentes Upstream/Downstream do Turing Runtime.
Inspirado na arquitetura determinística do Code Forge 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HandoffStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class HandoffEvaluation:
    """Avaliação de qualidade semântica dos insumos pelo agente consumidor."""

    status: HandoffStatus
    consumer_persona: str
    producer_persona: str
    artifact_path: str
    rejection_reason: str | None = None
    required_improvements: list[str] = field(default_factory=list)


class ConsumerHandoffGate:
    """Portão de Handoff Semântico entre Agentes.
    Garante que o consumidor só receba insumos com densidade e tópicos adequados.
    """

    def evaluate_input(
        self,
        consumer_persona: str,
        producer_persona: str,
        artifact_path: str,
        content: str,
        required_topics: list[str] | None = None,
        min_substantive_words: int = 15,
    ) -> HandoffEvaluation:
        required_topics = required_topics or []
        improvements: list[str] = []

        words = [w for w in content.split() if len(w) > 2]
        if len(words) < min_substantive_words:
            improvements.append(
                f"Densidade de conteúdo insuficiente ({len(words)} palavras substantivas, mínimo esperado: {min_substantive_words})"
            )

        lower_content = content.lower()
        for topic in required_topics:
            if topic.lower() not in lower_content:
                improvements.append(f"Tópico indispensável ausente: '{topic}'")

        if improvements:
            return HandoffEvaluation(
                status=HandoffStatus.BLOCKED,
                consumer_persona=consumer_persona,
                producer_persona=producer_persona,
                artifact_path=artifact_path,
                rejection_reason=(
                    f"Insumo incompleto: o agente consumidor {consumer_persona} identificou lacunas "
                    f"no documento gerado por {producer_persona}."
                ),
                required_improvements=improvements,
            )

        return HandoffEvaluation(
            status=HandoffStatus.ACCEPTED,
            consumer_persona=consumer_persona,
            producer_persona=producer_persona,
            artifact_path=artifact_path,
            rejection_reason=None,
            required_improvements=[],
        )

    def build_rework_prompt(
        self, evaluation: HandoffEvaluation, original_demand: str
    ) -> str:
        """Gera prompt formal de retrabalho para o agente produtor corrigir as lacunas."""
        lines: list[str] = [
            f"# Atenção {evaluation.producer_persona}: SOLICITAÇÃO DE RETRABALHO SEMÂNTICO (HANDOFF REJEITADO)",
            f"O agente sucessor ({evaluation.consumer_persona}) analisou o artefato `{evaluation.artifact_path}`.",
            "O conteúdo foi considerado insuficiente ou incompleto para prosseguir a esteira.",
            "",
            "## MOTIVO DO BLOQUEIO",
            evaluation.rejection_reason or "Qualidade semântica insuficiente.",
            "",
            "## MELHORIAS OBRIGATÓRIAS",
        ]
        for imp in evaluation.required_improvements:
            lines.append(f"- {imp}")

        lines.extend(
            [
                "",
                "## DEMANDA ORIGINAL",
                original_demand,
                "",
                f"Atualize o arquivo `{evaluation.artifact_path}` incorporando os pontos acima para desbloquear a esteira.",
            ]
        )
        return "\n".join(lines)
