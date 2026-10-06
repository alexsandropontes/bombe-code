"""Mecanismo determinístico de descoberta e formatação de skills."""

from __future__ import annotations

import os
from pathlib import Path

from .manifest import SkillManifest


def discover_skills(base_dir: str | Path) -> list[SkillManifest]:
    """Escaneia um diretório e subpastas procurando arquivos SKILL.md."""
    base_path = Path(base_dir).resolve()
    if not base_path.exists():
        return []

    skills: list[SkillManifest] = []
    # Busca recursiva em .agent/skills, .bombe/skills ou direto na pasta fornecida
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ("node_modules", "__pycache__", ".venv", ".git", "build", "dist")
        ]
        if "SKILL.md" in files:
            skill_file = Path(root) / "SKILL.md"
            try:
                manifest = SkillManifest.from_file(skill_file)
                skills.append(manifest)
            except (OSError, ValueError):
                continue

    return sorted(skills, key=lambda s: s.name)


def get_skill_by_name(skills: list[SkillManifest], name: str) -> SkillManifest | None:
    """Busca uma skill pelo nome exato ou semântico."""
    target = name.strip().lower()
    for s in skills:
        if s.name.lower() == target:
            return s
    return None


def format_skills_for_prompt(skills: list[SkillManifest]) -> str:
    """Formata catálogo de skills para injeção no prompt de sistema do agente."""
    if not skills:
        return ""

    lines = ["## Skills Disponíveis para o Agente:"]
    for s in skills:
        trigs = f" (Gatilhos: {', '.join(s.triggers)})" if s.triggers else ""
        lines.append(f"- **{s.name}**: {s.description}{trigs}")
    lines.append(
        "\nUse a ferramenta `skill` para ler as instruções detalhadas de uma skill quando necessário."
    )
    return "\n".join(lines)
