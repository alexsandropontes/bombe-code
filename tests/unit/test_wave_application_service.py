"""Testes unitários do WaveApplicationService (DDD Application Layer)."""

from pathlib import Path
from unittest.mock import MagicMock

from bombe_code.application.wave.service import WaveApplicationService


def test_wave_service_events_and_start(tmp_path: Path):
    events: list[dict] = []
    service = WaveApplicationService(project_dir=tmp_path, on_event=lambda ev: events.append(ev))

    res = service.start_wave(wave_id="ONDA-777", autonomy_mode="AUTO")
    assert res.get("success") is True
    assert any(e["type"] == "wave.starting" for e in events)
    assert any(e["type"] == "wave.started" for e in events)

    status = service.get_status()
    assert status["wave_id"] == "ONDA-777"
    assert status["autonomy_mode"] == "AUTO"


def test_wave_service_cascade_dispatch(tmp_path: Path):
    events: list[dict] = []
    mock_orch = MagicMock()
    mock_orch.run_discuss.return_value = {"success": True, "stage": "DISCUSS"}
    mock_orch.run_plan.return_value = {"success": True, "stage": "PLAN"}
    mock_orch.run_execute.return_value = {"success": True, "stage": "EXECUTE"}
    mock_orch.run_validate.return_value = {"success": True, "stage": "VALIDATE"}
    mock_orch.end_wave.return_value = {"success": True, "wave_id": "ONDA-001"}
    mock_orch.db.load_wave_state.return_value = {"autonomy_mode": "AUTO"}

    service = WaveApplicationService(
        project_dir=tmp_path,
        orchestrator=mock_orch,
        on_event=lambda ev: events.append(ev),
    )

    res = service.execute_with_auto_cascade("DISCUSS", input_text="Criar app")
    assert res.get("success") is True
    assert mock_orch.run_discuss.called
    assert mock_orch.run_plan.called
    assert mock_orch.run_execute.called
    assert mock_orch.run_validate.called
    assert mock_orch.end_wave.called
    assert any(e["type"] == "wave.cascade_advancing" for e in events)
