"""Testes para o executor de agentes (AgentRunner) integrado com Pydantic AI e Skills.
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from unittest.mock import MagicMock

import pytest

from bombe_code.agents.models import AgentOrigin
from bombe_code.agents.registry import AgentRegistry
from bombe_code.agents.runner import AgentExecutionResult, AgentRunner
from bombe_code.llm.pydantic_factory import PydanticAiFactory
from bombe_code.skills.models import SkillDefinition
from bombe_code.skills.registry import SkillRegistry
from bombe_code.storage.project_db import ProjectDatabase


@pytest.fixture
def skill_registry():
    reg = SkillRegistry()
    reg.register(
        SkillDefinition(
            name="clean-code",
            description="Padrões de legibilidade de código.",
            category="craftsmanship",
            instruction_content="Mantenha funções pequenas e com responsabilidade única.",
        )
    )
    return reg


@pytest.fixture
def mock_factory():
    factory = MagicMock(spec=PydanticAiFactory)
    # Mock do create_agent
    mock_agent_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.data = "PRD criado com sucesso em docs/briefings/PRD.md"
    mock_result.output = "PRD criado com sucesso em docs/briefings/PRD.md"
    mock_agent_instance.run.return_value = mock_result
    mock_agent_instance.run_sync.return_value = mock_result

    factory.create_agent.return_value = mock_agent_instance
    return factory


def test_agent_runner_initialization(skill_registry, mock_factory, tmp_path):
    db_path = tmp_path / "test_state.db"
    db = ProjectDatabase(db_path)

    agent_registry = AgentRegistry.default()
    grace = agent_registry.get("@grace")

    runner = AgentRunner(
        agent=grace,
        llm_factory=mock_factory,
        skill_registry=skill_registry,
        project_db=db,
    )

    assert runner.agent.handle == "@grace"
    assert runner.agent.origin == AgentOrigin.WORLD


def test_agent_runner_execution_flow(skill_registry, mock_factory, tmp_path):
    db_path = tmp_path / "test_state.db"
    db = ProjectDatabase(db_path)

    agent_registry = AgentRegistry.default()
    valim = agent_registry.get("@valim")

    runner = AgentRunner(
        agent=valim,
        llm_factory=mock_factory,
        skill_registry=skill_registry,
        project_db=db,
    )

    result = runner.run(prompt="Implementar ST-001 sob TDD", context={"stage": "EXECUTE"})

    assert isinstance(result, AgentExecutionResult)
    assert result.success is True
    assert "PRD criado com sucesso" in result.output
    assert result.agent_handle == "@valim"

    # Verifica se a task foi registrada no Kanban de agentes local
    tasks = db.list_agent_tasks(agent_handle="@valim")
    assert len(tasks) == 1
    assert tasks[0]["status"] == "completed"
    assert "ST-001" in tasks[0]["title"]


def test_agent_runner_execution_failure(skill_registry, mock_factory, tmp_path):
    db_path = tmp_path / "test_state.db"
    db = ProjectDatabase(db_path)

    agent_registry = AgentRegistry.default()
    meira = agent_registry.get("@meira")

    mock_agent_instance = MagicMock()
    mock_agent_instance.run.side_effect = RuntimeError("Falha de conexão com LLM")
    mock_agent_instance.run_sync.side_effect = RuntimeError("Falha de conexão com LLM")
    mock_factory.create_agent.return_value = mock_agent_instance

    runner = AgentRunner(
        agent=meira,
        llm_factory=mock_factory,
        skill_registry=skill_registry,
        project_db=db,
    )

    result = runner.run(prompt="Avaliar viabilidade do app")

    assert result.success is False
    assert "Falha de conexão" in result.error
    assert result.agent_handle == "@meira"

    tasks = db.list_agent_tasks(agent_handle="@meira")
    assert len(tasks) == 1
    assert tasks[0]["status"] == "failed"


def test_agent_runner_realtime_telemetry(mock_factory, capsys):
    agent_registry = AgentRegistry.default()
    grace = agent_registry.get("@grace")

    runner = AgentRunner(
        agent=grace,
        llm_factory=mock_factory,
    )

    result = runner.run("Execute a tarefa de telemetria")
    captured = capsys.readouterr()
    assert "⚡ [@grace] Invocando modelo..." in captured.out
    assert "✓ [@grace] Resposta recebida" in captured.out
    assert result.success is True


def test_agent_runner_automatic_failover():
    from bombe_code.llm.provider_rotator import ProviderFailoverRouter, ProviderSlot

    agent_registry = AgentRegistry.default()
    grace = agent_registry.get("@grace")

    slot1 = ProviderSlot(name="primary_zai", model="glm-5.3-flash", priority=1)
    slot2 = ProviderSlot(name="fallback_groq", model="llama-3.3-70b-versatile", priority=2)
    router = ProviderFailoverRouter(slots=[slot1, slot2])

    class MockStatus429(Exception):
        def __init__(self):
            super().__init__("HTTP 429 Too Many Requests")
            self.status_code = 429

    mock_agent_primary = MagicMock()
    mock_agent_primary.run.side_effect = MockStatus429()
    mock_agent_primary.run_sync.side_effect = MockStatus429()

    mock_agent_fallback = MagicMock()
    mock_res = MagicMock()
    mock_res.output = "Resposta gerada com sucesso via fallback"
    mock_agent_fallback.run.return_value = mock_res
    mock_agent_fallback.run_sync.return_value = mock_res


    mock_factory = MagicMock()
    # Primeiro retorno é o primário que falha; segundo retorno é o fallback que funciona
    mock_factory.create_agent.side_effect = [mock_agent_primary, mock_agent_fallback]

    runner = AgentRunner(
        agent=grace,
        llm_factory=mock_factory,
        router=router,
    )

    result = runner.run("Executar demanda")

    assert result.success is True
    assert "Resposta gerada com sucesso via fallback" in result.output
    # Garante que o slot 1 foi marcado como esgotado e o slot 2 está ativo
    assert slot1.is_available() is False
    assert router.get_active_slot().name == "fallback_groq"


