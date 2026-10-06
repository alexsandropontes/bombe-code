"""Rotas de API para o ciclo de vida e orquestração da ONDA no Servidor (Wave HTTP/SSE API)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...application.wave.service import WaveApplicationService
from ..deps import ServerDeps

logger = logging.getLogger(__name__)


class WaveStartBody(BaseModel):
    wave_id: str | None = None
    autonomy_mode: str = "AUTO"
    engineering_mode: str = "tdd-code"
    force: bool = False


class WaveStageBody(BaseModel):
    stage: str
    input_text: str = ""
    context: dict[str, Any] | None = None
    auto_cascade: bool = True


def build_wave_router(deps: ServerDeps) -> APIRouter:
    router = APIRouter()

    def _get_wave_service() -> WaveApplicationService:
        def on_wave_event(event: dict[str, Any]) -> None:
            deps.bus.publish({**event, "channel": "wave"})

        return WaveApplicationService(project_dir=deps.project_dir, on_event=on_wave_event)

    @router.get("/api/wave/status")
    def wave_status():
        service = _get_wave_service()
        return service.get_status()

    @router.post("/api/wave/start")
    def wave_start(body: WaveStartBody):
        service = _get_wave_service()
        res = service.start_wave(
            wave_id=body.wave_id,
            autonomy_mode=body.autonomy_mode,
            engineering_mode=body.engineering_mode,
            force=body.force,
        )
        return res

    @router.post("/api/wave/stage")
    def wave_stage(body: WaveStageBody):
        service = _get_wave_service()
        if body.auto_cascade:
            res = service.execute_with_auto_cascade(
                stage=body.stage,
                input_text=body.input_text,
                context=body.context,
            )
        else:
            stage_norm = body.stage.strip().upper()
            if stage_norm in ("DISCOVERY", "DISCUSS"):
                res = service.discovery_stage(topic=body.input_text, context=body.context)
            elif stage_norm == "INCEPTION":
                res = service.inception_stage(context=body.context)
            elif stage_norm == "PLAN":
                res = service.plan_stage(context=body.context)
            elif stage_norm == "REFINEMENT":
                res = service.refinement_stage(context=body.context)
            elif stage_norm in ("EXECUTE", "CYCLE"):
                res = service.execute_stage(context=body.context)
            elif stage_norm in ("VALIDATE", "REVIEW"):
                res = service.validate_stage(context=body.context)
            else:
                raise HTTPException(
                    400,
                    f"Estágio desconhecido: '{body.stage}'. Use: DISCOVERY, INCEPTION, PLAN, REFINEMENT, EXECUTE, VALIDATE.",
                )
        return res

    @router.post("/api/wave/end")
    def wave_end():
        service = _get_wave_service()
        return service.end_wave()

    return router
