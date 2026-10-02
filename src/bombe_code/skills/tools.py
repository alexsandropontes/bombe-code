"""Ferramentas operacionais de skills para agentes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bombe_code.skills.registry import SkillRegistry


def make_skill_tools(
    registry: SkillRegistry,
) -> tuple[Callable[[str], list[dict[str, Any]]], Callable[[str], str]]:
    """Gera o par de tools (search_skills, load_skill) vinculadas a um SkillRegistry."""

    def search_skills(query: str = "") -> list[dict[str, Any]]:
        """Busca skills disponíveis por palavra-chave na descrição, nome ou categoria."""
        summaries = registry.search(query)
        return [s.model_dump() for s in summaries]

    def load_skill(name: str) -> str:
        """Carrega sob demanda o corpo instrucional completo de uma skill pelo nome."""
        try:
            return registry.load(name)
        except KeyError:
            return f"Erro: Skill '{name}' não encontrada. Use search_skills para listar as disponíveis."

    return search_skills, load_skill
