"""Testes unitários para o chaveamento de estações via Tab na TUI (ST-006)."""

from __future__ import annotations

from unittest.mock import MagicMock

from bombe_code.tui.app import BombeTuiApp


def test_tui_initial_wave_station_and_cycle():
    mock_client = MagicMock()
    app = BombeTuiApp(client=mock_client)

    assert app.wave_station == "DISCUSS"

    # Tab 1 -> PLAN
    app.action_cycle_station()
    assert app.wave_station == "PLAN"

    # Tab 2 -> EXECUTE
    app.action_cycle_station()
    assert app.wave_station == "EXECUTE"

    # Tab 3 -> VALIDATE
    app.action_cycle_station()
    assert app.wave_station == "VALIDATE"

    # Tab 4 -> Volta para DISCUSS
    app.action_cycle_station()
    assert app.wave_station == "DISCUSS"


def test_status_text_includes_wave_station():
    mock_client = MagicMock()
    app = BombeTuiApp(client=mock_client)
    app.wave_station = "EXECUTE"
    status = app._status_text()
    assert "EXECUTE" in status
