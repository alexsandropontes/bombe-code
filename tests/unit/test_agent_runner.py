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
    # Mock do run
    mock_result = MagicMock()
    mock_result.data = "PRD criado com sucesso em docs/briefings/PRD.md"
    mock_agent_instance.run.return_value = mock_result

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
