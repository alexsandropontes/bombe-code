from __future__ import annotations

import base64
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ..config.paths import get_paths
from .bus import sse_format
from .deps import ServerDeps
from .routes.meta import build_meta_router
from .routes.session import build_session_router


def _ensure_password() -> str:
    path = get_paths().state / "server-auth"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    password = secrets.token_urlsafe(24)
    path.write_text(password, encoding="utf-8")
    path.chmod(0o600)
    return password


def _check_basic_auth(authorization: str | None, password: str) -> None:
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="autenticacao basica requerida")
    try:
        decoded = base64.b64decode(authorization[6:]).decode("utf-8")
        user, _, secret = decoded.partition(":")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="credenciais invalidas") from exc
    if user != "bombe" or secret != password:
        raise HTTPException(status_code=401, detail="credenciais invalidas")


def create_app(adapter, permissions=None, project_dir: str = ".") -> FastAPI:
    app = FastAPI(
        title="bombe-code", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(127\.0\.0\.1|localhost)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    password = _ensure_password()
    deps = ServerDeps(adapter=adapter, project_dir=project_dir, permissions=permissions)

    async def auth(authorization: str | None = Header(None)) -> None:
        _check_basic_auth(authorization, password)

    auth_dep = [Depends(auth)]

    @app.get("/healthz")
    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    @app.get("/openapi.json", dependencies=auth_dep)
    def openapi_spec():
        return app.openapi()

    @app.get("/api/event", dependencies=auth_dep)
    def root_events(
        last_event_id: int = 0,
        last_event_id_header: int | None = Header(None, alias="Last-Event-ID"),
    ):
        cursor = last_event_id_header if last_event_id_header is not None else last_event_id

        def generate():
            for entry in deps.bus.stream(last_id=cursor):
                yield sse_format(entry)

        return StreamingResponse(generate(), media_type="text/event-stream")

    app.include_router(build_session_router(deps), dependencies=auth_dep)
    app.include_router(build_meta_router(deps), dependencies=auth_dep)
    return app
