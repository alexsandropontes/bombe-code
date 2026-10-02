from __future__ import annotations

import json
import time
from collections.abc import Callable

from ..tools.base import ToolContext
from . import crud
from .models import Message, Session, TextPart
from .processor import TurnProcessor
from .system import build_system_prompt
from .to_provider import to_provider_messages

_MAX_RETRIES = 3
_RETRY_DELAY = 0.1
_MAX_SUBTASK_DEPTH = 3


def _never_abort() -> bool:
    return False


def _always_allow(permission: str, details: str = "") -> str:
    return "allow"


def tool_signature(event: dict) -> str:
    arguments = json.dumps(event.get("arguments", {}), sort_keys=True, separators=(",", ":"))
    return f"{event['name']}:{arguments}"


def _history(session_id: str):
    parts_by_message: dict[str, list] = {}
    for part in crud.load_parts(session_id):
        parts_by_message.setdefault(part.message_id, []).append(part)
    return [
        (message, parts_by_message.get(message.id, []))
        for message in crud.load_messages(session_id)
    ]


def _open_stream(adapter, messages, tools, system):
    delay = _RETRY_DELAY
    for attempt in range(_MAX_RETRIES):
        try:
            return adapter.stream(messages, tools=tools, system=system)
        except (ConnectionError, TimeoutError):
            if attempt == _MAX_RETRIES - 1:
                raise
            time.sleep(delay)
            delay *= 2


def _execute_tool(registry, event: dict, ctx) -> tuple[str, bool]:
    try:
        return registry.execute(event["name"], event.get("arguments", {}), ctx), False
    except Exception as exc:  # noqa: BLE001 — falha de tool vira output de erro, nunca derruba o loop
        return f"Erro: {exc}", True


def _prepare_turn(
    session: Session,
    adapter,
    registry,
    permissions,
    messages: list[dict],
    ask,
    run_subtask,
    abort,
    project_instructions: str | None,
):
    stage = getattr(session, "stage", "DISCUSS") or "DISCUSS"
    system = build_system_prompt(session.agent or "build", project_instructions, stage=stage)
    disabled = permissions.disabled_tools() if permissions is not None else set()
    tools_meta = [
        {"id": t.id, "description": t.description, "schema": t.json_schema()}
        for t in registry.tools_for_model(getattr(adapter, "model", ""), disabled=disabled)
    ]
    ctx = ToolContext(
        session_id=session.id,
        agent=session.agent or "build",
        stage=stage,
        project_dir=session.directory,
        messages=messages,
        ask=ask,
        run_subtask=run_subtask,
        abort=abort,
    )
    return system, tools_meta, ctx



def _handle_event(event, processor, recent_signatures, ask, ctx, registry) -> str | None:
    """Processa um evento de stream. Retorna finish prematuro ou None."""
    if event["type"] == "tool-call":
        signature = tool_signature(event)
        if (
            len(recent_signatures) >= 2
            and recent_signatures[-1] == signature
            and recent_signatures[-2] == signature
        ):
            if str(ask("loop", signature)) == "deny":
                return "stop"
            recent_signatures.clear()
        part = processor.start_tool(event)
        output, is_error = _execute_tool(registry, event, ctx)
        processor.complete_tool(part, output, error=is_error)
        recent_signatures.append(signature)
        recent_signatures[:] = recent_signatures[-2:]
        processor.emit(event)
        return None
    if event["type"] == "text-delta":
        processor.add_text(event["text"])
        processor.emit(event)
    return None


def run_prompt(
    session: Session,
    user_text: str,
    *,
    adapter,
    registry,
    permissions=None,
    max_steps: int = 20,
    on_event: Callable | None = None,
    abort: Callable[[], bool] | None = None,
    project_instructions: str | None = None,
    depth: int = 0,
) -> str:
    abort = abort or _never_abort
    ask = permissions.ask if permissions is not None else _always_allow

    def run_subtask(prompt: str) -> str:
        if depth >= _MAX_SUBTASK_DEPTH:
            return "Limite de subtasks atingido"
        child = crud.create_session(
            title="subtask",
            directory=session.directory,
            project_id=session.project_id,
            parent_id=session.id,
            agent=session.agent,
            model=session.model,
        )
        return run_prompt(
            child,
            prompt,
            adapter=adapter,
            registry=registry,
            permissions=permissions,
            max_steps=max_steps,
            on_event=on_event,
            abort=abort,
            project_instructions=project_instructions,
            depth=depth + 1,
        )

    user_message = Message(session_id=session.id, role="user")
    crud.save_message(user_message)
    crud.save_part(session.id, TextPart(message_id=user_message.id, text=user_text))

    final_text = ""
    recent_signatures: list[str] = []

    for _step in range(max_steps):
        if abort():
            break

        messages = to_provider_messages(_history(session.id), adapter.provider)
        system, tools_meta, ctx = _prepare_turn(
            session,
            adapter,
            registry,
            permissions,
            messages,
            ask,
            run_subtask,
            abort,
            project_instructions,
        )
        processor = TurnProcessor(session.id, on_event=on_event)
        stream = _open_stream(adapter, messages, tools_meta, system)
        finish_reason = "unknown"
        aborted = False

        for event in stream:
            if event["type"] == "finish":
                finish_reason = event.get("reason", "unknown")
                continue
            if abort():
                aborted = True
                break
            premature = _handle_event(event, processor, recent_signatures, ask, ctx, registry)
            if premature is not None:
                finish_reason = premature
                break
            if abort():
                aborted = True
                break

        if aborted:
            processor.cleanup_aborted()
            break

        processor.flush()
        if processor.text:
            final_text = processor.text

        if finish_reason == "tool-calls":
            continue
        if finish_reason == "unknown" and processor.has_tools:
            continue
        break

    return final_text
