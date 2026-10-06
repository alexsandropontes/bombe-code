"""Gerenciador do banco de dados local do projeto (.bombe-code/state.db) (ST-004)."""

from __future__ import annotations

import json
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

                CREATE TABLE IF NOT EXISTS kanban_cards (
                    story_id TEXT PRIMARY KEY,
                    wave_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reviews TEXT NOT NULL DEFAULT '{}',
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    block_reason TEXT NOT NULL DEFAULT '',
                    blocked_by TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS wave_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wave_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    autonomy_mode TEXT NOT NULL,
                    engineering_mode TEXT NOT NULL,
                    archived_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runtime_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )
            # Migração segura para tabelas já criadas
            try:
                conn.execute(
                    "ALTER TABLE kanban_cards ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0"
                )
            except Exception:  # noqa: BLE001, S110
                pass
            try:
                conn.execute(
                    "ALTER TABLE kanban_cards ADD COLUMN block_reason TEXT NOT NULL DEFAULT ''"
                )
            except Exception:  # noqa: BLE001, S110
                pass
            try:
                conn.execute(
                    "ALTER TABLE kanban_cards ADD COLUMN blocked_by TEXT NOT NULL DEFAULT ''"
                )
            except Exception:  # noqa: BLE001, S110
                pass

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

    def archive_wave_state(self) -> dict[str, Any] | None:
        """Arquiva o checkpoint ativo no histórico (nunca destrói estado).

        Parte da autonomia do Turing: trocar de onda não exige decisão humana
        nem flag de força — o checkpoint anterior é preservado em wave_history.
        """
        saved = self.load_wave_state()
        if not saved:
            return None
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO wave_history (wave_id, state, autonomy_mode, engineering_mode, archived_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    saved["wave_id"],
                    saved["state"],
                    saved["autonomy_mode"],
                    saved["engineering_mode"],
                    time.time(),
                ),
            )
        return saved

    def load_wave_checkpoint(self, wave_id: str) -> dict[str, Any] | None:
        """Recupera do histórico o checkpoint MAIS RECENTE de uma onda específica."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM wave_history
                WHERE UPPER(wave_id) = UPPER(?)
                ORDER BY archived_at DESC
                LIMIT 1
                """,
                (wave_id,),
            ).fetchone()
            if row:
                return dict(row)
        return None

    def get_meta(self, key: str) -> str | None:
        """Lê uma chave de metadados do runtime (orçamentos, assinaturas)."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT value FROM runtime_meta WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        """Grava uma chave de metadados do runtime."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO runtime_meta (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, time.time()),
            )

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

    def create_agent_task(
        self,
        agent_handle: str,
        description: str,
        story_id: str = "GLOBAL",
    ) -> str:
        """Cria e registra uma task operacional de agente no SQLite."""
        return self.create_task(story_id=story_id, agent_role=agent_handle, title=description)

    def update_agent_task_status(
        self,
        task_id: str,
        status: str,
        output: str = "",
    ) -> None:
        """Atualiza o status de uma task operacional de agente."""
        self.update_task_status(task_id=task_id, status=status, output=output)

    def list_agent_tasks(self, agent_handle: str | None = None) -> list[dict[str, Any]]:
        """Lista tasks filtradas pelo handle do agente ou todas."""
        with self._get_connection() as conn:
            if agent_handle:
                rows = conn.execute(
                    "SELECT * FROM agent_tasks WHERE agent_role = ? ORDER BY created_at ASC",
                    (agent_handle,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM agent_tasks ORDER BY created_at ASC").fetchall()
            return [dict(r) for r in rows]

    def save_kanban_card(
        self,
        story_id: str,
        wave_id: str,
        title: str,
        agent: str,
        status: str,
        reviews: dict[str, Any] | None = None,
        is_blocked: bool = False,
        block_reason: str = "",
        blocked_by: str = "",
    ) -> None:
        """Cria ou atualiza um card no Kanban do SQLite."""
        now = time.time()
        rev_json = json.dumps(reviews or {}, ensure_ascii=False)
        flag_val = 1 if is_blocked else 0
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO kanban_cards (
                    story_id, wave_id, title, agent, status, reviews,
                    is_blocked, block_reason, blocked_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(story_id) DO UPDATE SET
                    wave_id = excluded.wave_id,
                    title = excluded.title,
                    agent = excluded.agent,
                    status = excluded.status,
                    reviews = excluded.reviews,
                    is_blocked = excluded.is_blocked,
                    block_reason = excluded.block_reason,
                    blocked_by = excluded.blocked_by,
                    updated_at = excluded.updated_at
                """,
                (
                    story_id,
                    wave_id,
                    title,
                    agent,
                    status,
                    rev_json,
                    flag_val,
                    block_reason,
                    blocked_by,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_kanban_card(self, story_id: str) -> dict[str, Any] | None:
        """Obtém um card do Kanban pelo story_id."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM kanban_cards WHERE story_id = ?", (story_id,)
            ).fetchone()
            if row:
                res = dict(row)
                try:
                    res["reviews"] = json.loads(res.get("reviews", "{}"))
                except (json.JSONDecodeError, TypeError):
                    res["reviews"] = {}
                return res
        return None

    def list_kanban_cards(self, wave_id: str | None = None) -> list[dict[str, Any]]:
        """Lista cards do Kanban, opcionalmente filtrados por ONDA."""
        with self._get_connection() as conn:
            if wave_id:
                rows = conn.execute(
                    "SELECT * FROM kanban_cards WHERE wave_id = ? ORDER BY created_at ASC",
                    (wave_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM kanban_cards ORDER BY created_at ASC").fetchall()

            res = []
            for r in rows:
                card = dict(r)
                try:
                    card["reviews"] = json.loads(card.get("reviews", "{}"))
                except (json.JSONDecodeError, TypeError):
                    card["reviews"] = {}
                res.append(card)
            return res

    def update_kanban_card_status(
        self,
        story_id: str,
        status: str,
        reviews: dict[str, Any] | None = None,
    ) -> bool:
        """Atualiza o status e reviews de um card do Kanban."""
        now = time.time()
        with self._get_connection() as conn:
            if reviews is not None:
                rev_json = json.dumps(reviews, ensure_ascii=False)
                cur = conn.execute(
                    """
                    UPDATE kanban_cards
                    SET status = ?, reviews = ?, updated_at = ?
                    WHERE story_id = ?
                    """,
                    (status, rev_json, now, story_id),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE kanban_cards
                    SET status = ?, updated_at = ?
                    WHERE story_id = ?
                    """,
                    (status, now, story_id),
                )
            conn.commit()
            return cur.rowcount > 0

    def set_kanban_card_blocked(
        self,
        story_id: str,
        is_blocked: bool,
        reason: str = "",
        blocked_by: str = "",
    ) -> bool:
        """Altera a flag de bloqueio de um card no local do problema."""
        now = time.time()
        flag_val = 1 if is_blocked else 0
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                UPDATE kanban_cards
                SET is_blocked = ?, block_reason = ?, blocked_by = ?, updated_at = ?
                WHERE story_id = ?
                """,
                (
                    flag_val,
                    reason if is_blocked else "",
                    blocked_by if is_blocked else "",
                    now,
                    story_id,
                ),
            )
            conn.commit()
            return cur.rowcount > 0
