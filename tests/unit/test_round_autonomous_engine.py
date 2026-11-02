"""Tests for Autonomous Round Execution (execute_round_full and execute_round_all) - STORY-011."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from bombe_code.cli.commands.round import round_app
from bombe_code.domain.contracts.round import RoundState, RoundStatus
from bombe_code.orchestration.engine import RoundExecutionEngine


def _scaffold_mission(tmp_path: Path, rounds_dict: dict[str, dict] | None = None) -> Path:
    """Helper to create physical scaffolding for testing."""
    mission_dir = tmp_path / "docs" / "missions" / "01"
    rounds_dir = mission_dir / "rounds"
    rounds_dir.mkdir(parents=True, exist_ok=True)

    if rounds_dict is None:
        rounds_dict = {
            "ROUND-1": {"status": "validated", "story_id": "STORY-001"},
            "ROUND-2": {"status": "pending", "story_id": "STORY-002"},
            "ROUND-10": {"status": "pending", "story_id": "STORY-010"},
        }

    # Scaffold Round 1 goal as validated
    r1_dir = rounds_dir / "round-01"
    r1_dir.mkdir(parents=True, exist_ok=True)
    r1_goal = r1_dir / "goal.md"
    r1_goal.write_text(
        "---\nround: 1\nstatus: validated\nstory_id: STORY-001\n"
        "dor_ready: true\ndod_validated: true\n---\n"
        "# Round 1\n- [x] Done\n",
        encoding="utf-8",
    )

    mission_file = mission_dir / "mission.md"
    fm = yaml.safe_dump({"id": "01", "status": "in_progress", "rounds": rounds_dict}, sort_keys=False)
    mission_file.write_text(f"---\n{fm}---\n# Mission 01\n", encoding="utf-8")
    return mission_file


def test_execute_round_full_transitions_and_stops_at_boundary(tmp_path: Path) -> None:
    """Slice 1: execute_round_full executes upstream, burn, review, validate and stops."""
    _scaffold_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    state = engine.execute_round_full(2)

    assert isinstance(state, RoundState)
    assert state.round_number == 2
    assert state.story_id == "STORY-002"
    assert state.status == RoundStatus.VALIDATED
    assert state.dor_ready is True
    assert state.dod_validated is True
    assert state.next_round_auto_advanced is False

    # Backwards compatibility alias
    assert engine.full_round == engine.execute_round_full


def test_execute_round_all_sorts_numeric_order(tmp_path: Path) -> None:
    """Slice 2: execute_round_all must process rounds in strict numeric order (1, 2, 10)."""
    rounds = {
        "ROUND-10": {"status": "pending", "story_id": "STORY-010"},
        "ROUND-1": {"status": "validated", "story_id": "STORY-001"},
        "ROUND-2": {"status": "pending", "story_id": "STORY-002"},
    }
    _scaffold_mission(tmp_path, rounds)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    results = engine.execute_round_all()

    assert len(results) == 2
    assert [r.round_number for r in results] == [2, 10]
    assert all(r.status == RoundStatus.VALIDATED for r in results)
    assert all(r.dod_validated is True for r in results)

    # Backwards compatibility alias
    assert engine.all_rounds == engine.execute_round_all


def test_execute_round_all_fail_fast_on_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Slice 2: execute_round_all stops immediately on failure without running subsequent rounds."""
    rounds = {
        "ROUND-1": {"status": "validated", "story_id": "STORY-001"},
        "ROUND-2": {"status": "pending", "story_id": "STORY-002"},
        "ROUND-3": {"status": "pending", "story_id": "STORY-003"},
    }
    _scaffold_mission(tmp_path, rounds)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    executed_rounds: list[int] = []

    def mock_execute_round_full(round_num: int) -> RoundState:
        executed_rounds.append(round_num)
        if round_num == 2:
            return RoundState(
                round_number=round_num,
                story_id="STORY-002",
                status=RoundStatus.BURNING,  # Not validated
                dod_validated=False,
                message="Simulated test suite failure in slice execution",
            )
        return RoundState(
            round_number=round_num,
            story_id=f"STORY-{round_num:03d}",
            status=RoundStatus.VALIDATED,
            dod_validated=True,
        )

    monkeypatch.setattr(engine, "execute_round_full", mock_execute_round_full)

    with pytest.raises(RuntimeError) as exc_info:
        engine.execute_round_all()

    assert "Round 2 falhou na validação" in str(exc_info.value)
    # Round 3 must NOT have been executed
    assert executed_rounds == [2]


def test_assert_no_test_failures_validation() -> None:
    """Slice 2: _assert_no_test_failures raises RuntimeError for non-validated or dod_validated=False."""
    engine = RoundExecutionEngine()
    invalid_state = RoundState(
        round_number=5,
        story_id="STORY-005",
        status=RoundStatus.BURNING,
        dod_validated=False,
        message="Tests failed",
    )

    with pytest.raises(RuntimeError) as exc_info:
        engine._assert_no_test_failures(invalid_state)

    assert "Round 5 falhou na validação: Tests failed" in str(exc_info.value)

    valid_state = RoundState(
        round_number=5,
        story_id="STORY-005",
        status=RoundStatus.VALIDATED,
        dod_validated=True,
    )
    # Should not raise
    engine._assert_no_test_failures(valid_state)


def test_cli_round_full_command(tmp_path: Path) -> None:
    """Slice 3: CLI round full executes semi-auto round."""
    _scaffold_mission(tmp_path)
    runner = CliRunner()

    result = runner.invoke(round_app, ["full", "2", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Round 2" in result.output
    assert "validado com sucesso" in result.output or "VALIDADO" in result.output


def test_cli_round_all_command(tmp_path: Path) -> None:
    """Slice 3: CLI round all executes pipeline and instructs mission end."""
    _scaffold_mission(tmp_path)
    runner = CliRunner()

    result = runner.invoke(round_app, ["all", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "Pipeline concluído" in result.output or "Pipeline de Rounds Concluído" in result.output
    assert "bombe mission end" in result.output


def test_cli_round_all_error_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Slice 3: CLI round all fails cleanly with exit code 1 when an exception occurs."""
    _scaffold_mission(tmp_path)
    runner = CliRunner()

    def mock_all(self, timeout=None):
        raise RuntimeError("Round 2 falhou na validação: Testes falharam")

    monkeypatch.setattr(RoundExecutionEngine, "execute_round_all", mock_all)

    result = runner.invoke(round_app, ["all", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "ERRO BLOQUEANTE" in result.output


def test_zero_confirmations_in_round_cli() -> None:
    """Slice 3: Enforce zero typer.confirm or input() in round.py (Anti-Confirmações)."""
    import bombe_code.cli.commands.round as round_module

    source = inspect.getsource(round_module)
    assert "typer.confirm" not in source, "Proibido usar typer.confirm em round.py"
    assert "input(" not in source, "Proibido usar input() em round.py"
    assert "confirm(" not in source, "Proibido usar confirm() em round.py"
