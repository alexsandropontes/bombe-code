from __future__ import annotations

from pathlib import Path

from bombe_code.agents.validator import AgentDossierValidator

VALID_SYNTHETIC_DOSSIER = """---
name: sample
description: "Agente especialista de teste sintético."
version: 4.0
author: "@andrej"
metadata:
  type: agent
authority:
  is_lead: true
  can_route: false
  can_veto: true
  order: 1
identity:
  name: Sample Agent
  role: Test Specialist
  seniority: Principal
  background: Especialista em testes unitários e governança de software.
vibe:
  tone: Direto e factual.
  signature: "— Sample test signature."
  personality: Rigoroso e focado em qualidade.
constraints:
  - "PROIBIDO ACESSAR AMBIENTE SEM AUTORIZAÇÃO."
routing_triggers:
  - "@sample"
  - sample
skills:
  - clean-code
  - tdd-methodology
---

# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA
- **Autoridade:** Autoridade técnica em execução de testes sintéticos.
- **Postura Cognitiva:** Cético Adversarial e Guardião de Qualidade.
- **Viés Operacional:** Presunção de erro até que os testes comprovem conformidade.
- **Temperamento Técnico:** Intransigente contra amadorismo e hacks.
- **Tom de Voz:** Cirúrgico, direto e analítico.
- **Heurísticas Sentinelas:**
  - Se faltar asserção de teste, reprove.

# 2. MISSÃO
Executar validações automatizadas e assegurar integridade estrutural.

# 3. BASE
- Plataforma: Bombe Code Runtime
- Skills disponíveis: clean-code, tdd-methodology

# 4. REGRAS
Limites de atuação estritos em escopo de validação sintética.

# 5. RESTRIÇÕES
PROIBIDO executar ações destrutivas.

# 6. ENTREGA
Template de entrega padronizado com veredito determinístico.
"""


def test_validator_approves_valid_pdw4_dossier():
    """Valida que um dossiê perfeitamente aderente ao PDW 4.0 seja aprovado."""
    validator = AgentDossierValidator()
    report = validator.validate_content(VALID_SYNTHETIC_DOSSIER, file_path="sample.md")
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_validator_rejects_missing_frontmatter():
    """Rejeita conteúdo sem bloco de frontmatter YAML."""
    validator = AgentDossierValidator()
    report = validator.validate_content("# Sem frontmatter\nConteúdo puro.", file_path="broken.md")
    assert report.is_valid is False
    assert any("frontmatter" in err.lower() for err in report.errors)


def test_validator_rejects_forbidden_mystical_attributes():
    """Rejeita dossiês contendo sign, mbti, age ou gender no frontmatter."""
    legacy_dossier = VALID_SYNTHETIC_DOSSIER.replace(
        "seniority: Principal",
        "seniority: Principal\n  sign: Escorpião\n  mbti: INTJ\n  age: '40'\n  gender: Masculino",
    )
    validator = AgentDossierValidator()
    report = validator.validate_content(legacy_dossier, file_path="legacy.md")
    assert report.is_valid is False
    assert any("mbti" in err.lower() or "sign" in err.lower() for err in report.errors)


def test_validator_rejects_legacy_section_identity():
    """Rejeita dossiês que usam '# 1. IDENTIDADE' em vez de '# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA'."""
    legacy_section = VALID_SYNTHETIC_DOSSIER.replace(
        "# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA", "# 1. IDENTIDADE"
    )
    validator = AgentDossierValidator()
    report = validator.validate_content(legacy_section, file_path="legacy_sec.md")
    assert report.is_valid is False
    assert any("perfil comportamental" in err.lower() for err in report.errors)


def test_validator_rejects_missing_cognitive_profile_bullets():
    """Rejeita dossiês que omitam qualquer um dos 6 campos de postura cognitiva."""
    incomplete_cognitive = VALID_SYNTHETIC_DOSSIER.replace(
        "- **Viés Operacional:** Presunção de erro até que os testes comprovem conformidade.",
        "",
    )
    validator = AgentDossierValidator()
    report = validator.validate_content(incomplete_cognitive, file_path="incomplete.md")
    assert report.is_valid is False
    assert any("viés operacional" in err.lower() for err in report.errors)


def test_all_production_agent_dossiers_are_valid_pdw4():
    """Garante que todos os 25 dossiês de produção atendam 100% ao PDW 4.0."""
    definitions_dir = Path(__file__).parents[2] / "src" / "bombe_code" / "agents" / "definitions"
    assert definitions_dir.is_dir(), f"Diretório não encontrado: {definitions_dir}"

    md_files = list(definitions_dir.glob("*.md"))
    assert len(md_files) >= 24, (
        f"Esperado ao menos 24 agentes em produção, encontrados {len(md_files)}"
    )

    validator = AgentDossierValidator()
    reports = validator.validate_all(definitions_dir)

    failures: list[str] = []
    for file_name, report in reports.items():
        if not report.is_valid:
            failures.append(f"{file_name}: {'; '.join(report.errors)}")

    assert not failures, "Dossiês com inconformidade PDW 4.0:\n" + "\n".join(failures)
