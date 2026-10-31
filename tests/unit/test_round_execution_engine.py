"""Unit tests for RoundExecutionEngine, Kanban 1:1 invariant, DoD gatekeeper, and CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bombe_code.cli.commands.round import round_app
from bombe_code.orchestration.engine import (
    InvalidRoundScopeError,
    PendingDoDError,
    RoundExecutionEngine,
)


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
        "    status: ready\n"
        "    story_id: STORY-002\n"
        "  ROUND-3:\n"
        "    status: pending\n"
        "    story_id: STORY-003\n"
        "---\n\n"
        "# MISSION-01\n"
    )
    (mission_dir / "mission.md").write_text(mission_content, encoding="utf-8")

    # Round 1 goal (all completed)
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


def test_validate_round_scope_accepts_single_story():
    """AC-01: Verify engine accepts single story string or 1-element list."""
    engine = RoundExecutionEngine()
    assert engine.validate_round_scope("STORY-007") == "STORY-007"
    assert engine.validate_round_scope(["STORY-007"]) == "STORY-007"


def test_validate_round_scope_rejects_multiple_stories():
    """AC-01: Verify engine strictly rejects multiple stories per round with InvalidRoundScopeError."""
    engine = RoundExecutionEngine()

    with pytest.raises(InvalidRoundScopeError):
        engine.validate_round_scope(["STORY-001", "STORY-002"])

    with pytest.raises(InvalidRoundScopeError):
        engine.validate_round_scope("STORY-001, STORY-002")

    with pytest.raises(InvalidRoundScopeError):
        engine.validate_round_scope([])


def test_assert_no_dod_pendencies_passes_when_previous_round_is_done(tmp_path: Path):
    """AC-05: Verify check passes when previous round has all checkboxes checked."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    # Round 2 checking Round 1 (which is done with all - [x])
    engine.assert_no_dod_pendencies(2)


def test_assert_no_dod_pendencies_raises_when_previous_round_has_unchecked_dod(tmp_path: Path):
    """AC-05: Verify check raises PendingDoDError if previous round has unchecked items."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    # Corrupt Round 1 goal with unchecked item
    r1_goal_file = tmp_path / "docs" / "missions" / "01" / "rounds" / "round-01" / "goal.md"
    r1_goal_file.write_text(
        "---\nround: 1\nstatus: in_progress\n---\n"
        "- [x] Completed item\n"
        "- [ ] Pending uncompleted item\n",
        encoding="utf-8",
    )

    with pytest.raises(PendingDoDError) as exc_info:
        engine.assert_no_dod_pendencies(2)

    assert "round anterior 1 possui pendências" in str(exc_info.value).lower()


def test_start_round_stops_at_dor(tmp_path: Path):
    """AC-02: Verify start_round initializes upstream and stops deterministically at DoR."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    result = engine.start_round(2)
    assert result["status"] == "dor_ready"
    assert result["round"] == 2
    assert result["story_id"] == "STORY-002"
    assert "parada determinística na fronteira do dor" in result["message"].lower()


def test_full_round_executes_and_stops_at_round_boundary(tmp_path: Path):
    """AC-03: Verify full_round finishes round and stops without advancing to round 3."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    result = engine.full_round(2)
    assert result["status"] == "validated"
    assert result["round"] == 2
    assert result["next_round_auto_advanced"] is False


def test_all_rounds_pipeline(tmp_path: Path):
    """AC-04: Verify all_rounds iterates through remaining rounds in mission."""
    _scaffold_mock_mission(tmp_path)
    engine = RoundExecutionEngine(project_dir=tmp_path)

    results = engine.all_rounds()
    assert len(results) >= 2  # Rounds 2 and 3 executed
    assert all(r["status"] == "validated" for r in results)


def test_cli_round_start(tmp_path: Path):
    """CLI test: bombe-code round-start 2."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()

    result = runner.invoke(round_app, ["round-start", "2", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "DoR" in result.stdout or "ready" in result.stdout.lower()


def test_cli_round_full(tmp_path: Path):
    """CLI test: bombe-code round-full 2."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()

    result = runner.invoke(round_app, ["round-full", "2", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "validated" in result.stdout.lower() or "concluído" in result.stdout.lower()


def test_cli_round_all(tmp_path: Path):
    """CLI test: bombe-code round-all."""
    _scaffold_mock_mission(tmp_path)
    runner = CliRunner()

    result = runner.invoke(round_app, ["round-all", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "pipeline" in result.stdout.lower() or "concluídos" in result.stdout.lower()
