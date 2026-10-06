"""Testes unitários para o fluxo DEV_DONE -> DONE e Flag Ortogonal de Bloqueio (ST-031).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.kanban import KanbanCardStatus, KanbanManager
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def project_env(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    stories_dir = tmp_path / "docs" / "backlog" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path, db


def test_kanban_status_chain_includes_dev_done():
    # Verifica que o enum contém DEV_DONE e os estados limpos da cadeia
    assert KanbanCardStatus.DEV_DONE.value == "DEV_DONE"
    assert KanbanCardStatus.DONE.value == "DONE"


def test_kanban_orthogonal_blocked_flag_at_problem_location(project_env):
    tmp_path, db = project_env
    kanban = KanbanManager(project_dir=str(tmp_path), db=db)

    # Cria arquivo físico de story
    story_file = tmp_path / "docs" / "backlog" / "stories" / "ST-050.md"
    story_file.write_text(
        """# STORY ST-050: Teste de Bloqueio
> **Status:** IN_PROGRESS
> **Responsáveis:** @valim
> **Blocked:** False
""",
        encoding="utf-8",
    )

    kanban.scan_and_sync_directory()
    card = kanban.get_card("ST-050")
    assert card is not None
    assert card["status"] == "IN_PROGRESS"
    assert card.get("is_blocked") in (0, False, None)

    # Bloqueia a linha de montagem no local exato do problema (IN_PROGRESS)
    kanban.block_card("ST-050", reason="Falta credencial de pagamento", blocked_by="@valim")

    blocked_card = kanban.get_card("ST-050")
    # O status PERMANECE no local do problema (IN_PROGRESS)
    assert blocked_card["status"] == "IN_PROGRESS"
    assert blocked_card["is_blocked"] in (1, True)
    assert blocked_card["block_reason"] == "Falta credencial de pagamento"
    assert blocked_card["blocked_by"] == "@valim"

    # Desbloqueia e o fluxo segue
    kanban.unblock_card("ST-050")
    unblocked = kanban.get_card("ST-050")
    assert unblocked["status"] == "IN_PROGRESS"
    assert unblocked["is_blocked"] in (0, False)
    assert unblocked["block_reason"] == ""


def test_orchestrator_moves_to_dev_done_then_done_on_validate(project_env):
    tmp_path, db = project_env
    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()
    mock_res.data = "Entrega concluída e homologada."
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-007")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)

    # Cria story pré-requisito no disco
    stories_dir = tmp_path / "docs" / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    (stories_dir / "ST-051.md").write_text(
        "# STORY ST-051\n## INVEST\n## Critérios de Aceite\n### Cenários BDD\n- Dado X\n- Quando Y\n- Então Z\n"
    )

    # 1. Executa ciclo: ao final do dev + review técnico, status é DEV_DONE
    res_cycle = orch.run_cycle("ST-051")
    assert res_cycle["success"] is True

    card = orch.kanban.get_card("ST-051")
    assert card is not None
    assert card["status"] == "DEV_DONE"

    # 2. Executa validate: Edith homologa e promove DEV_DONE para DONE definitivo
    res_val = orch.run_validate()
    assert res_val["success"] is True

    final_card = orch.kanban.get_card("ST-051")
    assert final_card["status"] == "DONE"
