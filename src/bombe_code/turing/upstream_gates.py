"""Gates Determinísticos de Upstream do Turing Runtime (ST-027).

Valida os artefatos de PRD, Jornada do Usuário, Arquitetura e Stories
antes de autorizar a transição para a etapa EXECUTE da ONDA.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class PRDQualityGate:
    """Valida a integridade estrutural e técnica do PRD."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Visão Geral",
        "Problema",
        "Personas",
        "Critérios RICE",
        "MVP Operacional",
    ]

    def evaluate(self, content: str) -> dict[str, Any]:
        normalized = content.lower()
        missing = []
        for sec in self.REQUIRED_SECTIONS:
            # Checa correspondência flexível com sinônimos semânticos de engenharia de produto
            keywords = [sec.lower()]
            if "visão" in sec.lower():
                keywords.extend(
                    [
                        "visão",
                        "visao",
                        "visão do produto",
                        "visao do produto",
                        "overview",
                        "visão geral",
                    ]
                )
            if "problema" in sec.lower():
                keywords.extend(
                    [
                        "problema",
                        "dor",
                        "dores",
                        "necessidade",
                        "contexto",
                        "motivação",
                        "motivacao",
                    ]
                )
            if "personas" in sec.lower():
                keywords.extend(
                    [
                        "persona",
                        "personas",
                        "público",
                        "publico",
                        "usuário",
                        "usuario",
                        "stakeholder",
                    ]
                )
            if "rice" in sec.lower():
                keywords.extend(
                    ["rice", "wsjf", "moscow", "ice", "priorização", "priorizacao", "prioridade"]
                )
            if "mvp" in sec.lower():
                keywords.extend(["mvp", "faseamento", "escopo mínimo", "operacional", "f0"])

            if not any(kw in normalized for kw in keywords):
                missing.append(sec)

        approved = len(missing) == 0
        return {
            "approved": approved,
            "gate": "PRDQualityGate",
            "missing_sections": missing,
            "message": (
                "PRD aprovado com todas as seções obrigatórias."
                if approved
                else f"PRD reprovado. Faltam: {', '.join(missing)}."
            ),
        }


class JourneyGate:
    """Valida o mapeamento de jornadas e telas do usuário (@alan)."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Entry Points",
        "Fluxo de Navegação",
        "Telas",
    ]

    def evaluate(self, content: str) -> dict[str, Any]:
        normalized = content.lower()
        missing = []
        for sec in self.REQUIRED_SECTIONS:
            keywords = [sec.lower()]
            if "telas" in sec.lower():
                keywords.extend(["tela", "componentes"])
            if "navegação" in sec.lower():
                keywords.extend(["navegacao", "fluxo"])

            if not any(kw in normalized for kw in keywords):
                missing.append(sec)

        approved = len(missing) == 0
        return {
            "approved": approved,
            "gate": "JourneyGate",
            "missing_sections": missing,
            "message": (
                "Jornada do usuário validada com sucesso."
                if approved
                else f"Jornada reprovada. Faltam: {', '.join(missing)}."
            ),
        }


class ArchitectureGate:
    """Valida as decisões de arquitetura e tecnologia (@ieru / @unclebob)."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Decisões Arquiteturais",
        "Stack",
    ]

    def evaluate(self, content: str, project_dir: Any = None) -> dict[str, Any]:
        from ..starters.decision import load_starter_decision

        normalized = content.lower()
        missing = []
        for sec in self.REQUIRED_SECTIONS:
            keywords = [sec.lower()]
            if "decisões" in sec.lower():
                keywords.extend(["decisoes", "arquitetura", "adr"])
            if "stack" in sec.lower():
                keywords.extend(["tecnologia", "backend", "frontend"])

            if not any(kw in normalized for kw in keywords):
                missing.append(sec)

        starter_info = None
        if project_dir:
            starter_data = load_starter_decision(project_dir)
            if starter_data:
                s_id = str(starter_data.get("starter_id", "")).lower()
                starter_info = starter_data
                # Checa se o ADR ou documento referencia o starter selecionado
                if (
                    s_id
                    and s_id not in normalized
                    and "starter" not in normalized
                    and "template" not in normalized
                ):
                    missing.append(f"Referência ao Starter selecionado ({s_id})")

        approved = len(missing) == 0
        return {
            "approved": approved,
            "gate": "ArchitectureGate",
            "missing_sections": missing,
            "starter_info": starter_info,
            "message": (
                "Arquitetura aprovada com decisões documentadas."
                if approved
                else f"Arquitetura reprovada. Faltam: {', '.join(missing)}."
            ),
        }


