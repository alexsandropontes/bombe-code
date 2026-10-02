"""Testes para detecção de bloqueio pelo Pydantic AI e regra de restrição (Default-Deny) no Turing.
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.agents.registry import AgentRegistry
from bombe_code.agents.runner import AgentExecutionResult, AgentRunner
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.kanban import KanbanCardStatus
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import TuringStage


@pytest.fixture
def test_agent():
    return AgentRegistry.default().get("@valim")


def test_runner_detects_blocked_agent(test_agent, tmp_path: Path):
    """Garante que a própria resposta da LLM cagueta que ela está bloqueada."""
    db = ProjectDatabase(str(tmp_path / "state.db"))
    mock_factory = MagicMock()
    mock_agent = MagicMock()

    mock_res = MagicMock()
    mock_res.data = (
        "Status: ⛔ AUDITORIA NÃO INICIÁVEL — EVIDÊNCIAS OBRIGATÓRIAS NÃO RECEBIDAS.\n"
        "Sem RED legítimo na mesa, não há código de produção."
    )
    mock_agent.run.return_value = mock_res
    mock_agent.run_sync.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    runner = AgentRunner(agent=test_agent, llm_factory=mock_factory, project_db=db)
    result = runner.run(prompt="Implementar ST-001")

    assert isinstance(result, AgentExecutionResult)
    assert result.is_blocked is True
    assert result.success is False
    assert result.status == "BLOCKED"
    assert result.block_reason is not None
    assert "EVIDÊNCIAS" in result.block_reason or "RED" in result.block_reason

    # Registrado no SQLite como blocked
    tasks = db.list_agent_tasks(agent_handle="@valim")
    assert len(tasks) == 1
    assert tasks[0]["status"] == "blocked"


def test_turing_default_deny_rejects_without_explicit_approval(tmp_path: Path):
    """Garante a Lei da Restrição: qualquer coisa diferente de APROVADO explícito é rejeitada."""
    db = ProjectDatabase(str(tmp_path / "state.db"))
    mock_factory = MagicMock()
    mock_agent = MagicMock()

    # Resposta que NÃO tem a palavra 'aprovado' nem 'approved'
    mock_res = MagicMock()
    mock_res.data = "Código analisado. Algumas considerações foram feitas mas sem veredito final."
    mock_agent.run.return_value = mock_res
    mock_agent.run_sync.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-TEST")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)

    res = orch.run_cycle("ST-001")

    # Deve falhar pelo Default-Deny
    assert res["success"] is False
    card = orch.kanban.get_card("ST-001")
    assert card["status"] != KanbanCardStatus.DEV_DONE.value


def test_turing_blocks_card_when_agent_is_blocked(tmp_path: Path):
    """Garante que se o QA ou Dev bloqueia, o card do Kanban fica marcado como is_blocked."""
    db = ProjectDatabase(str(tmp_path / "state.db"))
    mock_factory = MagicMock()
    mock_agent = MagicMock()

    mock_res = MagicMock()
    mock_res.data = "Bloqueio registrado antes de qualquer execução: faltam cenários BDD."
    mock_agent.run.return_value = mock_res
    mock_agent.run_sync.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-TEST")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)

    res = orch.run_cycle("ST-001")

    assert res["success"] is False
    card = orch.kanban.get_card("ST-001")
    assert card["is_blocked"] == 1
    assert "BDD" in card["block_reason"] or "bloqueio" in card["block_reason"].lower()
