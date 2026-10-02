"""Modelos de dados e contratos de personas e agentes."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from bombe_code.turing.state_machine import TuringStage


class AgentOrigin(str, Enum):
    """Origem geográfica e de homenagem do agente."""

    BRAZIL = "BRAZIL"
    WORLD = "WORLD"
    UNIVERSAL = "UNIVERSAL"


class AgentDefinition(BaseModel):
    """Definição oficial de um agente do ecossistema Bombe Code."""

    handle: str = Field(..., description="Handle do agente no formato @nome (ex: @valim)")
    name: str = Field(..., description="Nome do pioneiro homenageado")
    role: str = Field(..., description="Papel profissional ou cargo do agente")
    country: str = Field(default="", description="País de origem do pioneiro homenageado")
    origin: AgentOrigin = Field(..., description="Origem da homenagem (BRAZIL, WORLD, UNIVERSAL)")
    historical_homage: str = Field(..., description="Homenagem e biografia histórica explícita")
    primary_stage: TuringStage = Field(..., description="Etapa primária do ciclo da ONDA")
    phase: str = Field(
        default="UPSTREAM", description="Fase de atuação: UPSTREAM, DOWNSTREAM ou ALL"
    )
    required_inputs: list[str] = Field(
        default_factory=list, description="Insumos obrigatórios validados pelo Consumer Gate"
    )
    expected_outputs: list[str] = Field(
        default_factory=list, description="Artefatos esperados fiscalizados pelo Turing Gate"
    )
    skills_allowed: list[str] = Field(
        default_factory=list, description="Skills sob demanda autorizadas"
    )
    system_prompt: str = Field(..., description="System prompt enxuto e determinístico do agente")

    @property
    def is_brazilian(self) -> bool:
        return self.origin == AgentOrigin.BRAZIL

    @property
    def is_universal(self) -> bool:
        return self.origin == AgentOrigin.UNIVERSAL
