"""Upstream Profiler — Classificação de Inception e Governança Adaptativa.

Avalia a origem do projeto (Greenfield vs Brownfield) e o Delivery Target (POC, PROTOTYPE, MVP, ENTERPRISE)
para determinar o nível adequado de Lean Inception e PBB a ser orquestrado por @caroli.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from bombe_code.turing.prompt_assembler import DeliveryTarget


class ProjectOrigin(str, Enum):
    """Origem física e histórica do projeto."""

    GREENFIELD = "GREENFIELD"
    BROWNFIELD = "BROWNFIELD"


class InceptionLevel(str, Enum):
    """Nível de profundidade e rigor da Lean Inception."""

    MINI = "MINI"                          # POC / PROTOTYPE: hipótese isolada e critérios rápidos
    FULL_CANONICAL = "FULL_CANONICAL"      # MVP Premium: Visão, É/Não É, Personas, Canvas MVP, PBB
    DEEP_ENTERPRISE = "DEEP_ENTERPRISE"    # Enterprise Grade: Inception completa + STRIDE + P99 + LGPD
    EVOLUTION_DAKI = "EVOLUTION_DAKI"      # Brownfield: Mapeamento de fluxo existente + DAKI + PBB Delta


@dataclass(frozen=True)
class UpstreamProfile:
    """Perfil consolidado que governa o ciclo de Upstream da ONDA."""

    origin: ProjectOrigin
    target: DeliveryTarget
    inception_level: InceptionLevel
    mocks_allowed: bool
    technical_debt_tolerance: str
    pbb_granularity: str
    required_artifacts: list[str] = field(default_factory=list)

    @property
    def is_enterprise(self) -> bool:
        return self.target in (DeliveryTarget.ENTERPRISE, DeliveryTarget.PRODUCTION)

    @property
    def is_mvp(self) -> bool:
        return self.target == DeliveryTarget.MVP

    @property
    def is_experimental(self) -> bool:
        return self.target in (DeliveryTarget.POC, DeliveryTarget.PROTOTYPE, DeliveryTarget.SNIPPET)


class UpstreamProfiler:
    """Classificador adaptativo que define a intensidade da Inception e do PBB."""

    @staticmethod
    def detect_origin(project_dir: Path | str) -> ProjectOrigin:
        """Detecta se o projeto já possui histórico funcional prévio ou está nascendo do zero."""
        p = Path(project_dir)
        prd_file = p / "docs" / "briefings" / "PRD.md"
        src_dir = p / "src"

        # Se já existe PRD com conteúdo e diretório src com código, é brownfield
        if prd_file.is_file() and prd_file.stat().st_size > 200:
            return ProjectOrigin.BROWNFIELD

        if src_dir.is_dir():
            code_files = [
                f for f in src_dir.rglob("*")
                if f.is_file() and f.suffix in (".ts", ".js", ".py", ".go", ".rs", ".java", ".cs")
            ]
            if len(code_files) >= 3:
                return ProjectOrigin.BROWNFIELD

        return ProjectOrigin.GREENFIELD

    @classmethod
    def profile(
        cls,
        project_dir: Path | str,
        target: DeliveryTarget | str = DeliveryTarget.MVP,
    ) -> UpstreamProfile:
        """Determina o perfil completo de Inception para a ONDA."""
        if isinstance(target, str):
            try:
                delivery_target = DeliveryTarget(target.lower())
            except ValueError:
                delivery_target = DeliveryTarget.MVP
        else:
            delivery_target = target

        origin = cls.detect_origin(project_dir)

        # 1. Brownfield: sempre aplica Inception DAKI + PBB Delta para evitar Frankenstein
        if origin == ProjectOrigin.BROWNFIELD:
            return UpstreamProfile(
                origin=ProjectOrigin.BROWNFIELD,
                target=delivery_target,
                inception_level=InceptionLevel.EVOLUTION_DAKI,
                mocks_allowed=False,
                technical_debt_tolerance="Zero nas novas rotas; refatoração cirúrgica no legado",
                pbb_granularity="PBB Delta (incrementos verticais sobre fluxos existentes)",
                required_artifacts=[
                    "docs/briefings/PRD.md",
                    "docs/architecture/journey.md",
                    "docs/architecture/adr/",
                    "docs/backlog/stories/",
                ],
            )

        # 2. Greenfield: calibra pela maturidade requerida
        if delivery_target in (DeliveryTarget.POC, DeliveryTarget.PROTOTYPE, DeliveryTarget.SNIPPET):
            return UpstreamProfile(
                origin=ProjectOrigin.GREENFIELD,
                target=delivery_target,
                inception_level=InceptionLevel.MINI,
                mocks_allowed=True,
                technical_debt_tolerance="Aceito para acelerar validação de hipótese",
                pbb_granularity="Spikes e stories de validação direta",
                required_artifacts=[
                    "docs/briefings/viability.md",
                    "docs/briefings/PRD.md",
                ],
            )

        if delivery_target in (DeliveryTarget.ENTERPRISE, DeliveryTarget.PRODUCTION):
            return UpstreamProfile(
                origin=ProjectOrigin.GREENFIELD,
                target=delivery_target,
                inception_level=InceptionLevel.DEEP_ENTERPRISE,
                mocks_allowed=False,
                technical_debt_tolerance="Zero absoluto; padrões bancários, ACID e resiliência",
                pbb_granularity="PBB Enterprise (Stories com critérios de segurança, auditoria e SLAs)",
                required_artifacts=[
                    "docs/briefings/viability.md",
                    "docs/briefings/PRD.md",
                    "docs/architecture/journey.md",
                    "docs/architecture/SYSTEM_ARCHITECTURE.md",
                    "docs/architecture/db.md",
                    "docs/architecture/adr/",
                    "docs/governance/compliance.md",
                    "docs/backlog/stories/",
                ],
            )

        # Default Greenfield MVP (MVP Premium)
        return UpstreamProfile(
            origin=ProjectOrigin.GREENFIELD,
            target=DeliveryTarget.MVP,
            inception_level=InceptionLevel.FULL_CANONICAL,
            mocks_allowed=False,
            technical_debt_tolerance="Débito pontual tolerado apenas em otimizações secundárias sem perda de UX",
            pbb_granularity="PBB Completo (Canvas MVP -> Step Map -> ai-stories INVEST)",
            required_artifacts=[
                "docs/briefings/viability.md",
                "docs/briefings/PRD.md",
                "docs/architecture/journey.md",
                "docs/architecture/SYSTEM_ARCHITECTURE.md",
                "docs/architecture/db.md",
                "docs/architecture/adr/",
                "docs/backlog/stories/",
            ],
        )
