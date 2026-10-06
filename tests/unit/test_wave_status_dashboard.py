"""Testes unitários para o Dashboard e Orquestração Integrada da ONDA (ST-030).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def orchestrator(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()

    # Retorna texto completo que satisfaz os gates de Upstream
    mock_res.data = """# Entrega Integrada

## 1. Visão Geral
Sistema de pagamentos autônomo.

## 2. Problema
Processamento manual.

## 3. Personas
Operador financeiro.

## 4. Critérios RICE
Reach 100%, Impact 3x, Confidence 90%, Effort 2 semanas.

## 5. MVP Operacional
Fluxo ponta a ponta.

## Viabilidade Técnica
Viável operacionalmente.

## Riscos
Riscos mitigados e controlados.

## Entry Points
Login web.

## Fluxo de Navegação
Home -> Checkout.

## Telas
Tela Principal.

## Decisões Arquiteturais
Clean Architecture.

## Stack
Python FastAPI.

## Schema
CREATE TABLE payments (id UUID);

## Constraints
PRIMARY KEY (id);

## Critérios INVEST
Independente e Testável.

## Critérios de Aceite
### Cenário 1: Sucesso
* **Dado** usuário
* **Quando** autenticar
* **Então** aprovar.

Review: APROVADO
Veredito: VERDE
"""
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-006")
    return orch


def test_upstream_gates_recorded_in_orchestrator(orchestrator):
    # Executa discuss
    res_disc = orchestrator.run_discuss("Novo Módulo de Pagamentos")
    assert res_disc["success"] is True

    # Executa plan
    res_plan = orchestrator.run_plan()
    assert res_plan["success"] is True
    assert "gates" in res_plan
    assert res_plan["gates"]["prd"]["approved"] is True
    assert res_plan["gates"]["journey"]["approved"] is True
    assert res_plan["gates"]["architecture"]["approved"] is True

    # Status agora reflete os gates
    st = orchestrator.get_status()
    assert "gates" in st
    assert st["gates"]["prd"]["approved"] is True


def test_downstream_review_gate_in_run_cycle(orchestrator):
    # Cria story pré-requisito no disco
    stories_dir = orchestrator.project_dir / "docs" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "ST-030.md").write_text(
        "# STORY ST-030\n## INVEST\n## Critérios de Aceite\n### Cenários BDD\n- Dado X\n- Quando Y\n- Então Z\n"
    )

    # Transita para EXECUTE
    orchestrator.transition_to(TuringStage.PLAN)
    orchestrator.transition_to(TuringStage.EXECUTE)

    # Executa ciclo com review duplo
    res = orchestrator.run_cycle(story_id="ST-030")
    assert res["success"] is True
    assert "review_gate" in res
    assert res["review_gate"]["approved"] is True

    # Verifica se o card no Kanban foi atualizado para DEV_DONE
    card = orchestrator.kanban.get_card("ST-030")
    assert card is not None
    assert card["status"] == "DEV_DONE"
    assert "@aniche" in card["reviews"]
    assert "@unclebob" in card["reviews"]

    # Após homologação em VALIDATE, promove para DONE definitivo
    res_val = orchestrator.run_validate()
    assert res_val["success"] is True
    assert orchestrator.kanban.get_card("ST-030")["status"] == "DONE"
