"""Testes unitários para os Gates Determinísticos de Upstream do Turing (ST-027).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from bombe_code.turing.upstream_gates import (
    ArchitectureGate,
    JourneyGate,
    PRDQualityGate,
    StoryDoRGate,
)


def test_prd_quality_gate_approves_valid_prd():
    gate = PRDQualityGate()
    valid_prd = """# PRD Oficial

## 1. Visão Geral
Sistema de alta disponibilidade para pagamentos.

## 2. Problema
Processamento manual e lento.

## 3. Personas
Operador financeiro e auditor.

## 4. Critérios RICE
Reach: 100%, Impact: 3x, Confidence: 80%, Effort: 2 semanas.

## 5. MVP Operacional
Fluxo ponta a ponta de conciliação.
"""
    result = gate.evaluate(valid_prd)
    assert result["approved"] is True
    assert len(result["missing_sections"]) == 0


def test_prd_quality_gate_rejects_incomplete_prd():
    gate = PRDQualityGate()
    incomplete_prd = """# PRD Incompleto

## 1. Visão Geral
Apenas uma visão superficial.
"""
    result = gate.evaluate(incomplete_prd)
    assert result["approved"] is False
    assert "Critérios RICE" in result["missing_sections"]
    assert "MVP Operacional" in result["missing_sections"]


def test_journey_gate_evaluates_user_flows():
    gate = JourneyGate()
    valid_journey = """# Mapeamento de Jornada (@alan)

## 1. Entry Points
Login e deep link de convite.

## 2. Fluxo de Navegação
Dashboard -> Detalhe da Transação -> Confirmação.

## 3. Telas e Componentes
Tela de Checkout, Modal de Validação.
"""
    result = gate.evaluate(valid_journey)
    assert result["approved"] is True


def test_architecture_gate_evaluates_tech_stack():
    gate = ArchitectureGate()
    valid_arch = """# Arquitetura do Sistema (@ieru)

## Decisões Arquiteturais
Uso de Arquitetura Hexagonal com Ports e Adapters.

## Stack Tecnológica
Backend: Python 3.13 / FastAPI, Banco: PostgreSQL.
"""
    result = gate.evaluate(valid_arch)
    assert result["approved"] is True


def test_story_dor_gate_evaluates_invest_and_bdd():
    gate = StoryDoRGate()
    valid_story = """# STORY ST-100: Autenticação de Usuário

## Critérios INVEST
Independente, Negociável, Valiosa, Estimável, Small, Testável.

## Critérios de Aceite
### Cenário 1: Login com sucesso
* **Dado** um usuário cadastrado
* **Quando** enviar credenciais válidas
* **Então** deve retornar JWT válido.
"""
    result = gate.evaluate(valid_story)
    assert result["approved"] is True

    invalid_story = """# STORY ST-101: Fazer tela
Sem critérios definidos e sem BDD.
"""
    bad_res = gate.evaluate(invalid_story)
    assert bad_res["approved"] is False
