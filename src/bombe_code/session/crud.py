from __future__ import annotations

from pydantic import TypeAdapter

from ..storage.session_store import SessionStore
from .models import Message, Part, Session


def create_session(title: str = "", directory: str = "", **kwargs) -> Session:
    if "stage" not in kwargs:
        try:
            from ..storage.project_db import ProjectDatabase

            db = ProjectDatabase(directory or ".")
            saved = db.load_wave_state()
            if saved and saved.get("state"):
                kwargs["stage"] = str(saved["state"]).upper()
        except Exception:  # noqa: BLE001, S110
            pass

    session = Session(title=title, directory=directory, **kwargs)
    SessionStore().save_session(session.model_dump())
    return session


def save_session(session: Session) -> None:
    SessionStore().save_session(session.model_dump())


def load_session(session_id: str) -> Session:
    return Session.model_validate(SessionStore().get_session(session_id))


def list_sessions() -> list[Session]:
    return [Session.model_validate(data) for data in SessionStore().list_sessions()]


def save_message(message: Message) -> None:
    SessionStore().save_message(message.session_id, message.model_dump())


def load_messages(session_id: str) -> list[Message]:
    messages = [Message.model_validate(data) for data in SessionStore().list_messages(session_id)]
    return sorted(messages, key=lambda m: (m.created_at, m.id))


def save_part(session_id: str, part: Part) -> None:
    SessionStore().save_part(session_id, part.model_dump())


def load_parts(session_id: str) -> list[Part]:
    adapter = TypeAdapter(Part)
    parts = [adapter.validate_python(data) for data in SessionStore().list_parts(session_id)]
    return sorted(parts, key=lambda p: (p.created_at, p.id))


def delete_message(session_id: str, message_id: str) -> None:
    SessionStore().delete_message(session_id, message_id)


def delete_part(session_id: str, part_id: str) -> None:
    SessionStore().delete_part(session_id, part_id)
