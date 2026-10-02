from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from ..config.paths import get_paths
from .kv import read_json, write_json


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else get_paths().data / "storage"

    @property
    def _base(self) -> Path:
        return self.root / "session"

    def create_session(self, title: str = "", directory: str = "") -> dict:
        session = {
            "id": f"ses_{uuid.uuid4().hex}",
            "title": title,
            "directory": directory,
            "created_at": datetime.now(UTC).isoformat(),
        }
        write_json(self._base / "info" / f"{session['id']}.json", session)
        return session

    def get_session(self, session_id: str) -> dict:
        data = read_json(self._base / "info" / f"{session_id}.json")
        if data is None:
            raise FileNotFoundError(f"Sessao nao encontrada: {session_id}")
        return data

    def save_session(self, session: dict) -> None:
        write_json(self._base / "info" / f"{session['id']}.json", session)

    def _read_dir(self, directory: Path) -> list[dict]:
        if not directory.is_dir():
            return []
        items: list[dict] = []
        for path in sorted(directory.glob("*.json")):
            data = read_json(path)
            if data is not None:
                items.append(data)
        return items

    def list_sessions(self) -> list[dict]:
        return self._read_dir(self._base / "info")

    def save_message(self, session_id: str, message: dict) -> None:
        write_json(self._base / "message" / session_id / f"{message['id']}.json", message)

    def _list(self, kind: str, session_id: str) -> list[dict]:
        return self._read_dir(self._base / kind / session_id)

    def list_messages(self, session_id: str) -> list[dict]:
        return self._list("message", session_id)

    def save_part(self, session_id: str, part: dict) -> None:
        write_json(self._base / "part" / session_id / f"{part['id']}.json", part)

    def list_parts(self, session_id: str) -> list[dict]:
        return self._list("part", session_id)

    def delete_message(self, session_id: str, message_id: str) -> None:
        path = self._base / "message" / session_id / f"{message_id}.json"
        path.unlink(missing_ok=True)

    def delete_part(self, session_id: str, part_id: str) -> None:
        path = self._base / "part" / session_id / f"{part_id}.json"
        path.unlink(missing_ok=True)
