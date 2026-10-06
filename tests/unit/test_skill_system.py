"""Testes unitários para a Feature 19: skill-system (RED phase)."""

from __future__ import annotations

from pathlib import Path

from bombe_code.skills.discovery import discover_skills, format_skills_for_prompt, get_skill_by_name
from bombe_code.skills.manifest import SkillManifest


def test_skill_manifest_parsing(tmp_path: Path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: test-skill
description: Skill de teste unitário
triggers: ['teste', 'exemplo']
---
# Instruções da Skill
Execute passo a passo com rigor.
""",
        encoding="utf-8",
    )

    manifest = SkillManifest.from_file(skill_file)
    assert manifest.name == "test-skill"
    assert manifest.description == "Skill de teste unitário"
    assert "teste" in manifest.triggers
    assert "Instruções da Skill" in manifest.content


def test_discover_skills_in_directory(tmp_path: Path):
    s1 = tmp_path / "skill-a"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: Desc A\n---\nConteudo A",
        encoding="utf-8",
    )

    s2 = tmp_path / "skill-b"
    s2.mkdir()
    (s2 / "SKILL.md").write_text(
        "---\nname: skill-b\ndescription: Desc B\n---\nConteudo B",
        encoding="utf-8",
    )

    skills = discover_skills(str(tmp_path))
    assert len(skills) == 2
    names = [s.name for s in skills]
    assert "skill-a" in names
    assert "skill-b" in names


def test_get_skill_by_name_and_format_prompt(tmp_path: Path):
    s1 = tmp_path / "skill-c"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: skill-c\ndescription: Auditoria C\n---\nInstruções C",
        encoding="utf-8",
    )

    skills = discover_skills(str(tmp_path))
    found = get_skill_by_name(skills, "skill-c")
    assert found is not None
    assert found.description == "Auditoria C"

    prompt_str = format_skills_for_prompt(skills)
    assert "skill-c" in prompt_str
    assert "Auditoria C" in prompt_str
