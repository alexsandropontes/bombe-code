"""Testes unitários para flexibilização de priorização no PRDQualityGate (ST-033).
TDD Estrito: RED -> GREEN.
"""

from bombe_code.turing.upstream_gates import PRDQualityGate


def test_prd_quality_gate_accepts_moscow():
    gate = PRDQualityGate()
    prd_content = """# PRD do Módulo
## Visão Geral
Sistema de pagamentos.
## Problema
Lentidão manual.
## Personas
Operador financeiro.
## Priorização MoSCoW
Must have: checkout básico.
## MVP Operacional
Fluxo ponta a ponta.
"""
    res = gate.evaluate(prd_content)
    assert res["approved"] is True
    assert len(res["missing_sections"]) == 0


def test_prd_quality_gate_accepts_wsjf():
    gate = PRDQualityGate()
    prd_content = """# PRD do Módulo
## Visão Geral
Sistema de pagamentos.
## Problema
Lentidão manual.
## Personas
Operador financeiro.
## Priorização WSJF
Cost of Delay 8, Job Duration 2.
## MVP Operacional
Fluxo ponta a ponta.
"""
    res = gate.evaluate(prd_content)
    assert res["approved"] is True
    assert len(res["missing_sections"]) == 0
