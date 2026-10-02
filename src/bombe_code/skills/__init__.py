"""Módulo de descoberta, parsing e injeção de skills no contexto do agente."""

from .discovery import discover_skills, format_skills_for_prompt, get_skill_by_name
from .manifest import SkillManifest

__all__ = ["SkillManifest", "discover_skills", "format_skills_for_prompt", "get_skill_by_name"]
