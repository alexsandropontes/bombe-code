"""Registro e repositório de skills sob demanda para agentes."""

import logging
import re
from pathlib import Path

from bombe_code.skills.models import SkillDefinition, SkillSummary

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Repositório de skills com suporte a registro, busca e carregamento on-demand."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition) -> None:
        """Registra uma nova skill no repositório."""
        self._skills[skill.name] = skill

    def load(self, name: str) -> str:
        """Carrega o corpo instrucional da skill sob demanda.

        Raises:
            KeyError: se a skill não estiver registrada.
        """
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' não encontrada no registro.")
        return self._skills[name].instruction_content

    def get(self, name: str) -> SkillDefinition | None:
        """Retorna a definição da skill ou None."""
        return self._skills.get(name)

    def list_names(self) -> list[str]:
        """Lista os nomes de todas as skills registradas."""
        return sorted(self._skills.keys())

    def search(self, query: str) -> list[SkillSummary]:
        """Busca skills por correspondência de texto no nome, descrição ou categoria."""
        q = query.strip().lower()
        if not q:
            return [s.to_summary() for s in self._skills.values()]

        results: list[SkillSummary] = []
        for skill in self._skills.values():
            if (
                q in skill.name.lower()
                or q in skill.description.lower()
                or q in skill.category.lower()
            ):
                results.append(skill.to_summary())
        return results

    def discover_from_directory(self, base_dir: Path | str) -> int:
        """Descobre e carrega skills a partir de uma pasta contendo SKILL.md.

        Retorna a quantidade de skills carregadas.
        """
        path = Path(base_dir)
        if not path.is_dir():
            return 0

        count = 0
        for skill_file in path.glob("**/SKILL.md"):
            try:
                content = skill_file.read_text(encoding="utf-8")
                # Parse frontmatter simples
                frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
                if frontmatter_match:
                    fm_text, body = frontmatter_match.groups()
                    name = skill_file.parent.name
                    desc = ""
                    category = "general"
                    for line in fm_text.splitlines():
                        if line.startswith("name:"):
                            name = line.split(":", 1)[1].strip()
                        elif line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip()
                        elif line.startswith("category:"):
                            category = line.split(":", 1)[1].strip()

                    self.register(
                        SkillDefinition(
                            name=name,
                            description=desc or name,
                            category=category,
                            instruction_content=body.strip(),
                        )
                    )
                    count += 1
            except (OSError, UnicodeDecodeError, ValueError) as err:
                logger.debug("Falha ao carregar skill de %s: %s", skill_file, err)
                continue

        return count
