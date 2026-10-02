"""Turing Gates Engine — Validação Determinística de Templates, Selos e Handoffs (ST-003)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class GateStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SealType(str, Enum):
    TECH_LEAD = "TECH_LEAD"
    VALIDATOR = "VALIDATOR"


@dataclass(frozen=True)
class GateEvaluation:
    status: GateStatus
    issues: list[str] = field(default_factory=list)
    seal_found: bool = False
    details: str = ""


@dataclass(frozen=True)
class HandoffEvaluation:
    status: GateStatus
    consumer: str
    producer: str
    artifact_name: str
    rejection_reason: str | None = None
    required_improvements: list[str] = field(default_factory=list)


class TemplateGate:
    """Valida deterministamente se um artefato existe e cumpre as seções do template."""

    def evaluate(
        self,
        file_path: str,
        required_sections: list[str] | None = None,
        min_words: int = 10,
    ) -> GateEvaluation:
        required_sections = required_sections or []
        issues: list[str] = []

        if not os.path.exists(file_path):
            return GateEvaluation(
                status=GateStatus.REJECTED,
                issues=[f"Arquivo não encontrado: {file_path}"],
            )

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as exc:
            return GateEvaluation(
                status=GateStatus.REJECTED,
                issues=[f"Erro ao ler arquivo {file_path}: {exc}"],
            )

        words = [w for w in content.split() if len(w) > 2]
        if len(words) < min_words:
            issues.append(f"Densidade insuficiente ({len(words)} palavras substantivas, mínimo: {min_words})")

        content_lower = content.lower()
        for sec in required_sections:
            if sec.lower() not in content_lower:
                issues.append(f"Seção obrigatória ausente: '{sec}'")

        if issues:
            return GateEvaluation(status=GateStatus.REJECTED, issues=issues)

        return GateEvaluation(status=GateStatus.APPROVED, issues=[])


class SealGate:
    """Fiscaliza deterministamente a presença e autenticidade de selos formais."""

    SEAL_PATTERNS: ClassVar[dict[SealType, str]] = {
        SealType.TECH_LEAD: r"\[SELO TECH LEAD:\s*APROVADO\]",
        SealType.VALIDATOR: r"\[SELO VALIDATOR:\s*HOMOLOGADO\]",
    }

    def evaluate(self, content: str, seal_type: SealType) -> GateEvaluation:
        pattern = self.SEAL_PATTERNS.get(seal_type, "")
        if pattern and re.search(pattern, content, re.IGNORECASE):
            return GateEvaluation(
                status=GateStatus.APPROVED,
                seal_found=True,
                details=f"Selo {seal_type.value} aprovado com sucesso.",
            )

        return GateEvaluation(
            status=GateStatus.REJECTED,
            seal_found=False,
            issues=[f"Selo obrigatório {seal_type.value} não encontrado ou pendente de aprovação."],
        )


class ConsumerHandoffGate:
    """Portão de Handoff Semântico onde o Agente Consumidor valida a qualidade dos insumos."""

    def evaluate_input(
        self,
        consumer: str,
        producer: str,
        artifact_name: str,
        content: str,
        required_topics: list[str] | None = None,
        min_words: int = 15,
    ) -> HandoffEvaluation:
        required_topics = required_topics or []
        improvements: list[str] = []

        words = [w for w in content.split() if len(w) > 2]
        if len(words) < min_words:
            improvements.append(
                f"Densidade semântica rasa ({len(words)} palavras, mínimo esperado: {min_words})"
            )

        content_lower = content.lower()
        for topic in required_topics:
            if topic.lower() not in content_lower:
                improvements.append(f"Tópico indispensável ausente: '{topic}'")

        if improvements:
            return HandoffEvaluation(
                status=GateStatus.REJECTED,
                consumer=consumer,
                producer=producer,
                artifact_name=artifact_name,
                rejection_reason=f"Insumo rejeitado pelo agente consumidor {consumer}.",
                required_improvements=improvements,
            )

        return HandoffEvaluation(
            status=GateStatus.APPROVED,
            consumer=consumer,
            producer=producer,
            artifact_name=artifact_name,
        )

    def build_rework_prompt(self, evaluation: HandoffEvaluation) -> str:
        improvements_text = "\n".join(f"  • {item}" for item in evaluation.required_improvements)
        return (
            f"Atenção {evaluation.producer}: seu documento '{evaluation.artifact_name}' foi avaliado "
            f"pelo agente consumidor {evaluation.consumer} e REPROVADO pelas seguintes pendências:\n"
            f"{improvements_text}\n\n"
            f"Por favor, revise o documento suprindo essas lacunas antes do avanço do fluxo."
        )
