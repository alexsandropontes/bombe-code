"""Testes unitários para o WaveWorkspace (Governança Documental: Projeto vs Ondas)."""

from pathlib import Path

from bombe_code.domain.wave.workspace import WaveWorkspace


def test_global_project_paths(tmp_path: Path):
    ws = WaveWorkspace(project_dir=tmp_path)
    assert ws.prd_path == tmp_path / "docs" / "briefings" / "PRD.md"
    assert ws.journey_master_path == tmp_path / "docs" / "architecture" / "journey.md"
    assert (
        ws.system_architecture_path == tmp_path / "docs" / "architecture" / "SYSTEM_ARCHITECTURE.md"
    )
    assert ws.db_schema_path == tmp_path / "docs" / "architecture" / "db.md"


def test_wave_specific_paths(tmp_path: Path):
    ws = WaveWorkspace(project_dir=tmp_path)
    wave_id = "ONDA-001"

    assert ws.wave_dir(wave_id) == tmp_path / "docs" / "waves" / "ONDA-001"
    assert ws.wave_epics_dir(wave_id) == tmp_path / "docs" / "waves" / "ONDA-001" / "epics"
    assert ws.wave_stories_dir(wave_id) == tmp_path / "docs" / "waves" / "ONDA-001" / "stories"
    assert ws.wave_qa_dir(wave_id) == tmp_path / "docs" / "waves" / "ONDA-001" / "qa"
    assert (
        ws.wave_journey_slice_path(wave_id)
        == tmp_path / "docs" / "waves" / "ONDA-001" / "journey-slice.md"
    )
    assert (
        ws.wave_validation_report_path(wave_id)
        == tmp_path / "docs" / "waves" / "ONDA-001" / "validation_report.md"
    )


def test_ensure_wave_structure(tmp_path: Path):
    ws = WaveWorkspace(project_dir=tmp_path)
    ws.ensure_wave_structure("ONDA-002")

    assert (tmp_path / "docs" / "waves" / "ONDA-002" / "epics").is_dir()
    assert (tmp_path / "docs" / "waves" / "ONDA-002" / "stories").is_dir()
    assert (tmp_path / "docs" / "waves" / "ONDA-002" / "qa").is_dir()


def test_find_story_file_resilient(tmp_path: Path):
    ws = WaveWorkspace(project_dir=tmp_path)
    ws.ensure_wave_structure("ONDA-001")

    # Cria story na nova pasta da onda
    story_file = ws.wave_stories_dir("ONDA-001") / "ST-001.md"
    story_file.write_text("# Story 1", encoding="utf-8")

    found = ws.find_story_file("ST-001", wave_id="ONDA-001")
    assert found == story_file

    # Fallback sem informar wave_id
    found_any = ws.find_story_file("ST-001")
    assert found_any == story_file