class StoryDoRGate:
    """Valida a conformidade de histórias de usuário com Definition of Ready (DoR)."""

    REQUIRED_ELEMENTS: ClassVar[list[str]] = [
        "INVEST",
        "Critérios de Aceite",
        "Dado",
        "Quando",
        "Então",
    ]

    def evaluate(self, content: str) -> dict[str, Any]:
        normalized = content.lower()
        missing = []

        # Validação de INVEST
        if "invest" not in normalized:
            missing.append("INVEST")

        # Validação de Critérios de Aceite
        if "critérios de aceite" not in normalized and "criterios de aceite" not in normalized:
            missing.append("Critérios de Aceite")

        # Validação de BDD (Dado/Quando/Então ou Given/When/Then)
        has_given = "dado" in normalized or "given" in normalized
        has_when = "quando" in normalized or "when" in normalized
        has_then = "então" in normalized or "entao" in normalized or "then" in normalized

        if not (has_given and has_when and has_then):
            missing.append("Cenários BDD (Dado/Quando/Então)")

        approved = len(missing) == 0
        return {
            "approved": approved,
            "gate": "StoryDoRGate",
            "missing_elements": missing,
            "message": (
                "Story em conformidade com DoR e INVEST."
                if approved
                else f"Story não atende ao DoR. Faltam: {', '.join(missing)}."
            ),
        }


class ViabilityQualityGate:
    """Valida o parecer de viabilidade técnica e estratégica (@meira)."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Viabilidade",
        "Riscos",
    ]

    def evaluate(self, content: str) -> dict[str, Any]:
        normalized = content.lower()
        missing = []
        for sec in self.REQUIRED_SECTIONS:
            keywords = [sec.lower()]
            if "viabilidade" in sec.lower():
                keywords.extend(["viab", "parecer", "viavel", "estratég"])
            if "riscos" in sec.lower():
                keywords.extend(["risco", "mitiga", "tradeoff", "trade-off", "seguran"])
            if not any(kw in normalized for kw in keywords):
                missing.append(sec)

        approved = len(missing) == 0
        return {
            "approved": approved,
            "gate": "ViabilityQualityGate",
            "missing_sections": missing,
            "message": (
                "Viabilidade técnica aprovada."
                if approved
                else f"Viabilidade reprovada. Faltam: {', '.join(missing)}."
            ),
        }


class DatabaseQualityGate:
    """Valida a modelagem relacional e schemas de banco (@codd)."""

    REQUIRED_SECTIONS: ClassVar[list[str]] = [
        "Schema",
        "Constraints",
    ]

    def evaluate(self, content: str) -> dict[str, Any]:
        normalized = content.lower()
        missing = []
        for sec in self.REQUIRED_SECTIONS:
            # Schemas, tabelas, ddl, constraints, chaves
            keywords = [sec.lower()]
            if "schema" in sec.lower():
                keywords.extend(["tabela", "ddl", "create table", "modelo"])
            if "constraints" in sec.lower():
                keywords.extend(
                    ["foreign key", "primary key", "constraint", "integridade", "índice", "indice"]
                )

            if not any(kw in normalized for kw in keywords):
                missing.append(sec)

        approved = len(missing) == 0
        return {
            "approved": approved,
            "gate": "DatabaseQualityGate",
            "missing_sections": missing,
            "message": (
                "Modelagem de dados e schema aprovados."
                if approved
                else f"Modelagem reprovada. Faltam: {', '.join(missing)}."
            ),
        }
