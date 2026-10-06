"""Testes para os comandos de governança operacional e utilitários (ST-020, ST-021, ST-022).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.orchestrator import WaveOrchestrator
from bombe_code.turing.state_machine import AutonomyMode, EngineeringMode


@pytest.fixture
def orchestrator(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    mock_factory = MagicMock()
    mock_agent = MagicMock()
    mock_res = MagicMock()
    mock_res.data = "Ação de governança executada com sucesso."
    mock_agent.run.return_value = mock_res
    mock_factory.create_agent.return_value = mock_agent

    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db, llm_factory=mock_factory)
    orch.start_wave("ONDA-004")
    return orch


def test_set_mode_autonomy_and_engineering(orchestrator):
    # 1. Altera modo de autonomia para MANUAL
    res_manual = orchestrator.set_mode("manual")
    assert res_manual["success"] is True
    assert res_manual["autonomy_mode"] == AutonomyMode.MANUAL.value

    # 2. Altera modo de engenharia para VIBE
    res_vibe = orchestrator.set_mode("vibe")
    assert res_vibe["success"] is True
    assert res_vibe["engineering_mode"] == EngineeringMode.VIBE_CODE.value

    # 3. Altera de volta para TDD e AUTO
    orchestrator.set_mode("auto")
    orchestrator.set_mode("tdd")
    status = orchestrator.get_status()
    assert status["autonomy_mode"] == AutonomyMode.AUTO.value
    assert status["engineering_mode"] == EngineeringMode.TDD_CODE.value


def test_run_rca_and_simplify(orchestrator):
    # 1. RCA de incidente
    rca_res = orchestrator.run_rca("Falha intermitente na autenticação JWT")
    assert rca_res["success"] is True
    assert "report" in rca_res
    assert rca_res["incident"] == "Falha intermitente na autenticação JWT"

    # 2. Simplify em módulo
    simp_res = orchestrator.run_simplify("src/bombe_code/storage/project_db.py")
    assert simp_res["success"] is True
    assert simp_res["target"] == "src/bombe_code/storage/project_db.py"


def test_run_task_avulsa_without_state_advance(orchestrator):
    initial_stage = orchestrator.get_status()["stage"]

    # Executa task avulsa
    task_res = orchestrator.run_task(
        "Corrigir typo na doc de arquitetura", agent_handle="@unclebob"
    )
    assert task_res["success"] is True
    assert "output" in task_res

    # Confirma que a ONDA continua no mesmo estágio
    assert orchestrator.get_status()["stage"] == initial_stage


def test_generate_status_report(orchestrator):
    rep = orchestrator.generate_status_report()
    assert rep["wave_id"] == "ONDA-004"
    assert "tasks_summary" in rep
    assert "config" in rep
