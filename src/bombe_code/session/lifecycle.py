from __future__ import annotations

from pydantic import TypeAdapter

from . import crud
from .models import CompactionPart, Message, Part, Session


def _ordered_messages(session_id: str) -> list[Message]:
    return crud.load_messages(session_id)


def revert_session(session_id: str, target_message_id: str) -> int:
    messages = _ordered_messages(session_id)
    ids = [m.id for m in messages]
    if target_message_id not in ids:
        raise FileNotFoundError(f"mensagem alvo nao encontrada: {target_message_id}")
    keep = ids[: ids.index(target_message_id) + 1]
    removed_parts = 0
    for message in messages[len(keep) :]:
        for part in crud.load_parts(session_id):
            if part.message_id == message.id:
                crud.delete_part(session_id, part.id)
                removed_parts += 1
        crud.delete_message(session_id, message.id)
    return len(messages) - len(keep)


def fork_session(session_id: str, at_message_id: str | None = None) -> Session:
    original = crud.load_session(session_id)
    messages = _ordered_messages(session_id)
    if at_message_id is not None:
        ids = [m.id for m in messages]
        if at_message_id not in ids:
            raise FileNotFoundError(f"mensagem alvo nao encontrada: {at_message_id}")
        messages = messages[: ids.index(at_message_id) + 1]

    child = crud.create_session(
        title=original.title,
        directory=original.directory,
        project_id=original.project_id,
        parent_id=original.id,
        agent=original.agent,
        model=original.model,
    )
    wanted = {m.id for m in messages}
    adapter = TypeAdapter(Part)
    for message in messages:
        data = message.model_dump()
        data["session_id"] = child.id
        crud.save_message(Message.model_validate(data))
    for part in crud.load_parts(session_id):
        if part.message_id in wanted:
            crud.save_part(child.id, adapter.validate_python(part.model_dump()))
    return child


def compact_session(session_id: str, summary: str) -> Message:
    message = Message(session_id=session_id, role="system")
    crud.save_message(message)
    crud.save_part(session_id, CompactionPart(message_id=message.id, summary=summary))
    return message
