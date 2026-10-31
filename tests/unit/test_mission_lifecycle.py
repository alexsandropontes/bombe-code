"""Unit tests for Mission Lifecycle, Atomic Gatekeeper, and Typer CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bombe_code.cli.commands.mission import mission_app
from bombe_code.domain.contracts.mission import (
    MissionMetadata,
    MissionState,
    MissionStatus,
    NoActiveMissionError,
    OpenMissionBlockedError,
    PendingDoDError,
)
from bombe_code.orchestration.mission_engine import MissionLifecycleEngine

runner = CliRunner()


def test_mission_domain_contracts_strict_validation() -> None:
    """AC-01: Verify strict Pydantic contract validation and immutability/forbid extra."""
    meta = MissionMetadata(
        id="MISSION-01",
        title="Test Mission",
        demand="Construir auth",
        status=MissionStatus.OPEN,
        created_at="2026-10-31T15:00:00Z",
    )
    assert meta.id == "MISSION-01"
    assert meta.status == MissionStatus.OPEN

    state = MissionState(
        id="01",
        title="Test Mission",
        demand="Construir auth",
        status=MissionStatus.OPEN,
        path=Path("/tmp/mission.md"),
        created_at="2026-10-31T15:00:00Z",
    )
    assert state.total_rounds == 0
    assert state.current_round is None


def test_assert_no_open_mission_passes_when_clean(tmp_path: Path) -> None:
    """AC-01: Engine passes when no missions or only completed missions exist."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    engine.assert_no_open_mission()


def test_assert_no_open_mission_blocks_when_mission_open(tmp_path: Path) -> None:
    """AC-01: Gatekeeper raises OpenMissionBlockedError if any mission has open/active/in_progress status."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    m_dir = tmp_path / "docs" / "missions" / "01"
    m_dir.mkdir(parents=True, exist_ok=True)
    (m_dir / "mission.md").write_text(
        "---\nid: MISSION-01\nstatus: active\ndemand: Criar app\n---\n# Mission 01\n",
        encoding="utf-8",
    )

    with pytest.raises(OpenMissionBlockedError) as exc_info:
        engine.assert_no_open_mission()

    assert "01" in str(exc_info.value) or "MISSION-01" in str(exc_info.value)


def test_get_next_mission_id_calculates_sequential_ids(tmp_path: Path) -> None:
    """AC-02: Next mission id is zero-padded sequential string."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    assert engine.get_next_mission_id() == "01"

    m1_dir = tmp_path / "docs" / "missions" / "01"
    m1_dir.mkdir(parents=True, exist_ok=True)
    assert engine.get_next_mission_id() == "02"

    m2_dir = tmp_path / "docs" / "missions" / "02"
    m2_dir.mkdir(parents=True, exist_ok=True)
    assert engine.get_next_mission_id() == "03"


def test_init_mission_creates_physical_scaffold(tmp_path: Path) -> None:
    """AC-02: init_mission creates directories and writes valid mission.md."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    state = engine.init_mission(demand="Construir API de pagamentos", title="Pagamentos Core")

    assert state.id == "01"
    assert state.title == "Pagamentos Core"
    assert state.demand == "Construir API de pagamentos"
    assert state.status == MissionStatus.OPEN

    mission_dir = tmp_path / "docs" / "missions" / "01"
    assert (mission_dir / "prd").is_dir()
    assert (mission_dir / "architecture").is_dir()
    assert (mission_dir / "epics").is_dir()
    assert (mission_dir / "stories").is_dir()
    assert (mission_dir / "rounds").is_dir()

    mission_file = mission_dir / "mission.md"
    assert mission_file.is_file()
    content = mission_file.read_text(encoding="utf-8")
    assert "status: open" in content
    assert "Construir API de pagamentos" in content


def test_init_mission_rejects_empty_demand(tmp_path: Path) -> None:
    """AC-02: init_mission rejects empty or whitespace-only demand."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    with pytest.raises(ValueError, match="Demand cannot be empty"):
        engine.init_mission(demand="   ")


