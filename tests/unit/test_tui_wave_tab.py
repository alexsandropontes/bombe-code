"""Testes unitários para o chaveamento de estações via Tab na TUI (ST-006 / EP-008)."""

from __future__ import annotations

from unittest.mock import MagicMock

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.tui.app import BombeTuiApp


def test_tui_initial_wave_station_and_cycle_wave_zero(tmp_path):
    """Em projeto novo / Greenfield (Onda Zero), o Tab cicla estritamente entre DISCOVERY e INCEPTION."""
    mock_client = MagicMock()
    app = BombeTuiApp(client=mock_client, project_dir=str(tmp_path))

    # Projeto novo nasce na Onda Zero em DISCOVERY
    assert app.wave_station == "DISCOVERY"

    # Tab 1 -> INCEPTION (Lean Inception Macro)
    app.action_cycle_station()
    assert app.wave_station == "INCEPTION"

    # Tab 2 -> Volta para DISCOVERY (bloqueando EXECUTE/VALIDATE na Onda 0)
    app.action_cycle_station()
    assert app.wave_station == "DISCOVERY"


def test_tui_cycle_delivery_wave(tmp_path):
    """Em Ondas de Entrega (1..N ou Brownfield), o Tab cicla PLAN ➔ REFINEMENT ➔ EXECUTE ➔ VALIDATE."""
    db = ProjectDatabase(str(tmp_path))
    db.save_wave_state(
        wave_id="ONDA-001",
        state="PLAN",
        autonomy_mode="AUTO",
        engineering_mode="tdd-code",
    )

    mock_client = MagicMock()
    app = BombeTuiApp(client=mock_client, project_dir=str(tmp_path))

    assert app.wave_station == "PLAN"

    # Tab 1 -> REFINEMENT (PBB Decomposer)
    app.action_cycle_station()
    assert app.wave_station == "REFINEMENT"

    # Tab 2 -> EXECUTE (TDD fullstack)
    app.action_cycle_station()
    assert app.wave_station == "EXECUTE"

    # Tab 3 -> VALIDATE (Quality & E2E)
    app.action_cycle_station()
    assert app.wave_station == "VALIDATE"

    # Tab 4 -> Volta para PLAN
    app.action_cycle_station()
    assert app.wave_station == "PLAN"


def test_status_text_includes_wave_station(tmp_path):
    mock_client = MagicMock()
    app = BombeTuiApp(client=mock_client, project_dir=str(tmp_path))
    app.wave_station = "INCEPTION"
    status = app._status_text()
    assert "INCEPTION" in status
