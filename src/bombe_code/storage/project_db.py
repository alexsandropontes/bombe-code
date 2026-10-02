"""Gerenciador do banco de dados local do projeto (.bombe-code/state.db) (ST-004)."""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class ProjectDatabase:
    """Banco de dados SQLite local isolado em .bombe-code/state.db.
    
    Gerencia checkpoints de estado da ONDA e o Kanban operacional de tasks dos agentes.
    """

    def __init__(self, project_dir: str = ".") -> None:
        self.project_dir = Path(project_dir).resolve()
        self.bombe_dir = self.project_dir / ".bombe-code"
        self.bombe_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.bombe_dir / "state.db"
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS wave_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    wave_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    autonomy_mode TEXT NOT NULL,
                    engineering_mode TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_tasks (
                    id TEXT PRIMARY KEY,
                    story_id TEXT NOT NULL,
                    agent_role TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    output TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )
            conn.commit()

    def save_wave_state(
        self,
        wave_id: str,
        state: str,
        autonomy_mode: str,
        engineering_mode: str,
    ) -> None:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO wave_state (id, wave_id, state, autonomy_mode, engineering_mode, updated_at)
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    wave_id = excluded.wave_id,
                    state = excluded.state,
                    autonomy_mode = excluded.autonomy_mode,
                    engineering_mode = excluded.engineering_mode,
                    updated_at = excluded.updated_at
                """,
                (wave_id, state, autonomy_mode, engineering_mode, now),
            )
            conn.commit()

    def load_wave_state(self) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM wave_state WHERE id = 1").fetchone()
            if row:
                return dict(row)
        return None

    def create_task(
        self,
        story_id: str,
        agent_role: str,
        title: str,
    ) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agent_tasks (id, story_id, agent_role, title, status, output, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', '', ?, ?)
                """,
                (task_id, story_id, agent_role, title, now, now),
            )
            conn.commit()
        return task_id

    def update_task_status(
        self,
        task_id: str,
        status: str,
        output: str = "",
    ) -> None:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE agent_tasks
                SET status = ?, output = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, output, now, task_id),
            )
            conn.commit()

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
            if row:
                return dict(row)
        return None

    def list_tasks(self, story_id: str | None = None) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            if story_id:
                rows = conn.execute(
                    "SELECT * FROM agent_tasks WHERE story_id = ? ORDER BY created_at ASC",
                    (story_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM agent_tasks ORDER BY created_at ASC").fetchall()
            return [dict(r) for r in rows]
