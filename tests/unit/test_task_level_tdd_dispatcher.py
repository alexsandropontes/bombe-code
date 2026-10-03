"""Testes TDD para a Story ST-037: Despachante de Execução por Task no WaveOrchestrator."""

from unittest.mock import MagicMock
import pytest
from bombe_code.turing.kanban import KanbanCardStatus, KanbanManager
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.pbb import AtomicTask, AtomicTaskType


@pytest.fixture
def mock_orchestrator(tmp_path):
    orch = WaveOrchestrator(project_dir=tmp_path)
    # Cria card inicial no Kanban
    orch.kanban.add_card(story_id="ST-001", wave_id="ONDA-001", title="Demanda Teste", agent="@aniche")
    return orch


def test_dispatcher_executes_tasks_sequentially(mock_orchestrator):
    tasks = [
        AtomicTask(
            id="ST-001-T1",
            story_id="ST-001",
            task_type=AtomicTaskType.DATABASE,
            title="Migration DB",
            description="Criar tabela",
            responsible_agent="@codd",
        ),
        AtomicTask(
            id="ST-001-T2",
            story_id="ST-001",
            task_type=AtomicTaskType.BACKEND_TDD,
            title="Rota Backend",
            description="Implementar rota",
            responsible_agent="@aniche",
            depends_on=["ST-001-T1"],
        ),
    ]

    executed_agents = []

    def mock_runner_factory(agent_handle: str):
        runner = MagicMock()
        def mock_run(prompt, context=None):
            executed_agents.append(agent_handle)
            res = MagicMock()
            res.success = True
            res.output = f"Output de {agent_handle}"
            res.is_blocked = False
            res.input_tokens = 10
            res.output_tokens = 20
            res.total_tokens = 30
            res.cost = 0.001
            res.duration_seconds = 0.5
            return res
        runner.run.side_effect = mock_run
        return runner

    mock_orchestrator._get_runner = mock_runner_factory

    result = mock_orchestrator.run_story_tasks("ST-001", tasks)
    assert result["success"] is True
    assert executed_agents == ["@codd", "@aniche"]

    # Valida que todos os status das tasks foram atualizados para COMPLETED
    assert all(t.status == "COMPLETED" for t in tasks)

    # Valida que o card no Kanban foi promovido para DEV_DONE
    cards = mock_orchestrator.kanban.list_cards(wave_id="ONDA-001")
    card = next(c for c in cards if c["story_id"] == "ST-001")
    assert card["status"] == KanbanCardStatus.DEV_DONE.value


def test_dispatcher_aborts_immediately_on_task_failure(mock_orchestrator):
    tasks = [
        AtomicTask(
            id="ST-001-T1",
            story_id="ST-001",
            task_type=AtomicTaskType.DATABASE,
            title="Migration DB",
            description="Criar tabela",
            responsible_agent="@codd",
        ),
        AtomicTask(
            id="ST-001-T2",
            story_id="ST-001",
            task_type=AtomicTaskType.BACKEND_TDD,
            title="Rota Backend",
            description="Implementar rota",
            responsible_agent="@aniche",
            depends_on=["ST-001-T1"],
        ),
    ]

    def mock_runner_factory(agent_handle: str):
        runner = MagicMock()
        res = MagicMock()
        res.success = False
        res.error = "Erro no SQL"
        res.output = ""
        res.is_blocked = False
        res.input_tokens = 10
        res.output_tokens = 0
        res.total_tokens = 10
        res.cost = 0.0
        res.duration_seconds = 0.1
        runner.run.return_value = res
        return runner

    mock_orchestrator._get_runner = mock_runner_factory

    result = mock_orchestrator.run_story_tasks("ST-001", tasks)
    assert result["success"] is False
    assert "Erro no SQL" in result["error"]
    assert tasks[0].status == "FAILED"
    assert tasks[1].status == "PENDING"  # Não executou a segunda task (Fail-Fast)
