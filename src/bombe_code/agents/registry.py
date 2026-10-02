"""Registro oficial de agentes do Bombe Code.
Equipe de Personas com paridade rigorosa: 50% Pioneiros Brasileiros de TI / 50% Mundiais.
"""

from __future__ import annotations

from bombe_code.agents.loader import load_all_agents
from bombe_code.agents.models import AgentDefinition
from bombe_code.turing.state_machine import TuringStage


class AgentRegistry:
    """Repositório de agentes do Bombe Code."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        """Registra um agente normalizando a chave do handle."""
        key = agent.handle.lower().lstrip("@")
        self._agents[key] = agent

    def get(self, handle: str) -> AgentDefinition | None:
        """Busca agente pelo handle (com ou sem '@')."""
        key = handle.lower().lstrip("@")
        return self._agents.get(key)

    def list_all(self) -> list[AgentDefinition]:
        """Retorna todos os agentes registrados."""
        return list(self._agents.values())

    def list_by_stage(self, stage: TuringStage) -> list[AgentDefinition]:
        """Filtra agentes pela etapa primária ou que atuam em todas."""
        return [
            a
            for a in self._agents.values()
            if a.primary_stage == stage or a.primary_stage == TuringStage.COMPLETED
        ]

    def list_by_phase(self, phase: str) -> list[AgentDefinition]:
        """Filtra agentes por fase (UPSTREAM, DOWNSTREAM ou ALL)."""
        target = phase.upper()
        return [a for a in self._agents.values() if a.phase == target or a.phase == "ALL"]

    @classmethod
    def default(cls) -> AgentRegistry:
        """Cria e popula o catálogo oficial de agentes a partir das definições PDW 4.0."""
        reg = cls()
        agents = load_all_agents()
        for agent in agents:
            reg.register(agent)
        return reg
