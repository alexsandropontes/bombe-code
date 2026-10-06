"""Testes unitários para a captura e persistência de telemetria de agentes e ONDAS.
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path
from unittest.mock import MagicMock

from bombe_code.agents.runner import AgentExecutionResult
from bombe_code.turing.orchestrator import WaveOrchestrator


def test_agent_execution_result_telemetry_defaults():
    res = AgentExecutionResult(
        agent_handle="@meira",
        agent_role="Business Analyst",
        output="Análise concluída",
        success=True,
    )
    assert res.input_tokens == 0
    assert res.output_tokens == 0
    assert res.total_tokens == 0
    assert res.cost == 0.0
    assert res.duration_seconds == 0.0


def test_agent_execution_result_telemetry_values():
    res = AgentExecutionResult(
        agent_handle="@grace",
        agent_role="Product Manager",
        output="PRD gerado",
        success=True,
        input_tokens=500,
        output_tokens=1500,
        total_tokens=2000,
        cost=0.0012,
        duration_seconds=42.5,
    )
    assert res.input_tokens == 500
    assert res.output_tokens == 1500
    assert res.total_tokens == 2000
    assert res.cost == 0.0012
    assert res.duration_seconds == 42.5


def test_wave_orchestrator_record_telemetry(tmp_path: Path):
    db_mock = MagicMock()
    orch = WaveOrchestrator(project_dir=tmp_path, db=db_mock)

    res1 = AgentExecutionResult(
        agent_handle="@meira",
        agent_role="Business Analyst",
        output="Viabilidade",
        success=True,
        input_tokens=100,
        output_tokens=400,
        total_tokens=500,
        cost=0.0001,
        duration_seconds=5.0,
    )
    orch._record_telemetry("DISCUSS", "@meira", res1)

    assert "DISCUSS" in orch.telemetry["stages"]
    stage = orch.telemetry["stages"]["DISCUSS"]
    assert stage["input_tokens"] == 100
    assert stage["output_tokens"] == 400
    assert stage["total_tokens"] == 500
    assert stage["cost"] == 0.0001
    assert stage["duration_seconds"] == 5.0
    assert len(stage["agents"]) == 1

    # Gravação dos arquivos de telemetria
    telemetry_file = tmp_path / "docs" / "telemetry.json"
    telemetria_md = tmp_path / "docs" / "telemetria.md"
    assert telemetry_file.exists()
    assert telemetria_md.exists()
    assert "DISCUSS" in telemetria_md.read_text(encoding="utf-8")
