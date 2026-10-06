"""Serviço de Aplicação da ONDA (Wave Application Service).

Orquestra os Casos de Uso do ciclo de vida da ONDA, abstraindo a máquina de estados,
a execução sequencial de estágios com auto-cascade (modo AUTO), despacho de eventos
e garantindo independência total de interfaces (TUI, HTTP Server, CLI).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bombe_code.turing.orchestrator import WaveOrchestrator

logger = logging.getLogger(__name__)

WaveEventCallback = Callable[[dict[str, Any]], None]


class WaveApplicationService:
    """Caso de uso de alto nível para orquestração e execução da ONDA."""

    def __init__(
        self,
        project_dir: str | Path = ".",
        orchestrator: WaveOrchestrator | None = None,
        on_event: WaveEventCallback | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.orch = orchestrator or WaveOrchestrator(project_dir=str(self.project_dir))
        self.on_event = on_event

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Dispara um evento para os listeners conectados (SSE, TUI, etc.)."""
        payload = {"type": event_type, "timestamp": None, **data}
        if self.on_event:
            try:
                self.on_event(payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha no listener de evento da ONDA: %s", exc)

    def get_status(self) -> dict[str, Any]:
        """Consulta o status consolidado da ONDA ativa."""
        return self.orch.get_status()

    def start_wave(
        self,
        wave_id: str | None = None,
        autonomy_mode: str = "AUTO",
        engineering_mode: str = "tdd-code",
        force: bool = False,
    ) -> dict[str, Any]:
        """Inicia uma nova ONDA ou reinicia uma existente."""
        self._emit(
            "wave.starting",
            {
                "wave_id": wave_id,
                "autonomy_mode": autonomy_mode,
                "engineering_mode": engineering_mode,
            },
        )
        res = self.orch.start_wave(wave_id=wave_id, autonomy_mode=autonomy_mode, force=force)
        self._emit("wave.started", {"result": res})
        return res

    def end_wave(self) -> dict[str, Any]:
        """Finaliza a ONDA atual com cálculo de métricas e relatório consolidado."""
        self._emit("wave.ending", {"wave_id": self.orch.state_machine.wave_id})
        res = self.orch.end_wave()
        self._emit("wave.ended", {"result": res})
        return res

    def discovery_stage(
        self, topic: str = "", context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Executa a etapa DISCOVERY / DISCUSS (Viabilidade com @meira e alinhamento preliminar)."""
        self._emit("wave.stage_started", {"stage": "DISCOVERY", "topic": topic})
        res = self.orch.run_discuss(topic=topic, context=context)
        self._emit("wave.stage_completed", {"stage": "DISCOVERY", "result": res})
        return res

    def discuss_stage(
        self, topic: str = "", context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Alias para discovery_stage."""
        return self.discovery_stage(topic=topic, context=context)

    def inception_stage(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa INCEPTION (Lean Inception completa com @caroli, @grace, @alan e PRD Canônico)."""
        self._emit("wave.stage_started", {"stage": "INCEPTION"})
        res = self.orch.run_plan(context=context)
        self._emit("wave.stage_completed", {"stage": "INCEPTION", "result": res})
        return res

    def plan_stage(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa PLAN (Arquitetura com @ieru e modelagem com @codd)."""
        self._emit("wave.stage_started", {"stage": "PLAN"})
        res = self.orch.run_plan(context=context)
        self._emit("wave.stage_completed", {"stage": "PLAN", "result": res})
        return res

    def refinement_stage(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa REFINEMENT (PBB, Step Map, quebra de stories INVEST e DoR com @caroli)."""
        self._emit("wave.stage_started", {"stage": "REFINEMENT"})
        res = self.orch.run_plan(context=context)
        self._emit("wave.stage_completed", {"stage": "REFINEMENT", "result": res})
        return res

    def execute_stage(
        self,
        story_id: str | None = None,
        developer_agent: str = "@barbara",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executa o ciclo de implementação TDD (EXECUTE)."""
        self._emit("wave.stage_started", {"stage": "EXECUTE", "story_id": story_id})
        stories = [story_id] if story_id else None
        res = self.orch.run_execute(stories=stories)
        self._emit("wave.stage_completed", {"stage": "EXECUTE", "result": res})
        return res

    def validate_stage(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa VALIDATE (Auditoria de qualidade com @hoare e @unclebob)."""
        self._emit("wave.stage_started", {"stage": "VALIDATE"})
        res = self.orch.run_validate()
        self._emit("wave.stage_completed", {"stage": "VALIDATE", "result": res})
        return res

    def execute_with_auto_cascade(
        self,
        stage: str,
        input_text: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executa um estágio e, se a ONDA estiver em modo AUTO, encadeia autonomamente os próximos."""
        stage_norm = stage.strip().upper()
        res: dict[str, Any] = {"success": False, "stage": stage_norm}
        saved = self.orch.db.load_wave_state() or {}
        is_wave_zero = str(saved.get("wave_id", "")).upper() in (
            "ONDA-000",
            "ONDA-0",
            "WAVE-000",
            "WAVE-0",
        )

        # 1. Onda Zero: DISCOVERY (ou DISCUSS)
        if stage_norm in ("DISCOVERY", "DISCUSS"):
            res = self.discovery_stage(topic=input_text, context=context)
            if not res.get("success"):
                return res

            if saved.get("autonomy_mode") == "AUTO":
                next_stage = "INCEPTION" if is_wave_zero else "PLAN"
                self._emit(
                    "wave.cascade_advancing",
                    {"from_stage": stage_norm, "to_stage": next_stage},
                )
                return self.execute_with_auto_cascade(next_stage, context=context)

        # 2. Onda Zero: INCEPTION
        elif stage_norm == "INCEPTION":
            res = self.inception_stage(context=context)
            if not res.get("success"):
                return res

            if saved.get("autonomy_mode") == "AUTO":
                self._emit(
                    "wave.cascade_advancing",
                    {"from_stage": "INCEPTION", "to_stage": "COMPLETED"},
                )
                end_res = self.end_wave()
                res["wave_ended"] = end_res

        # 3. Onda de Entrega: PLAN
        elif stage_norm == "PLAN":
            res = self.plan_stage(context=context)
            if not res.get("success"):
                return res

            if saved.get("autonomy_mode") == "AUTO":
                next_stage = "REFINEMENT" if not is_wave_zero else "COMPLETED"
                self._emit(
                    "wave.cascade_advancing",
                    {"from_stage": "PLAN", "to_stage": next_stage},
                )
                if is_wave_zero:
                    end_res = self.end_wave()
                    res["wave_ended"] = end_res
                else:
                    return self.execute_with_auto_cascade(next_stage, context=context)

        # 4. Onda de Entrega: REFINEMENT
        elif stage_norm == "REFINEMENT":
            res = self.refinement_stage(context=context)
            if not res.get("success"):
                return res

            if saved.get("autonomy_mode") == "AUTO":
                self._emit(
                    "wave.cascade_advancing",
                    {"from_stage": "REFINEMENT", "to_stage": "EXECUTE"},
                )
                return self.execute_with_auto_cascade("EXECUTE", context=context)

        # 5. Onda de Entrega: EXECUTE / CYCLE
        elif stage_norm in ("EXECUTE", "CYCLE"):
            res = self.execute_stage(context=context)
            if not res.get("success"):
                return res

            if saved.get("autonomy_mode") == "AUTO":
                self._emit(
                    "wave.cascade_advancing",
                    {"from_stage": "EXECUTE", "to_stage": "VALIDATE"},
                )
                return self.execute_with_auto_cascade("VALIDATE", context=context)

        # 6. Onda de Entrega: VALIDATE / REVIEW
        elif stage_norm in ("VALIDATE", "REVIEW"):
            res = self.validate_stage(context=context)
            if not res.get("success"):
                return res

            if saved.get("autonomy_mode") == "AUTO":
                self._emit(
                    "wave.cascade_advancing",
                    {"from_stage": "VALIDATE", "to_stage": "COMPLETED"},
                )
                end_res = self.end_wave()
                res["wave_ended"] = end_res

        return res
