"""Unit tests for manual round execution engine with DoR gate and Rich formatting."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bombe_code.cli.commands.round import round_app
from bombe_code.domain.contracts.round import (
    InvalidRoundStateError,
    RoundNotReadyError,
    RoundState,
    RoundStatus,
    SliceState,
    SliceType,
)
from bombe_code.orchestration.engine import RoundExecutionEngine


def _scaffold_mock_mission(base_dir: Path) -> Path:
    """Helper to create a realistic mock mission structure in base_dir."""
    mission_dir = base_dir / "docs" / "missions" / "01"
    rounds_dir = mission_dir / "rounds"
    rounds_dir.mkdir(parents=True, exist_ok=True)

    mission_content = (
        "---\n"
        "id: MISSION-01\n"
        "rounds:\n"
        "  ROUND-1:\n"
        "    status: validated\n"
        "    story_id: STORY-001\n"
        "  ROUND-2:\n"
        "    status: pending\n"
        "    story_id: STORY-002\n"
        "  ROUND-3:\n"
        "    status: pending\n"
        "    story_id: STORY-003\n"
        "---\n\n"
        "# MISSION-01\n"
    )
    (mission_dir / "mission.md").write_text(mission_content, encoding="utf-8")

    r1_dir = rounds_dir / "round-01"
    r1_dir.mkdir(parents=True, exist_ok=True)
    r1_goal = (
        "---\nround: 1\nstatus: done\n---\n"
        "## Checklist de Definition of Done (DoD)\n"
        "- [x] Task 1 completed\n"
        "- [x] Task 2 completed\n"
    )
    (r1_dir / "goal.md").write_text(r1_goal, encoding="utf-8")
    return mission_dir


def test_round_contracts_and_dict_compatibility():
    """Verify RoundState Pydantic V2 contract and dict-like access."""
    slice_1 = SliceState(
        slice_id="SLICE-01",
        name="Backend Slice",
        type=SliceType.BACKEND_TDD,
        status="pending",
    )
    state = RoundState(
        round_number=1,
        story_id="STORY-001",
        status=RoundStatus.DOR_READY,
        slices=[slice_1],
        dor_ready=True,
        dod_validated=False,
        message="Stopped at DoR",
    )

    assert state.round_number == 1
    assert state.status == RoundStatus.DOR_READY
    assert state.status == "dor_ready"
    assert state["round"] == 1
    assert state["story_id"] == "STORY-001"
    assert state["status"] == "dor_ready"
    assert state.get("dor_ready") is True
    assert state.get("non_existent", "default") == "default"


def test_start_round_generates_scaffolds_and_stops_at_dor(tmp_path: Path):
    """Verify start_round initializes physical scaffolds and marks DoR ready."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    state = engine.start_round(2)
    assert isinstance(state, RoundState)
    assert state.round_number == 2
    assert state.status == RoundStatus.DOR_READY
    assert state.dor_ready is True
    assert len(state.slices) >= 2
    assert state.slices[0].type == SliceType.BACKEND_TDD
    assert state.slices[1].type == SliceType.FRONTEND_CONSTRUCTION

    # Verify physical scaffolds
    rounds_dir = tmp_path / "docs" / "missions" / "01" / "rounds" / "round-02"
    assert (rounds_dir / "goal.md").exists()
    assert (rounds_dir / "stories.md").exists()


def test_burn_round_blocks_when_dor_not_ready(tmp_path: Path):
    """Verify burn_round blocks with RoundNotReadyError when round not at DoR."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    # Round 3 is pending, not started/DoR
    with pytest.raises(RoundNotReadyError) as exc_info:
        engine.burn_round(3)
    assert "não atingiu dor" in str(exc_info.value).lower()


def test_burn_round_transitions_slices_to_done(tmp_path: Path):
    """Verify burn_round executes slices and transitions status."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    engine.start_round(2)
    state = engine.burn_round(2)
    assert state.round_number == 2
    assert state.status in (RoundStatus.BURNING, RoundStatus.IN_PROGRESS)
    assert all(s.status == "done" for s in state.slices)


def test_review_round_lifecycle_gates(tmp_path: Path):
    """Verify review_round blocks if not burned, and succeeds after burn."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    engine.start_round(2)
    # Attempt review while still in DOR_READY
    with pytest.raises(InvalidRoundStateError):
        engine.review_round(2)

    engine.burn_round(2)
    rev_state = engine.review_round(2)
    assert rev_state.status == RoundStatus.REVIEWING


def test_validate_round_checks_dod_and_completes(tmp_path: Path):
    """Verify validate_round checks goal.md items and updates status to VALIDATED."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    engine.start_round(2)
    engine.burn_round(2)
    engine.review_round(2)
    val_state = engine.validate_round(2)

    assert val_state.status == RoundStatus.VALIDATED
    assert val_state.dod_validated is True

    # Verify goal.md has checkboxes checked
    goal_path = tmp_path / "docs" / "missions" / "01" / "rounds" / "round-02" / "goal.md"
    content = goal_path.read_text(encoding="utf-8")
    assert "- [ ]" not in content
    assert "- [x]" in content


def test_status_round_retrieves_rounds_and_single(tmp_path: Path):
    """Verify status_round retrieves list of rounds or single round state."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    engine.start_round(2)
    all_rounds = engine.status_round()
    assert isinstance(all_rounds, list)
    assert len(all_rounds) >= 3

    single = engine.status_round(2)
    assert isinstance(single, RoundState)
    assert single.round_number == 2
    assert single.status == RoundStatus.DOR_READY


def test_cli_round_burn_blocks_when_not_ready(tmp_path: Path):
    """CLI test: bombe round burn blocks when DoR gate is not fulfilled."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()

    result = runner.invoke(round_app, ["burn", "3", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1
    assert "não atingiu dor" in result.stdout.lower() or "bloqueante" in result.stdout.lower()


def test_cli_round_burn_and_review_and_validate(tmp_path: Path):
    """CLI test: complete manual flow start -> burn -> review -> validate."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()

    # 1. start
    res_start = runner.invoke(round_app, ["start", "2", "--project-dir", str(tmp_path)])
    assert res_start.exit_code == 0
    assert "dor" in res_start.stdout.lower() or "ready" in res_start.stdout.lower()

    # 2. burn
    res_burn = runner.invoke(round_app, ["burn", "2", "--project-dir", str(tmp_path)])
    assert res_burn.exit_code == 0
    assert "queimado" in res_burn.stdout.lower() or "burn" in res_burn.stdout.lower()

    # 3. review
    res_review = runner.invoke(round_app, ["review", "2", "--project-dir", str(tmp_path)])
    assert res_review.exit_code == 0
    assert "revis" in res_review.stdout.lower()

    # 4. validate
    res_val = runner.invoke(round_app, ["validate", "2", "--project-dir", str(tmp_path)])
    assert res_val.exit_code == 0
    assert "validado" in res_val.stdout.lower() or "dod" in res_val.stdout.lower()


def test_cli_round_status_table(tmp_path: Path):
    """CLI test: bombe round status renders Rich table with gates."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()

    runner.invoke(round_app, ["start", "2", "--project-dir", str(tmp_path)])
    res_status = runner.invoke(round_app, ["status", "--project-dir", str(tmp_path)])
    assert res_status.exit_code == 0
    assert "ROUND" in res_status.stdout.upper()
    assert "STORY" in res_status.stdout.upper()
    assert "DOR" in res_status.stdout.upper()
    assert "DOD" in res_status.stdout.upper()


