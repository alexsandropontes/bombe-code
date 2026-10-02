from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deps import ServerDeps


class PermissionRequestBody(BaseModel):
    permission: str
    details: str = ""


class QuestionRequestBody(BaseModel):
    question: str


def build_meta_router(deps: ServerDeps) -> APIRouter:
    router = APIRouter()
    ask = deps.ask_router()

    @router.get("/api/health")
    def health():
        return {"status": "ok"}

    @router.get("/api/model")
    def models():
        from ...providers.models_dev import get_models

        catalog = get_models()
        return [
            {"id": f"{provider}/{model_id}", "provider": provider}
            for provider, data in catalog.items()
            for model_id in (data.get("models") or {})
        ]

    @router.get("/api/provider")
    def providers():
        from ...providers.models_dev import get_models

        return [{"id": provider} for provider in get_models()]

    @router.get("/api/provider/{provider_id}")
    def provider(provider_id: str):
        from ...providers.models_dev import get_models

        catalog = get_models()
        if provider_id not in catalog:
            raise HTTPException(404, f"provider desconhecido: {provider_id}")
        return catalog[provider_id]

    @router.get("/api/agent")
    def agents():
        return [{"name": "build"}, {"name": "plan"}]

    @router.get("/api/command")
    def commands():
        return []

    @router.get("/api/skill")
    def skills():
        base = Path(deps.project_dir)
        found = []
        for directory in (base / ".bombe" / "skills", base / "skills"):
            if directory.is_dir():
                found.extend(p.stem for p in directory.rglob("*.md"))
        return [{"name": name} for name in sorted(set(found))]

    @router.get("/api/fs/list")
    def fs_list(path: str):
        target = Path(path)
        if not target.is_dir():
            raise HTTPException(404, f"diretorio nao encontrado: {path}")
        if str(ask("read", path)) == "deny":
            raise HTTPException(403, "permissao negada")
        return {"entries": sorted(p.name for p in target.iterdir())}

    @router.get("/api/fs/read")
    def fs_read(path: str):
        target = Path(path)
        if str(ask("read", path)) == "deny":
            raise HTTPException(403, "permissao negada")
        if not target.is_file():
            raise HTTPException(404, f"arquivo nao encontrado: {path}")
        return {"content": target.read_text(encoding="utf-8", errors="replace")}

    @router.get("/api/fs/find")
    def fs_find(pattern: str, path: str):
        target = Path(path)
        if not target.is_dir():
            raise HTTPException(404, f"diretorio nao encontrado: {path}")
        if str(ask("read", path)) == "deny":
            raise HTTPException(403, "permissao negada")
        matches = sorted(str(p) for p in target.rglob(pattern))
        return {"matches": matches}

    @router.post("/api/permission/request")
    def permission_request(body: PermissionRequestBody):
        return {"decision": ask(body.permission, body.details)}

    @router.get("/api/permission/saved")
    def permission_saved():
        if deps.permissions is None:
            return {"approved": []}
        return {
            "approved": [
                {
                    "permission": rule.permission,
                    "pattern": rule.pattern,
                    "action": rule.action,
                }
                for rule in deps.permissions.approved
            ]
        }

    @router.post("/api/question/request")
    def question_request(body: QuestionRequestBody):
        return {"answer": deps.questions.ask(body.question)}

    @router.get("/api/location")
    def location():
        return {"cwd": deps.project_dir}

    return router
