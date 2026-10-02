"""Testes unitários para Fail-Fast determinístico e validação de pré-requisitos em DISCUSS e PLAN."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import WaveState, TuringStage
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.agents.runner import AgentExecutionResult


def test_plan_fails_fast_when_prd_missing(tmp_path):
    """Se PRD.md não existir no disco, o PLAN barra antes de chamar qualquer arquiteto."""
    db = ProjectDatabase(tmp_path / "test.db")
    mock_factory = MagicMock()
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-FAIL-01")

    res = orch.run_plan()
    assert res["success"] is False
    assert "Pré-requisito ausente" in res["error"]
    assert "PRD.md" in res["error"]
    # Nenhum agente foi chamado
    mock_factory.create_agent.assert_not_called()


def test_plan_fails_fast_when_ieru_times_out(tmp_path):
    """Se @ieru falhar/dar timeout, o PLAN aborta IMEDIATAMENTE e NÃO chama @codd nem @caroli."""
    db = ProjectDatabase(tmp_path / "test.db")
    
    # Prepara PRD.md válido
    briefings_dir = tmp_path / "docs" / "briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    (briefings_dir / "PRD.md").write_text("# PRD\n" + "x" * 100, encoding="utf-8")

    mock_factory = MagicMock()
    mock_agent = MagicMock()

    calls = []

    def mock_run(prompt, context=None):
        m = MagicMock()
        if "Mapeie a jornada" in prompt:
            calls.append("@alan")
            m.data = "## Entry Points\nHome\n## Fluxo de Navegação\nFluxo\n## Telas\nMain\n"
            return m
        elif "Defina as decisões técnicas" in prompt:
            calls.append("@ieru")
            # Simula timeout / falha
            raise RuntimeError("Request timed out.")
        elif "Projete a modelagem" in prompt:
            calls.append("@codd")
            m.data = "schema"
            return m
        elif "Decomponha" in prompt:
            calls.append("@caroli")
            m.data = "stories"
            return m
        return m

    mock_agent.run.side_effect = mock_run
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-FAIL-02")

    res = orch.run_plan()
    assert res["success"] is False
    assert "Falha no arquiteto @ieru" in res["error"]
    assert "Fail-Fast" in res["error"]

    # Garante que @alan foi chamado, @ieru tentou e falhou, e @codd e @caroli NUNCA foram chamados
    assert "@alan" in calls
    assert "@ieru" in calls
    assert "@codd" not in calls
    assert "@caroli" not in calls
