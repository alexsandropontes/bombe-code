"""Testes unitários para o fluxo de QA no ciclo TDD e auto-desbloqueio pelo Turing.
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.kanban import KanbanCardStatus
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage, WaveState


@pytest.fixture
def mock_orchestrator(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    mock_factory = MagicMock()
    mock_agent = MagicMock()

    mock_res = MagicMock()
    mock_res.data = "Plano de testes aprovado com suíte unitária."
    mock_agent.run.return_value = mock_res
    mock_agent.run_sync.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    # Cria story pré-requisito no disco
    stories_dir = tmp_path / "docs" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "ST-001.md").write_text(
        "# STORY ST-001\n## INVEST\n## Critérios de Aceite\n### Cenários BDD\n- Dado X\n- Quando Y\n- Então Z\n"
    )

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-TEST")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    return orch


def test_run_cycle_dispatches_aniche_first_for_test_plan(mock_orchestrator):
    """Garante que @aniche cria o plano de testes ANTES do Dev codificar."""
    res = mock_orchestrator.run_cycle("ST-001")

    assert res["success"] is True
    assert "test_plan_output" in res
    assert res["test_plan_output"] != ""

    # Verifica status DEV_DONE
    card = mock_orchestrator.kanban.get_card("ST-001")
    assert card["status"] == KanbanCardStatus.DEV_DONE.value


def test_turing_auto_resolves_blocked_story(mock_orchestrator):
    """Garante que o Turing resolve autonomamente bloqueios delegando a quem resolve."""
    # Cria o card no Kanban
    mock_orchestrator.kanban.add_card(
        story_id="ST-001",
        wave_id="ONDA-TEST",
        title="Story Test",
        agent="@aniche",
        status=KanbanCardStatus.IN_PROGRESS.value,
    )

    # Bloqueia o card simulando especificação ambígua
    mock_orchestrator.kanban.block_card(
        story_id="ST-001",
        reason="Critérios BDD ambíguos na regra de pontuação",
        blocked_by="@aniche",
    )

    card = mock_orchestrator.kanban.get_card("ST-001")
    assert card["is_blocked"] == 1

    # Turing resolve autonomamente
    res = mock_orchestrator.auto_resolve_block("ST-001")
    assert res["success"] is True
    assert res["delegated_to"] == "@caroli"

    # Card agora está desbloqueado
    card_after = mock_orchestrator.kanban.get_card("ST-001")
    assert card_after["is_blocked"] == 0


def test_run_validate_executes_integration_and_marks_done(mock_orchestrator):
    """Garante que no VALIDATE rodam os testes de integração e stories viram DONE."""
    # Adiciona card em DEV_DONE
    mock_orchestrator.kanban.add_card(
        story_id="ST-001",
        wave_id="ONDA-TEST",
        title="Story Test",
        agent="@valim",
        status=KanbanCardStatus.DEV_DONE.value,
    )

    # Transita para VALIDATE
    mock_orchestrator.transition_to(TuringStage.VALIDATE)
    assert mock_orchestrator.state_machine.current_state == WaveState.VALIDATE

    res_val = mock_orchestrator.run_validate()
    assert res_val["success"] is True
    assert "integration_tests" in res_val

    # Card vira DONE definitivo
    card = mock_orchestrator.kanban.get_card("ST-001")
    assert card["status"] == KanbanCardStatus.DONE.value