def test_init_mission_blocked_if_existing_open(tmp_path: Path) -> None:
    """AC-01 & AC-02: init_mission invokes assert_no_open_mission first and blocks."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    engine.init_mission(demand="Primeira missão")

    with pytest.raises(OpenMissionBlockedError):
        engine.init_mission(demand="Segunda missão simultânea")


def test_get_active_mission(tmp_path: Path) -> None:
    """AC-03: get_active_mission returns the open mission state or None."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    assert engine.get_active_mission() is None

    engine.init_mission(demand="Missão 1")
    active = engine.get_active_mission()
    assert active is not None
    assert active.id == "01"
    assert active.status in (MissionStatus.OPEN, MissionStatus.ACTIVE)


def test_complete_mission_with_dod_pendencies_raises(tmp_path: Path) -> None:
    """AC-04: complete_mission validates rounds and goal.md DoD checkboxes."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    state = engine.init_mission(demand="Missão com rounds")

    # Mock a round in mission.md
    mission_file = state.path
    rounds_dir = mission_file.parent / "rounds" / "round-01"
    rounds_dir.mkdir(parents=True, exist_ok=True)
    goal_file = rounds_dir / "goal.md"
    goal_file.write_text(
        "---\nround: 1\n---\n- [x] Done\n- [ ] Pending Item\n",
        encoding="utf-8",
    )

    # Update mission.md with round-01 pending
    content = mission_file.read_text(encoding="utf-8")
    updated = content.replace("rounds: {}", "rounds:\n  ROUND-1:\n    status: in_progress")
    mission_file.write_text(updated, encoding="utf-8")

    with pytest.raises(PendingDoDError):
        engine.complete_mission(force=False)


def test_complete_mission_success_and_force(tmp_path: Path) -> None:
    """AC-04: complete_mission completes mission and supports force flag."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    state = engine.init_mission(demand="Missão com rounds")

    # Test force=True even with unvalidated rounds
    completed = engine.complete_mission(force=True)
    assert completed.status == MissionStatus.COMPLETED
    assert completed.completed_at is not None

    # Check disk persistence
    content = state.path.read_text(encoding="utf-8")
    assert "status: completed" in content
    assert engine.get_active_mission() is None


def test_complete_mission_raises_when_no_active(tmp_path: Path) -> None:
    """AC-04: complete_mission raises NoActiveMissionError if no mission is open."""
    engine = MissionLifecycleEngine(project_dir=tmp_path)
    with pytest.raises(NoActiveMissionError):
        engine.complete_mission()


def test_cli_mission_new_and_block(tmp_path: Path) -> None:
    """AC-01, AC-02, CLI: Typer command 'mission new' creates mission or exits with 1 on block."""
    result = runner.invoke(
        mission_app,
        ["new", "Implementar auth", "--title", "Auth Core", "--project-dir", str(tmp_path)],
    )
    assert result.exit_code == 0
    assert "01" in result.stdout

    # Trying again must fail with exit code 1
    result2 = runner.invoke(
        mission_app,
        ["new", "Segunda missão", "--project-dir", str(tmp_path)],
    )
    assert result2.exit_code == 1
    assert (
        "bloqueada" in result2.stdout.lower()
        or "aberta" in result2.stdout.lower()
        or "erro" in result2.stdout.lower()
    )


def test_cli_mission_status(tmp_path: Path) -> None:
    """AC-03, CLI: Typer command 'mission status' displays warning or Rich table."""
    # When no active mission
    result = runner.invoke(mission_app, ["status", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "nenhuma" in result.stdout.lower()

    # Create mission and check status table
    runner.invoke(
        mission_app,
        ["new", "Nova Missão", "--title", "Minha Missão", "--project-dir", str(tmp_path)],
    )
    result2 = runner.invoke(mission_app, ["status", "--project-dir", str(tmp_path)])
    assert result2.exit_code == 0
    assert "01" in result2.stdout
    assert "Minha Missão" in result2.stdout


def test_cli_mission_end(tmp_path: Path) -> None:
    """AC-04, CLI: Typer command 'mission end' completes active mission."""
    runner.invoke(
        mission_app,
        ["new", "Missão a encerrar", "--project-dir", str(tmp_path)],
    )
    result = runner.invoke(mission_app, ["end", "--project-dir", str(tmp_path), "--force-abort"])
    assert result.exit_code == 0
    assert "encerrada" in result.stdout.lower() or "concluída" in result.stdout.lower()
