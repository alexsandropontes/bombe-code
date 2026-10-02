"""Testes unitários para o Turing Gates Engine (ST-003)."""

from __future__ import annotations

from pathlib import Path

from bombe_code.turing.gates import (
    ConsumerHandoffGate,
    GateStatus,
    SealGate,
    SealType,
    TemplateGate,
)


def test_template_gate_passes_when_file_and_sections_present(tmp_path: Path):
    doc = tmp_path / "PRD.md"
    doc.write_text("# PRD\n\n## 1. Visão Geral\nConteúdo substantivo do projeto.\n\n## 2. Requisitos\nLista de regras.", encoding="utf-8")

    gate = TemplateGate()
    eval_res = gate.evaluate(
        file_path=str(doc),
        required_sections=["Visão Geral", "Requisitos"],
        min_words=5,
    )

    assert eval_res.status == GateStatus.APPROVED
    assert len(eval_res.issues) == 0


def test_template_gate_fails_when_file_missing(tmp_path: Path):
    missing_doc = tmp_path / "NON_EXISTENT.md"

    gate = TemplateGate()
    eval_res = gate.evaluate(
        file_path=str(missing_doc),
        required_sections=["Visão Geral"],
    )

    assert eval_res.status == GateStatus.REJECTED
    assert "Arquivo não encontrado" in eval_res.issues[0]


def test_template_gate_fails_when_section_missing(tmp_path: Path):
    doc = tmp_path / "PRD.md"
    doc.write_text("# PRD\n\n## 1. Visão Geral\nApenas visão.", encoding="utf-8")

    gate = TemplateGate()
    eval_res = gate.evaluate(
        file_path=str(doc),
        required_sections=["Visão Geral", "Requisitos", "Arquitetura"],
    )

    assert eval_res.status == GateStatus.REJECTED
    assert any("Requisitos" in issue for issue in eval_res.issues)
    assert any("Arquitetura" in issue for issue in eval_res.issues)


def test_seal_gate_tech_lead_approval():
    gate = SealGate()
    content_approved = "# Story ST-001\n\nImplementação feita.\n\n[SELO TECH LEAD: APROVADO]\nData: 2026-10-01"
    eval_res = gate.evaluate(content_approved, SealType.TECH_LEAD)

    assert eval_res.status == GateStatus.APPROVED
    assert eval_res.seal_found is True


def test_seal_gate_tech_lead_rejected_or_missing():
    gate = SealGate()
    content_missing = "# Story ST-001\n\nImplementação feita sem review."
    eval_res = gate.evaluate(content_missing, SealType.TECH_LEAD)

    assert eval_res.status == GateStatus.REJECTED
    assert eval_res.seal_found is False


def test_consumer_handoff_gate_rejects_shallow_input_and_builds_rework():
    handoff = ConsumerHandoffGate()
    content = "Documento curto demais."

    eval_res = handoff.evaluate_input(
        consumer="Architect",
        producer="ProductManager",
        artifact_name="PRD.md",
        content=content,
        required_topics=["Modelo de Domínio", "Critérios de Sucesso"],
        min_words=10,
    )

    assert eval_res.status == GateStatus.REJECTED
    assert len(eval_res.required_improvements) >= 2

    prompt = handoff.build_rework_prompt(eval_res)
    assert "Modelo de Domínio" in prompt
    assert "Critérios de Sucesso" in prompt
    assert "ProductManager" in prompt
