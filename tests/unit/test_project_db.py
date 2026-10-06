"""Testes unitários para o ProjectDatabase local (ST-004)."""

from __future__ import annotations

from pathlib import Path

from bombe_code.storage.project_db import ProjectDatabase


def test_init_creates_bombe_code_dir_and_db(tmp_path: Path):
    db = ProjectDatabase(project_dir=str(tmp_path))
    assert db.db_path.exists()


def test_save_and_load_wave_state(tmp_path: Path):
    db = ProjectDatabase(project_dir=str(tmp_path))
    db.save_wave_state(
        wave_id="ONDA-002",
        state="EXECUTE",
        autonomy_mode="AUTO",
        engineering_mode="tdd-code",
    )

    state = db.load_wave_state()
    assert state is not None
    assert state["wave_id"] == "ONDA-002"
    assert state["state"] == "EXECUTE"
    assert state["autonomy_mode"] == "AUTO"
    assert state["engineering_mode"] == "tdd-code"


def test_agent_tasks_crud_and_kanban(tmp_path: Path):
    db = ProjectDatabase(project_dir=str(tmp_path))

    # Criação de tasks internas dos agentes
    t1_id = db.create_task(
        story_id="ST-001",
        agent_role="Developer",
        title="Criar teste unitário RED",
    )
    t2_id = db.create_task(
        story_id="ST-001",
        agent_role="Developer",
        title="Implementar classe do classificador",
    )

    tasks_story = db.list_tasks(story_id="ST-001")
    assert len(tasks_story) == 2

    # Atualização de status
    db.update_task_status(t1_id, status="completed", output="Testes passaram")
    t1 = db.get_task(t1_id)
    assert t1 is not None
    assert t1["status"] == "completed"
    assert t1["output"] == "Testes passaram"

    # Verificação de status pendente na outra
    t2 = db.get_task(t2_id)
    assert t2 is not None
    assert t2["status"] == "pending"
