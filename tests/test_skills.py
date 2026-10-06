"""Testes para o subsistema de Skills sob Demanda (bombe_code.skills).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path

import pytest

from bombe_code.skills.models import SkillDefinition, SkillSummary
from bombe_code.skills.registry import SkillRegistry
from bombe_code.skills.tools import make_skill_tools


def test_skill_definition_creation():
    skill = SkillDefinition(
        name="solid-dry",
        description="Rigor tático de design de software e defesa contra entropia.",
        category="architecture",
        instruction_content="# Regras SOLID e DRY\n1. Single Responsibility...",
    )
    assert skill.name == "solid-dry"
    assert skill.category == "architecture"
    summary = skill.to_summary()
    assert isinstance(summary, SkillSummary)
    assert summary.name == "solid-dry"
    assert "Rigor" in summary.description


def test_skill_registry_register_and_load():
    registry = SkillRegistry()
    skill = SkillDefinition(
        name="clean-code",
        description="Padrões de legibilidade e nomes significativos.",
        category="craftsmanship",
        instruction_content="# Clean Code Guidelines...",
    )
    registry.register(skill)

    loaded = registry.load("clean-code")
    assert loaded == "# Clean Code Guidelines..."

    with pytest.raises(KeyError, match="Skill 'inexistente' não encontrada"):
        registry.load("inexistente")


def test_skill_registry_search():
    registry = SkillRegistry()
    registry.register(
        SkillDefinition(
            name="pbb-backlog",
            description="Construção de backlog via Product Backlog Building.",
            category="agile",
            instruction_content="PBB flow...",
        )
    )
    registry.register(
        SkillDefinition(
            name="clean-code",
            description="Padrões de legibilidade de código.",
            category="craftsmanship",
            instruction_content="Clean code rules...",
        )
    )

    results = registry.search("backlog")
    assert len(results) == 1
    assert results[0].name == "pbb-backlog"

    results_all = registry.search("")
    assert len(results_all) == 2


def test_skill_registry_discover_from_dir(tmp_path: Path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: test-skill\ndescription: Skill de teste\ncategory: testing\n---\n# Instruções da skill\nCorpo da instrução aqui.",
        encoding="utf-8",
    )

    registry = SkillRegistry()
    registry.discover_from_directory(tmp_path)

    assert "test-skill" in registry.list_names()
    assert registry.load("test-skill") == "# Instruções da skill\nCorpo da instrução aqui."
    results = registry.search("teste")
    assert len(results) == 1
    assert results[0].name == "test-skill"


def test_skill_tools_for_agent():
    registry = SkillRegistry()
    registry.register(
        SkillDefinition(
            name="tdd-governance",
            description="Regras de TDD estrito e gates de qualidade.",
            category="testing",
            instruction_content="Regra 1: Sem teste RED = Sem código.",
        )
    )

    search_fn, load_fn = make_skill_tools(registry)

    found = search_fn("TDD")
    assert any(item["name"] == "tdd-governance" for item in found)

    content = load_fn("tdd-governance")
    assert "Sem teste RED" in content

    missing = load_fn("skill-desconhecida")
    assert "Erro: Skill 'skill-desconhecida' não encontrada" in missing
