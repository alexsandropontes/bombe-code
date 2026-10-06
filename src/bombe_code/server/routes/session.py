import logging
import threading
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ...session import crud
from ...session.lifecycle import compact_session, revert_session
from ...session.loop import run_prompt
from ..bus import sse_format
from ..deps import ServerDeps

logger = logging.getLogger(__name__)


def _session_or_404(session_id: str):
    try:
        return crud.load_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


class SessionBody(BaseModel):
    title: str = ""
    directory: str = ""
    stage: str | None = None


class PromptBody(BaseModel):
    text: str
    model: str | None = None
    stage: str | None = None


class StageBody(BaseModel):
    stage: str


class CompactBody(BaseModel):
    summary: str


class ModelBody(BaseModel):
    model: str


class AgentBody(BaseModel):
    agent: str


class PermissionReplyBody(BaseModel):
    permission: str
    details: str
    decision: str


class QuestionReplyBody(BaseModel):
    question: str
    answer: str


def build_session_router(deps: ServerDeps) -> APIRouter:
    router = APIRouter()
    ask = deps.ask_router()

    @router.post("/api/session")
    def create_session(body: SessionBody):
        directory = body.directory or deps.project_dir
        kwargs = {}
        if body.stage:
            kwargs["stage"] = body.stage.upper()
        session = crud.create_session(title=body.title, directory=directory, **kwargs)
        return session.model_dump()

    @router.get("/api/session")
    def list_sessions():
        return [s.model_dump() for s in crud.list_sessions()]

    @router.get("/api/session/{session_id}/message")
    def list_messages(session_id: str):
        _session_or_404(session_id)
        return [m.model_dump() for m in crud.load_messages(session_id)]

    @router.get("/api/session/{session_id}/history")
    def history(session_id: str):
        _session_or_404(session_id)
        return [m.model_dump() for m in crud.load_messages(session_id)]

    @router.post("/api/session/{session_id}/prompt")
    def prompt(session_id: str, body: PromptBody):
        session = _session_or_404(session_id)
        if body.model:
            session.model = body.model
        if body.stage:
            session.stage = body.stage.upper()
        if body.model or body.stage:
            crud.save_session(session)

        interrupt = deps.interrupts.setdefault(session_id, threading.Event())

        interrupt.clear()
        deps.running.add(session_id)
        deps.bus.publish({"type": "prompt.started", "session_id": session_id})
        try:
            from pathlib import Path

            import anyio

            from ...application.intent.service import IntentApplicationService
            from ...application.wave.service import WaveApplicationService
            from ...storage.project_db import ProjectDatabase

            project_dir = session.directory or deps.project_dir
            db = ProjectDatabase(project_dir)
            wave_state = db.load_wave_state() or {}
            eng_mode = wave_state.get("engineering_mode", "tdd-code")

            handled_by_wave = False
            text = ""

            # Em modo TDD, passa pelo despachante determinístico do Turing
            if eng_mode == "tdd-code" and not body.text.startswith(
                ("/model", "/theme", "/help", "/clear", "/exit")
            ):
                prd_file = Path(project_dir) / "docs" / "briefings" / "PRD.md"
                is_greenfield = not prd_file.exists()
                intent_svc = IntentApplicationService()
                action = anyio.from_thread.run(
                    intent_svc.attend,
                    body.text,
                    session.stage or "DISCUSS",
                    is_greenfield,
                )

                if action.command and action.command.startswith("/wave"):
                    handled_by_wave = True
                    deps.bus.publish(
                        {
                            "type": "turing.intent",
                            "session_id": session_id,
                            "intention": action.intention,
                            "command": action.command,
                        }
                    )

                    wave_svc = WaveApplicationService(
                        project_dir=project_dir,
                        on_event=lambda ev: deps.bus.publish({**ev, "session_id": session_id}),
                    )

                    # Desmembra comando da ONDA
                    cmd_parts = action.command.split(maxsplit=2)
                    subcmd = cmd_parts[1].lower() if len(cmd_parts) > 1 else "status"
                    subarg = cmd_parts[2] if len(cmd_parts) > 2 else ""

                    if subcmd == "start":
                        res = wave_svc.start_wave(wave_id=subarg or None)
                        text = f"ONDA iniciada com sucesso: {res.get('wave_id')}"
                    elif subcmd == "discuss":
                        topic = subarg or body.text
                        res = wave_svc.execute_with_auto_cascade("DISCUSS", input_text=topic)
                        text = (
                            "Etapa DISCUSS concluída com @meira e @grace."
                            if res.get("success")
                            else f"Aviso em DISCUSS: {res.get('error')}"
                        )
                    elif subcmd == "plan":
                        res = wave_svc.execute_with_auto_cascade("PLAN", input_text=subarg)
                        text = (
                            "Etapa PLAN concluída. Backlog e arquitetura definidos."
                            if res.get("success")
                            else f"Aviso em PLAN: {res.get('error')}"
                        )
                    elif subcmd in ("execute", "cycle"):
                        res = wave_svc.execute_with_auto_cascade("EXECUTE")
                        text = (
                            "Ciclo EXECUTE TDD concluído."
                            if res.get("success")
                            else f"Aviso em EXECUTE: {res.get('error')}"
                        )
                    elif subcmd in ("validate", "review"):
                        res = wave_svc.execute_with_auto_cascade("VALIDATE")
                        text = (
                            "Etapa VALIDATE concluída com @hoare e @unclebob."
                            if res.get("success")
                            else f"Aviso em VALIDATE: {res.get('error')}"
                        )
                    elif subcmd == "end":
                        res = wave_svc.end_wave()
                        text = f"ONDA finalizada com sucesso: {res.get('wave_id')}"
                    else:
                        st = wave_svc.get_status()
                        text = f"Status da ONDA {st.get('wave_id')}: Etapa {st.get('stage')}"

                    # Persiste mensagem do usuário e resposta no histórico
                    from ...session.models import Message as SessionMessage
                    from ...session.models import TextPart

                    user_msg = SessionMessage(session_id=session_id, role="user")
                    crud.save_message(user_msg)
                    crud.save_part(session_id, TextPart(message_id=user_msg.id, text=body.text))
                    ast_msg = SessionMessage(session_id=session_id, role="assistant")
                    crud.save_message(ast_msg)
                    crud.save_part(session_id, TextPart(message_id=ast_msg.id, text=text))

            if not handled_by_wave:
                model_to_use = body.model or session.model
                if model_to_use and model_to_use != "padrão":
                    try:
                        from ...providers.resolver import resolve_provider_adapter

                        adapter = resolve_provider_adapter(model_to_use)
                    except (RuntimeError, ValueError, OSError, KeyError) as exc:
                        logger.warning(
                            "Falha ao resolver adaptador para %s: %s; usando padrão",
                            model_to_use,
                            exc,
                        )
                        adapter = deps.adapter
                else:
                    adapter = deps.adapter

                text = run_prompt(
                    session,
                    body.text,
                    adapter=adapter,
                    registry=deps.registry,
                    permissions=ask,
                    on_event=lambda event: deps.bus.publish({**event, "session_id": session_id}),
                    abort=interrupt.is_set,
                )
        finally:
            deps.running.discard(session_id)
        deps.bus.publish({"type": "prompt.finished", "session_id": session_id, "text": text})
        return {"status": "completed", "text": text}

    @router.post("/api/session/{session_id}/wait")
    def wait(session_id: str):
        _session_or_404(session_id)
        while session_id in deps.running:
            time.sleep(0.05)
        return {"status": "idle"}

    @router.post("/api/session/{session_id}/interrupt")
    def interrupt(session_id: str):
        _session_or_404(session_id)
        deps.interrupts.setdefault(session_id, threading.Event()).set()
        return {"status": "interrupted"}

    @router.post("/api/session/{session_id}/compact")
    def compact(session_id: str, body: CompactBody):
        _session_or_404(session_id)
        message = compact_session(session_id, body.summary)
        return message.model_dump()

    @router.get("/api/session/{session_id}/event")
    def session_events(
        session_id: str,
        last_event_id: int = 0,
        last_event_id_header: int | None = Header(None, alias="Last-Event-ID"),
    ):
        from fastapi.responses import StreamingResponse

        _session_or_404(session_id)
        cursor = last_event_id_header if last_event_id_header is not None else last_event_id

        def generate():
            for entry in deps.bus.stream(last_id=cursor, session_id=session_id):
                yield sse_format(entry)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.post("/api/session/{session_id}/revert/{message_id}")
    def revert(session_id: str, message_id: str):
        _session_or_404(session_id)
        try:
            removed = revert_session(session_id, message_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"removed": removed}

    @router.post("/api/session/{session_id}/permission/reply")
    def permission_reply(session_id: str, body: PermissionReplyBody):
        _session_or_404(session_id)
        if deps.permissions is None:
            raise HTTPException(400, "servico de permissao indisponivel")
        deps.permissions.reply(body.permission, body.details, body.decision)
        return {"status": "ok"}

    @router.get("/api/session/{session_id}/question")
    def question_pending(session_id: str):
        _session_or_404(session_id)
        return {"pending": deps.questions.pending()}

    @router.post("/api/session/{session_id}/question/reply")
    def question_reply(session_id: str, body: QuestionReplyBody):
        _session_or_404(session_id)
        deps.questions.reply(body.question, body.answer)
        return {"status": "ok"}

    @router.get("/api/session/{session_id}/model")
    def get_model(session_id: str):
        return {"model": _session_or_404(session_id).model}

    @router.post("/api/session/{session_id}/model")
    def set_model(session_id: str, body: ModelBody):
        session = _session_or_404(session_id)
        session.model = body.model
        crud.save_session(session)
        return session.model_dump()

    @router.get("/api/session/{session_id}/agent")
    def get_agent(session_id: str):
        return {"agent": _session_or_404(session_id).agent}

    @router.post("/api/session/{session_id}/agent")
    def set_agent(session_id: str, body: AgentBody):
        session = _session_or_404(session_id)
        session.agent = body.agent
        crud.save_session(session)
        return session.model_dump()

    @router.get("/api/session/{session_id}/context")
    def context(session_id: str):
        _session_or_404(session_id)
        messages = crud.load_messages(session_id)
        parts = crud.load_parts(session_id)
        session = crud.load_session(session_id)
        return {
            "message_count": len(messages),
            "part_count": len(parts),
            "model": session.model,
            "agent": session.agent,
        }

    @router.get("/api/session/{session_id}/stage")
    def get_stage(session_id: str):
        return {"stage": _session_or_404(session_id).stage}

    @router.post("/api/session/{session_id}/stage")
    def set_stage(session_id: str, body: StageBody):
        session = _session_or_404(session_id)
        session.stage = body.stage.upper()
        crud.save_session(session)
        # Sincroniza também no banco de dados local do projeto (.bombe-code/state.db)
        try:
            from ...storage.project_db import ProjectDatabase

            db = ProjectDatabase(session.directory or deps.project_dir)
            saved = db.load_wave_state() or {}
            wave_id = saved.get("wave_id", "ONDA-001")
            autonomy = saved.get("autonomy_mode", "AUTO")
            eng = saved.get("engineering_mode", "tdd-code")
            db.save_wave_state(
                wave_id=wave_id,
                state=session.stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao sincronizar stage no state.db: %s", exc)

        return session.model_dump()

    return router
