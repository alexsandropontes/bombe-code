"""Testes unitários para o KanbanManager e sincronização física/lógica de cards (ST-029).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from pathlib import Path

from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.kanban import KanbanCardStatus, KanbanManager


def test_kanban_add_and_transition_card(tmp_path: Path):
    db = ProjectDatabase(str(tmp_path))
    km = KanbanManager(project_dir=str(tmp_path), db=db)

    # 1. Adiciona card inicial
    card = km.add_card(
        story_id="ST-030",
        wave_id="ONDA-006",
        title="Dashboard da Onda",
        agent="@norman",
        status=KanbanCardStatus.BACKLOG.value,
    )
    assert card["story_id"] == "ST-030"
    assert card["status"] == KanbanCardStatus.BACKLOG.value

    # 2. Transita para IN_PROGRESS
    res_prog = km.update_status("ST-030", KanbanCardStatus.IN_PROGRESS.value)
    assert res_prog["success"] is True
    assert res_prog["status"] == KanbanCardStatus.IN_PROGRESS.value

    # 3. Transita para DONE com reviews de @aniche e @unclebob
    reviews = {"@aniche": "Aprovado", "@unclebob": "Aprovado"}
    res_done = km.update_status("ST-030", KanbanCardStatus.DONE.value, reviews=reviews)
    assert res_done["success"] is True
    assert res_done["status"] == KanbanCardStatus.DONE.value
    assert res_done["reviews"] == reviews


def test_kanban_syncs_with_physical_markdown_file(tmp_path: Path):
    stories_dir = tmp_path / "docs" / "backlog" / "stories"
    stories_dir.mkdir(parents=True)

    story_file = stories_dir / "ST-030-wave-dashboard.md"
    story_file.write_text(
        """# STORY ST-030: Wave Dashboard\n\n> **Status:** READY\n> **Prioridade:** ALTA\n\nTexto.""",
        encoding="utf-8",
    )

    db = ProjectDatabase(str(tmp_path))
    km = KanbanManager(project_dir=str(tmp_path), db=db)
    km.add_card("ST-030", "ONDA-006", "Wave Dashboard", "@norman", status="READY")

    # Atualiza status para DONE no Kanban
    km.update_status("ST-030", KanbanCardStatus.DONE.value)

    # Verifica se o arquivo markdown foi sincronizado no disco
    updated_content = story_file.read_text(encoding="utf-8")
    assert "> **Status:** DONE" in updated_content


def test_kanban_scan_and_sync_existing_stories(tmp_path: Path):
    stories_dir = tmp_path / "docs" / "backlog" / "stories"
    stories_dir.mkdir(parents=True)

    (stories_dir / "ST-001-auth.md").write_text(
        "# STORY ST-001: Autenticacao\n\n> **Status:** READY\n", encoding="utf-8"
    )
    (stories_dir / "ST-002-perfil.md").write_text(
        "# STORY ST-002: Perfil de Usuario\n\n> **Status:** BACKLOG\n", encoding="utf-8"
    )

    db = ProjectDatabase(str(tmp_path))
    km = KanbanManager(project_dir=str(tmp_path), db=db)

    scanned = km.scan_and_sync_directory(wave_id="ONDA-006")
    assert len(scanned) == 2

    ids = [c["story_id"] for c in scanned]
    assert "ST-001" in ids
    assert "ST-002" in ids
