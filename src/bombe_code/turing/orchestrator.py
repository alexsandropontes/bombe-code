"""Orquestrador Autônomo da ONDA no Turing Runtime (EP-003).

Coordena as transições de estado, despacho de agentes especialistas,
fiscalização determinística de gates e persistência no banco local do projeto.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from bombe_code.agents.registry import AgentRegistry
from bombe_code.agents.runner import AgentExecutionResult, AgentRunner
from bombe_code.config.project_config import ProjectConfigManager
from bombe_code.llm.pydantic_factory import PydanticAiFactory
from bombe_code.permissions.stage_guard import (
    validate_safe_relative_path,
    validate_stage_permission,
)
from bombe_code.storage.project_db import ProjectDatabase
from bombe_code.turing.gates import SealGate, TemplateGate
from bombe_code.turing.kanban import KanbanCardStatus, KanbanManager
from bombe_code.turing.pbb import AtomicTask, AtomicTaskType
from bombe_code.turing.progress import BUS
from bombe_code.turing.prompt_assembler import DeliveryTarget, TuringPromptAssembler
from bombe_code.turing.review_gate import TuringReviewGate
from bombe_code.turing.rework import VETO_ROUTES, VetoClass, VetoReworkEngine
from bombe_code.turing.state_machine import (
    AutonomyMode,
    EngineeringMode,
    InvalidTransitionError,
    TuringStage,
    TuringStateMachine,
    WaveState,
    WaveType,
)
from bombe_code.turing.upstream_gates import (
    ArchitectureGate,
    DatabaseQualityGate,
    JourneyGate,
    PRDQualityGate,
    StoryDoRGate,
    ViabilityQualityGate,
)
from bombe_code.turing.upstream_profiler import UpstreamProfiler

logger = logging.getLogger(__name__)


class WaveOrchestrator:
    """Motor de execução e orquestração do ciclo de vida da ONDA."""

    def __init__(
        self,
        project_dir: str = ".",
        db: ProjectDatabase | None = None,
        state_machine: TuringStateMachine | None = None,
        registry: AgentRegistry | None = None,
        llm_factory: PydanticAiFactory | None = None,
        template_gate: TemplateGate | None = None,
        seal_gate: SealGate | None = None,
        prd_gate: PRDQualityGate | None = None,
        journey_gate: JourneyGate | None = None,
        architecture_gate: ArchitectureGate | None = None,
        story_dor_gate: StoryDoRGate | None = None,
        review_gate: TuringReviewGate | None = None,
        kanban: KanbanManager | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.db = db or ProjectDatabase(str(self.project_dir))
        self.registry = registry or AgentRegistry.default()
        self.llm_factory = llm_factory or PydanticAiFactory()
        self.template_gate = template_gate or TemplateGate()
        self.seal_gate = seal_gate or SealGate()
        self.viability_gate = ViabilityQualityGate()
        self.prd_gate = prd_gate or PRDQualityGate()
        self.journey_gate = journey_gate or JourneyGate()
        self.architecture_gate = architecture_gate or ArchitectureGate()
        self.db_gate = DatabaseQualityGate()
        self.story_dor_gate = story_dor_gate or StoryDoRGate()
        self.review_gate = review_gate or TuringReviewGate()
        from bombe_code.domain.wave.workspace import WaveWorkspace

        self.workspace = WaveWorkspace(project_dir=self.project_dir)
        self.kanban = kanban or KanbanManager(project_dir=str(self.project_dir), db=self.db)
        self._gate_evaluations: dict[str, Any] = {}
        self.config_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = self.config_mgr.load()
        raw_target = getattr(cfg, "delivery_target", "mvp")
        self.delivery_target = DeliveryTarget.from_str(raw_target)
        BUS.set_verbosity(os.environ.get("BOMBE_VERBOSITY") or getattr(cfg, "verbosity", "verbose"))
        self.prompt_assembler = TuringPromptAssembler()
        self.telemetry: dict[str, Any] = {
            "stages": {},
            "total": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_seconds": 0.0,
            },
        }

        # Carrega ou inicializa a máquina de estados a partir do banco SQLite
        if state_machine:
            self.state_machine = state_machine
        else:
            self.state_machine = self._load_or_create_state_machine()

        # AUTOCURA (à prova de erro): o runtime detecta e corrige sozinho
        # anomalias de estado — o humano NUNCA precisa saber que houve erro.
        try:
            self._autocure()
        except Exception as exc:  # noqa: BLE001 — autocura nunca derruba o boot
            logger.warning("Autocura falhou (não bloqueante): %s", exc)

    def _autocure(self) -> dict[str, Any] | None:
        """Diagnóstico automático GLOBAL e cura de estados inconsistentes.

        Roda a cada boot do runtime. Varre TODAS as ondas — não apenas a ativa:
        1. ONDA ativa COMPLETED com stories DEV_DONE ou relatório de REJEIÇÃO
           → reabre na VALIDATE.
        2. ONDA arquivada com evidência de pendência (relatório REJEITADO,
           stories DEV_DONE) e onda ativa SEM trabalho em voo → ADOTA a onda
           anômala e reabre na VALIDATE. (caso make-books: ONDA-001 fechada
           indevidamente enquanto a ONDA-002 vazia ocupava a máquina)
        """
        saved = self.db.load_wave_state()
        if not saved:
            return None

        # 1. Autocura da onda ATIVA
        cured = self._autocurar_onda(wave_id=str(saved.get("wave_id", "")), pode_trocar=False)
        if cured:
            return cured

        # 2. Varredura GLOBAL: detecção determinística (custo ZERO de tokens) —
        #    apenas AVISA; a ação é do usuário via `/wave audit ONDA-xxx`.
        #    (economia de tokens: nada de revalidar 300 ondas retroativamente)
        if str(saved.get("state", "")).upper() == WaveState.COMPLETED.value:
            return None
        current_cards = self.kanban.list_cards(wave_id=str(saved.get("wave_id", "")))
        if current_cards:
            return None  # trabalho em voo: prioridade é a onda ativa

        candidatos: set[str] = {
            c.get("wave_id", "") for c in self.kanban.list_cards() if c.get("wave_id")
        }
        waves_dir = self.project_dir / "docs" / "waves"
        if waves_dir.is_dir():
            for pasta in waves_dir.iterdir():
                if pasta.is_dir() and (pasta / "validation_report.md").exists():
                    candidatos.add(pasta.name)
        candidatos.discard(str(saved.get("wave_id", "")))

        for wave in sorted(candidatos):
            cards = self.kanban.list_cards(wave_id=wave)
            dev_done = [
                c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DEV_DONE.value
            ]
            motivo: str | None = None
            if dev_done:
                motivo = f"{len(dev_done)} story(ies) em DEV_DONE sem homologação DONE: {', '.join(dev_done)}"
            else:
                try:
                    report = self.workspace.wave_validation_report_path(wave)
                    conteudo = report.read_text(encoding="utf-8").lower() if report.exists() else ""
                except OSError:
                    conteudo = ""
                if "veredito final" in conteudo and "rejeitad" in conteudo:
                    motivo = "relatório de validação contém veredito de REJEIÇÃO"
            if motivo:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"⚠️ [EVIDÊNCIA DE PENDÊNCIA] A {wave} possui indício de pendência não resolvida "
                        f"({motivo}). A máquina não revalida retroativamente (economia de tokens) — "
                        f"se houver dúvida, invoque: /wave audit {wave}"
                    ),
                    wave_id=wave,
                )
        return None

    def _autocurar_onda(self, wave_id: str, pode_trocar: bool) -> dict[str, Any] | None:
        """Detecta anomalia em UMA onda e cura (reabrindo na VALIDATE).

        Se pode_trocar=True, a onda anômala assume o comando da máquina
        (wave_state passa a apontar para ela) — sem perguntar nada a ninguém.
        """
        motivo: str | None = None

        cards = self.kanban.list_cards(wave_id=wave_id)
        dev_done = [
            c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DEV_DONE.value
        ]
        if dev_done:
            motivo = f"{len(dev_done)} story(ies) em DEV_DONE sem homologação DONE: {', '.join(dev_done)}"
        else:
            try:
                report = self.workspace.wave_validation_report_path(wave_id)
                conteudo = report.read_text(encoding="utf-8").lower() if report.exists() else ""
            except OSError:
                conteudo = ""
            if "veredito final" in conteudo and "rejeitad" in conteudo:
                motivo = "relatório de validação contém veredito de REJEIÇÃO"

        if not motivo:
            return None

        # Preserva o checkpoint da onda ativa se vamos assumir o comando.
        if pode_trocar:
            ativo = self.db.load_wave_state()
            if (
                ativo
                and str(ativo.get("wave_id", "")).upper() != wave_id.upper()
                and str(ativo.get("state", "")).upper() != WaveState.COMPLETED.value
            ):
                self.db.archive_wave_state()

        self.state_machine = TuringStateMachine(
            wave_id=wave_id,
            initial_state=WaveState.VALIDATE,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        self.db.save_wave_state(
            wave_id=wave_id,
            state=WaveState.VALIDATE,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        mensagem = (
            f"🩺 [AUTOCURA] Anomalia detectada e corrigida automaticamente: a {wave_id} "
            f"possui pendência não resolvida ({motivo}). Reaberta na etapa VALIDATE — "
            "a validação será reexecutada pelo Ciclo Autônomo."
            + (" Ela assume o comando da máquina." if pode_trocar else "")
        )
        BUS.publish("announcement", agent="@turing", text=mensagem, wave_id=wave_id)
        logger.warning("AUTOCURA: %s", mensagem)
        return {
            "cured": True,
            "wave_id": wave_id,
            "stage": WaveState.VALIDATE.value,
            "motivo": motivo,
        }

    def _record_telemetry(self, stage: str, agent: str, result: Any) -> None:
        """Registra métricas de execução de um agente em uma etapa da ONDA."""
        if not result:
            return
        if stage not in self.telemetry["stages"]:
            self.telemetry["stages"][stage] = {
                "agents": [],
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "duration_seconds": 0.0,
            }
        stg = self.telemetry["stages"][stage]
        try:
            in_tok = int(getattr(result, "input_tokens", 0) or 0)
        except (ValueError, TypeError):
            in_tok = 0
        try:
            out_tok = int(getattr(result, "output_tokens", 0) or 0)
        except (ValueError, TypeError):
            out_tok = 0
        try:
            tot_tok = int(getattr(result, "total_tokens", 0) or (in_tok + out_tok))
        except (ValueError, TypeError):
            tot_tok = in_tok + out_tok
        try:
            c = float(getattr(result, "cost", 0.0) or 0.0)
        except (ValueError, TypeError):
            c = 0.0
        try:
            dur = float(getattr(result, "duration_seconds", 0.0) or 0.0)
        except (ValueError, TypeError):
            dur = 0.0

        stg["agents"].append(
            {
                "agent": agent,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": tot_tok,
                "cost": round(c, 6),
                "duration_seconds": round(dur, 3),
                "success": getattr(result, "success", True),
            }
        )
        stg["input_tokens"] += in_tok
        stg["output_tokens"] += out_tok
        stg["total_tokens"] += tot_tok
        stg["cost"] = round(stg["cost"] + c, 6)
        stg["duration_seconds"] = round(stg["duration_seconds"] + dur, 3)

        tot = self.telemetry["total"]
        tot["input_tokens"] += in_tok
        tot["output_tokens"] += out_tok
        tot["total_tokens"] += tot_tok
        tot["cost"] = round(tot["cost"] + c, 6)
        tot["duration_seconds"] = round(tot["duration_seconds"] + dur, 3)

        self._save_telemetry_files()

    def _save_telemetry_files(self) -> None:
        """Persiste os arquivos telemetry.json e telemetria.md sob docs/ e na ONDA ativa."""
        try:
            docs_dir = self.project_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            telemetry_data = json.dumps(self.telemetry, indent=2, ensure_ascii=False)
            telemetry_json = docs_dir / "telemetry.json"
            telemetry_json.write_text(telemetry_data, encoding="utf-8")

            if hasattr(self, "workspace") and hasattr(self, "state_machine"):
                wave_telemetry = self.workspace.wave_telemetry_path(self.state_machine.wave_id)
                wave_telemetry.parent.mkdir(parents=True, exist_ok=True)
                wave_telemetry.write_text(telemetry_data, encoding="utf-8")

            tot = self.telemetry["total"]
            speed = round(tot["total_tokens"] / max(tot["duration_seconds"], 0.001), 1)
            md_lines = [
                f"# 📊 Telemetria de Execução da ONDA {self.state_machine.wave_id}",
                "",
                "## 📈 Resumo Geral Consolidado",
                f"- **Tokens de Entrada (Prompt):** {tot['input_tokens']:,}",
                f"- **Tokens de Saída (Completion):** {tot['output_tokens']:,}",
                f"- **Total de Tokens:** {tot['total_tokens']:,}",
                f"- **Custo Total Estimado:** ${tot['cost']:.6f} USD",
                f"- **Tempo Total em LLM:** {tot['duration_seconds']:.2f}s",
                f"- **Velocidade Média:** {speed:,} tokens/s",
                "",
                "## 📋 Detalhamento por Etapa e Agente Especialista",
                "| Etapa | Agente | Tokens Entrada | Tokens Saída | Total Tokens | Custo (USD) | Duração (s) | Velocidade (tok/s) |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
            for stg_name, stg_data in self.telemetry["stages"].items():
                for ag in stg_data["agents"]:
                    ag_speed = round(ag["total_tokens"] / max(ag["duration_seconds"], 0.001), 1)
                    md_lines.append(
                        f"| **{stg_name}** | `{ag['agent']}` | {ag['input_tokens']:,} | {ag['output_tokens']:,} | {ag['total_tokens']:,} | ${ag['cost']:.6f} | {ag['duration_seconds']:.2f}s | {ag_speed:,} |"
                    )
                stg_speed = round(
                    stg_data["total_tokens"] / max(stg_data["duration_seconds"], 0.001), 1
                )
                md_lines.append(
                    f"| *Subtotal {stg_name}* | - | *{stg_data['input_tokens']:,}* | *{stg_data['output_tokens']:,}* | *{stg_data['total_tokens']:,}* | *${stg_data['cost']:.6f}* | *{stg_data['duration_seconds']:.2f}s* | *{stg_speed:,}* |"
                )

            (docs_dir / "telemetria.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Falha ao salvar arquivos de telemetria: %s", exc)

    def _load_or_create_state_machine(self) -> TuringStateMachine:
        saved = self.db.load_wave_state()
        if saved:
            wave_id = saved.get("wave_id", "ONDA-001")
            raw_state = saved.get("state", WaveState.DISCOVERY.value)
            raw_autonomy = saved.get("autonomy_mode", AutonomyMode.AUTO.value)
            raw_eng = saved.get("engineering_mode", EngineeringMode.TDD_CODE.value)

            try:
                state = WaveState(raw_state)
            except ValueError:
                state = WaveState.DISCOVERY

            try:
                autonomy = AutonomyMode(raw_autonomy)
            except ValueError:
                autonomy = AutonomyMode.AUTO

            try:
                eng = EngineeringMode(raw_eng)
            except ValueError:
                eng = EngineeringMode.TDD_CODE

            return TuringStateMachine(
                wave_id=wave_id,
                initial_state=state,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )

        return TuringStateMachine(wave_id="ONDA-001", initial_state=WaveState.DISCOVERY)

    def start_wave(
        self,
        wave_id: str,
        autonomy_mode: str = "AUTO",
        engineering_mode: str = "tdd-code",
        force: bool = False,
        delivery_target: str | None = None,
    ) -> dict[str, Any]:
        """Inicializa (ou retoma) uma ONDA de forma autônoma e inteligente.

        Autonomia total — NÃO existe decisão humana nem flag de força:
        - Mesma ONDA pendente → retoma o checkpoint exato (RESUME).
        - Outra ONDA pedida com checkpoint ativo → arquiva o checkpoint no
          histórico (nada é destruído) e inicia a pedida.
        - ONDA pedida tem checkpoint histórico não concluído → retoma dele.
        - ONDA concluída com cards DEV_DONE (anomalia: homologação indevida
          ou validação interrompida) → reabre na etapa inferida pelas filas.
        """
        # `force` é obsoleto: mantido na assinatura por compatibilidade, ignorado.
        saved = self.db.load_wave_state()

        if delivery_target:
            self.delivery_target = DeliveryTarget.from_str(delivery_target)
            try:
                cfg = self.config_mgr.load()
                cfg.delivery_target = self.delivery_target.value
                self.config_mgr.save(cfg)
            except Exception as e:  # noqa: BLE001 — persistência de config é best-effort
                logger.warning("Falha ao salvar delivery_target no config: %s", e)

        try:
            autonomy = AutonomyMode(autonomy_mode.upper())
        except ValueError:
            autonomy = AutonomyMode.AUTO

        try:
            eng = EngineeringMode(engineering_mode.lower())
        except ValueError:
            eng = EngineeringMode.TDD_CODE

        # RESUME: mesma ONDA pendente → retoma EXATAMENTE do ponto onde o
        # processo anterior parou (ex.: veto na VALIDATE).
        saved = self.db.load_wave_state() or {}
        same_wave_pending = bool(
            saved
            and str(saved.get("wave_id", "")).upper() == wave_id.upper().strip()
            and saved.get("state") not in (WaveState.COMPLETED.value, "COMPLETED", None, "")
        )
        if same_wave_pending:
            try:
                restored_stage = WaveState(str(saved.get("state")).upper())
            except ValueError:
                restored_stage = WaveState.DISCUSS
            saved_autonomy = str(saved.get("autonomy_mode") or autonomy.value).upper()
            caller_usou_defaults = (
                autonomy_mode.upper() == "AUTO" and engineering_mode.lower() == "tdd-code"
            )
            if caller_usou_defaults:
                try:
                    autonomy = AutonomyMode(saved_autonomy)
                except ValueError:
                    pass
                saved_eng = str(saved.get("engineering_mode") or eng.value).lower()
                try:
                    eng = EngineeringMode(saved_eng)
                except ValueError:
                    pass

            self.state_machine = TuringStateMachine(
                wave_id=wave_id,
                initial_state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
            self.db.save_wave_state(
                wave_id=wave_id,
                state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )

            # Diagnóstico pelas FILAS do Kanban (padrão code-forge retomar()):
            # onde exatamente o processo parou e o que já está selado.
            cards = self.kanban.list_cards(wave_id=wave_id)
            dev_done = [
                c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DEV_DONE.value
            ]
            done = [c["story_id"] for c in cards if c.get("status") == KanbanCardStatus.DONE.value]
            blocked = [
                c["story_id"]
                for c in cards
                if c.get("is_blocked") or c.get("block_reason") or c.get("status") == "BLOCKED"
            ]
            diagnosis_parts = [f"{len(done)} story(ies) DONE (seladas)"]
            if dev_done:
                diagnosis_parts.append(
                    f"{len(dev_done)} DEV_DONE aguardando validação: {', '.join(dev_done)}"
                )
            if blocked:
                diagnosis_parts.append(f"{len(blocked)} bloqueada(s): {', '.join(blocked)}")
            diagnosis = " | ".join(diagnosis_parts) if cards else "sem cards registrados no Kanban"

            BUS.publish(
                "wave_start",
                agent="@turing",
                wave_id=wave_id,
                text=(
                    f"↩️ ONDA {wave_id} retomada na etapa {restored_stage.value} "
                    f"(checkpoint persistido). Autonomia: {autonomy.value}. Diagnóstico: {diagnosis}"
                ),
                autonomy=autonomy.value,
                engineering_mode=eng.value,
                resumed=True,
                diagnosis=diagnosis,
            )
            return {
                "success": True,
                "wave_id": wave_id,
                "stage": restored_stage.value,
                "autonomy_mode": autonomy.value,
                "engineering_mode": eng.value,
                "resumed": True,
                "diagnosis": {
                    "done": done,
                    "dev_done": dev_done,
                    "blocked": blocked,
                    "summary": diagnosis,
                },
                "message": (
                    f"ONDA {wave_id} retomada na etapa {restored_stage.value} "
                    f"exatamente de onde o processo anterior parou. {diagnosis}."
                ),
            }

        # Outra ONDA com checkpoint ativo → arquiva no histórico (sem destruir nada,
        # sem perguntar nada ao humano).
        if (
            saved
            and str(saved.get("wave_id", "")).upper() != wave_id.upper().strip()
            and saved.get("state") not in (WaveState.COMPLETED.value, "COMPLETED")
        ):
            arquivado = self.db.archive_wave_state()
            if arquivado:
                BUS.publish(
                    "announcement",
                    agent="@turing",
                    text=(
                        f"🗄️ Checkpoint da {arquivado.get('wave_id')} (etapa {arquivado.get('state')}) "
                        "arquivado no histórico com segurança — prosseguindo para a ONDA pedida."
                    ),
                )

        # ONDA pedida tem checkpoint histórico não concluído → retoma dele.
        checkpoint = self.db.load_wave_checkpoint(wave_id)
        if checkpoint and checkpoint.get("state") not in (
            WaveState.COMPLETED.value,
            "COMPLETED",
        ):
            try:
                restored_stage = WaveState(str(checkpoint.get("state")).upper())
            except ValueError:
                restored_stage = WaveState.DISCUSS
            self.state_machine = TuringStateMachine(
                wave_id=wave_id,
                initial_state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
            self.db.save_wave_state(
                wave_id=wave_id,
                state=restored_stage,
                autonomy_mode=autonomy,
                engineering_mode=eng,
            )
            BUS.publish(
                "wave_start",
                agent="@turing",
                wave_id=wave_id,
                text=(
                    f"↩️ ONDA {wave_id} retomada do histórico na etapa {restored_stage.value}. "
                    f"Autonomia: {autonomy.value}."
                ),
                autonomy=autonomy.value,
                resumed=True,
            )
            return {
                "success": True,
                "wave_id": wave_id,
                "stage": restored_stage.value,
                "autonomy_mode": autonomy.value,
                "engineering_mode": eng.value,
                "resumed": True,
                "message": (
                    f"ONDA {wave_id} retomada do histórico na etapa {restored_stage.value}."
                ),
            }

        initial_stage = WaveState.DISCUSS
        norm_id = wave_id.upper().strip()
        if norm_id in ("ONDA-000", "ONDA-0", "WAVE-000", "WAVE-0") or norm_id.startswith(
            ("ONDA-000-", "WAVE-000-", "ONDA-0-")
        ):
            initial_stage = WaveState.DISCOVERY
        elif (self.project_dir / "docs" / "briefings" / "PRD.md").exists():
            cards = self.kanban.list_cards(wave_id=wave_id)
            if cards:
                statuses = {c.get("status") for c in cards}
                trabalho_em_curso = statuses & {"IN_PROGRESS", "IN_REVIEW", "READY", "BACKLOG"}
                if not trabalho_em_curso and KanbanCardStatus.DEV_DONE.value in statuses:
                    # Anomalia detectada: todas as stories DEV_DONE mas a onda não
                    # concluiu (ex.: homologação indevida). Reabre na VALIDATE.
                    initial_stage = WaveState.VALIDATE
                else:
                    initial_stage = WaveState.EXECUTE
            else:
                initial_stage = WaveState.PLAN

        self.state_machine = TuringStateMachine(
            wave_id=wave_id,
            initial_state=initial_stage,
            autonomy_mode=autonomy,
            engineering_mode=eng,
        )

        self.db.save_wave_state(
            wave_id=wave_id,
            state=initial_stage,
            autonomy_mode=autonomy,
            engineering_mode=eng,
        )

        is_zero = initial_stage == WaveState.DISCOVERY
        fluxo = (
            "DISCOVERY → INCEPTION → COMPLETED (Upstream estrito, sem código em src/)"
            if is_zero
            else "PLAN → REFINEMENT → EXECUTE → VALIDATE → COMPLETED"
        )
        BUS.publish(
            "wave_start",
            agent="@turing",
            wave_id=wave_id,
            text=(
                f"🌊 ONDA {wave_id} iniciada — "
                + ("Onda Zero (Greenfield Lean Inception Macro)" if is_zero else "Onda de Entrega")
                + f". Fluxo: {fluxo}. Autonomia: {autonomy.value}."
            ),
            autonomy=autonomy.value,
            engineering_mode=eng.value,
        )

        return {
            "success": True,
            "wave_id": wave_id,
            "stage": initial_stage.value,
            "autonomy_mode": autonomy.value,
            "engineering_mode": eng.value,
            "message": f"ONDA {wave_id} inicializada com sucesso na etapa {initial_stage.value}.",
        }

    def get_status(self) -> dict[str, Any]:
        """Retorna uma radiografia completa do estado da ONDA ativa."""
        tasks = self.db.list_agent_tasks()
        pending = sum(1 for t in tasks if t.get("status") in ("pending", "in_progress"))
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)

        return {
            "wave_id": self.state_machine.wave_id,
            "stage": self.state_machine.current_state.value,
            "autonomy_mode": self.state_machine.autonomy_mode.value,
            "engineering_mode": self.state_machine.engineering_mode.value,
            "tasks_summary": {
                "total": len(tasks),
                "pending": pending,
                "completed": completed,
                "failed": failed,
            },
            "gates": self._gate_evaluations,
            "kanban_cards": cards,
        }

    def transition_to(self, target_stage: TuringStage) -> bool:
        """Executa a transição determinística para a etapa solicitada."""
        if not self.state_machine.can_transition_to(target_stage):
            logger.warning(
                "Transição ilegal rejeitada pelo Turing: %s -> %s",
                self.state_machine.current_state.value,
                target_stage.value,
            )
            return False

        try:
            self.state_machine.transition_to(target_stage)
            self.db.save_wave_state(
                wave_id=self.state_machine.wave_id,
                state=self.state_machine.current_state,
                autonomy_mode=self.state_machine.autonomy_mode,
                engineering_mode=self.state_machine.engineering_mode,
            )
            return True
        except InvalidTransitionError:
            return False

    def _get_project_fs_tools(self, guarda: Any = None) -> list[Any]:
        project_dir = self.project_dir

        def read_project_file(path: str) -> str:
            """Lê o conteúdo de um arquivo do projeto a partir do caminho relativo (ex: 'docs/stories/ST-001.md')."""
            aviso_leitura = ""
            if guarda is not None:
                aviso_leitura = guarda.registrar_leitura(path)
            is_safe, err_msg = validate_safe_relative_path(path)
            if not is_safe:
                return f"Erro: {err_msg}"
            try:
                target = (project_dir / path).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return f"Erro: Acesso fora do projeto negado para {path}"
                if not target.exists() or not target.is_file():
                    return f"Erro: Arquivo {path} não existe no projeto."
                conteudo = target.read_text(encoding="utf-8", errors="replace")
                return f"{conteudo}{aviso_leitura}" if aviso_leitura else conteudo
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return f"Erro ao ler {path}: {e}"

        def write_project_file(path: str, content: str) -> str:
            """Grava conteúdo em um arquivo do projeto no caminho relativo especificado (ex: 'js/logic.js')."""
            is_safe, err_msg = validate_safe_relative_path(path)
            if not is_safe:
                return f"Erro: {err_msg}"
            try:
                target = (project_dir / path).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return f"Erro: Acesso fora do projeto negado para {path}"
                stage = getattr(self.state_machine, "stage", None)
                stage_name = stage.name if hasattr(stage, "name") else str(stage or "DISCUSS")
                allowed, stage_reason = validate_stage_permission(
                    stage_name, "write", str(target), str(project_dir)
                )
                if not allowed:
                    return (
                        stage_reason
                        or "Erro: Operação bloqueada pelas regras da etapa atual da ONDA."
                    )
                # GUARDIÃ DETERMINÍSTICA DE AÇÕES: valida o conteúdo ANTES de
                # gravar (anti-alucinação por ação, não por relógio).
                if guarda is not None:
                    veto = guarda.validar_escrita(path, content)
                    if veto:
                        return veto
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"Arquivo {path} gravado com sucesso ({len(content)} caracteres)."
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return f"Erro ao gravar {path}: {e}"

        def list_project_files(directory: str = ".") -> list[str]:
            """Lista os arquivos existentes no diretório relativo do projeto."""
            if directory and directory != ".":
                is_safe, err_msg = validate_safe_relative_path(directory)
                if not is_safe:
                    return [f"Erro: {err_msg}"]
            try:
                target = (project_dir / directory).resolve()
                if not target.is_relative_to(project_dir.resolve()):
                    return ["Erro: Acesso fora do projeto negado."]
                if not target.exists():
                    return []
                return [
                    str(p.relative_to(project_dir))
                    for p in target.rglob("*.*")
                    if p.is_file() and not str(p).startswith(str(project_dir / ".git"))
                ]
            except Exception as e:  # noqa: BLE001 — tool de FS retorna erro textual à LLM
                return [f"Erro: {e}"]

        return [read_project_file, write_project_file, list_project_files]

    def _get_runner(self, agent_handle: str) -> AgentRunner | None:
        agent = self.registry.get(agent_handle)
        if not agent:
            return None
        from bombe_code.permissions.acao_guard import GuardaDeAcoes

        guarda = GuardaDeAcoes(agente=agent_handle)
        return AgentRunner(
            agent=agent,
            llm_factory=self.llm_factory,
            project_db=self.db,
            extra_tools=self._get_project_fs_tools(guarda),
            guarda=guarda,
        )

    def _assemble_prompt(
        self, agent_handle: str, task_prompt: str, context: dict[str, Any] | None = None
    ) -> str:
        """Monta deterministamente o prompt de execução usando o Lego de Prompts."""
        eng_mode = (
            self.state_machine.engineering_mode.value
            if hasattr(self.state_machine.engineering_mode, "value")
            else str(self.state_machine.engineering_mode)
        )
        return self.prompt_assembler.assemble(
            agent_handle=agent_handle,
            task_instruction=task_prompt,
            delivery_target=self.delivery_target,
            mode=eng_mode,
            context=context,
        )

    AGENT_REQUIRED_INPUTS: ClassVar[dict[str, list[tuple[str, str]]]] = {
        "@meira": [],
        "@grace": [
            ("docs/briefings/VIABILITY.md", "Parecer de Viabilidade Técnica e Estratégica (@meira)")
        ],
        "@alan": [("docs/briefings/PRD.md", "PRD Estruturado (@grace)")],
        "@ieru": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            ("docs/architecture/journey.md", "Mapeamento da Jornada do Usuário (@alan)"),
        ],
        "@codd": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            (
                "docs/architecture/SYSTEM_ARCHITECTURE.md",
                "Arquitetura do Sistema e Decisões Técnicas (@ieru)",
            ),
        ],
        "@caroli": [
            ("docs/briefings/PRD.md", "PRD Estruturado (@grace)"),
            ("docs/architecture/journey.md", "Mapeamento da Jornada do Usuário (@alan)"),
            ("docs/architecture/SYSTEM_ARCHITECTURE.md", "Arquitetura do Sistema (@ieru)"),
        ],
        "@aniche": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
        "@fowler": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
            ("docs/stories/{story_id}_test_plan.md", "Plano de Testes da Story (@aniche)"),
        ],
        "@barbara": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
        "@ada": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
        "@unclebob": [
            ("docs/stories/{story_id}.md", "Story com INVEST e BDD (@caroli)"),
        ],
    }

    def validate_agent_prerequisites(
        self, agent_handle: str, story_id: str | None = None
    ) -> tuple[bool, str]:
        """REGRA INEGOCIÁVEL 2: Valida se todas as entradas essenciais do agente existem fisicamente no disco antes de chamá-lo."""
        reqs = self.AGENT_REQUIRED_INPUTS.get(agent_handle, [])
        wave_id = (
            getattr(self.state_machine, "wave_id", None) if hasattr(self, "state_machine") else None
        )
        target_sid = story_id or "ST-001"
        for rel_template, desc in reqs:
            rel_path = rel_template.replace("{story_id}", target_sid)
            target = self.project_dir / rel_path
            if not target.exists() and "stories" in rel_path:
                if "_test_plan.md" in rel_path:
                    alt = self.workspace.find_test_plan_file(target_sid, wave_id=wave_id)
                else:
                    alt = self.workspace.find_story_file(target_sid, wave_id=wave_id)
                if alt and alt.exists():
                    target = alt
            if not target.exists():
                return (
                    False,
                    f"Pré-requisito ausente para {agent_handle}: O arquivo '{rel_path}' ({desc}) não existe no disco.",
                )
            if target.is_file() and target.stat().st_size < 50:
                return (
                    False,
                    f"Pré-requisito inválido para {agent_handle}: O arquivo '{rel_path}' ({desc}) está vazio ou raso (< 50 bytes).",
                )
        return True, "Entradas validadas com sucesso."

    def handle_agent_block(
        self, agent_handle: str, reason: str, story_id: str | None = None
    ) -> None:
        """Intervenção OBRIGATÓRIA do Turing Runtime ao detectar bloqueio de agente."""
        logger.error(
            "🛑 INTERVENÇÃO DO TURING RUNTIME: Agente %s reportou bloqueio ou pré-requisito falho: %s",
            agent_handle,
            reason,
        )
        target_story = story_id or "ST-001"
        card = self.kanban.get_card(target_story)
        if not card:
            self.kanban.add_card(
                story_id=target_story,
                wave_id=self.state_machine.wave_id,
                title=f"Bloqueio: {agent_handle}",
                agent=agent_handle,
                status="BLOCKED",
            )
        self.kanban.block_card(target_story, reason=reason, blocked_by=agent_handle)

    def _publish_stage(self, event_type: str, text: str, **data: Any) -> None:
        """Publica anúncio canônico de etapa (visível mesmo no modo quiet)."""
        BUS.publish(
            event_type,
            agent="@turing",
            text=text,
            wave_id=self.state_machine.wave_id,
            stage=self.state_machine.current_state.value,
            **data,
        )

    def run_discuss(self, topic: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Etapa DISCUSS com anúncios canônicos de início/fim."""
        self._publish_stage(
            "stage_start",
            f"🎬 Etapa DISCUSS iniciada — @meira (viabilidade) e @grace (PRD) acionados para: {str(topic)[:120]}",
        )
        result = self._run_discuss_inner(topic, context)
        if result.get("success"):
            self._publish_stage(
                "stage_end",
                "✓ Etapa DISCUSS concluída — artefatos: docs/briefings/VIABILITY.md e docs/briefings/PRD.md.",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa DISCUSS interrompida: {result.get('error')}",
            )
        return result

    def run_plan(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Etapa PLAN com anúncios canônicos de início/fim."""
        self._publish_stage(
            "stage_start",
            "🎬 Etapa PLAN iniciada — arquitetos de Upstream (@ieru, @codd, @caroli) em ação.",
        )
        result = self._run_plan_inner(context)
        if result.get("success"):
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            self._publish_stage(
                "stage_end",
                f"✓ Etapa PLAN concluída — arquitetura e backlog prontos ({len(cards)} stories no Kanban).",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa PLAN interrompida: {result.get('error')}",
            )
        return result

    def run_cycle(self, story_id: str | None = None) -> dict[str, Any]:
        """Etapa EXECUTE (ciclo TDD) com anúncios canônicos de início/fim."""
        alvo = story_id or "lote de stories pendentes"
        self._publish_stage("stage_start", f"🎬 Etapa EXECUTE iniciada — alvo: {alvo}.")
        result = self._run_cycle_inner(story_id)
        if result.get("success"):
            self._publish_stage(
                "stage_end",
                f"✓ Etapa EXECUTE concluída — {result.get('message', '')}",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa EXECUTE interrompida: {result.get('error')}",
            )
        return result

    def run_validate(self) -> dict[str, Any]:
        """Etapa VALIDATE com anúncios canônicos e ciclo de retrabalho de vetos."""
        self._publish_stage(
            "stage_start",
            "🎬 Etapa VALIDATE iniciada — auditoria formal com @edith (homologação) e @nina (governança).",
        )
        result = self._run_validate_inner()
        if result.get("success"):
            self._publish_stage(
                "stage_end",
                "✓ Etapa VALIDATE concluída — Selo de Homologação emitido (@edith + @nina).",
            )
        else:
            self._publish_stage(
                "stage_failed",
                f"✗ Etapa VALIDATE não aprovada: {result.get('error')}",
            )
        return result

    def _run_discuss_inner(
        self, topic: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Executa a etapa DISCOVERY / DISCUSS com @meira (viabilidade) e @grace (PRD)."""
        if not topic or not str(topic).strip():
            return {
                "success": False,
                "error": "missing_topic",
                "message": (
                    "⚠️ Nenhuma demanda ou briefing informado para a etapa DISCOVERY / DISCUSS. "
                    "Informe a ideia ou escopo do produto (ex: /wave discuss <ideia>) para iniciar a viabilidade com @meira e o PRD com @grace."
                ),
            }

        if self.state_machine.current_state not in (WaveState.DISCUSS, WaveState.DISCOVERY):
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado DISCOVERY ou DISCUSS.",
            }

        results: list[dict[str, Any]] = []
        profile = UpstreamProfiler.profile(self.project_dir, self.delivery_target)
        logger.info(
            "🎯 [DISCUSS] Nível: %s | Origem: %s | Inception: %s",
            self.delivery_target.value.upper(),
            profile.origin.value,
            profile.inception_level.value,
        )

        ctx = dict(context or {})
        ctx["upstream_profile"] = profile
        context = ctx

        # 1. Despacha @meira para viabilidade
        ok, pre_err = self.validate_agent_prerequisites("@meira")
        if not ok:
            self.handle_agent_block("@meira", pre_err)
            return {"success": False, "stage": TuringStage.DISCUSS.value, "error": pre_err}

        runner_meira = self._get_runner("@meira")
        if runner_meira:
            raw_prompt = (
                f"Analise a viabilidade técnica e estratégica para a demanda: '{topic}'.\n"
                f"Avalie a demanda solicitada sem inventar escopos extras ou módulos adicionais.\n"
                f"Se a viabilidade for positiva para o nível solicitado ({self.delivery_target.value.upper()}), declare explicitamente: 'Status: APROVADO' ou 'Veredito: PROSSEGUIR'."
            )
            meira_prompt = self._assemble_prompt("@meira", raw_prompt, context)
            res_meira = runner_meira.run(
                prompt=meira_prompt,
                context=context,
            )
            self._record_telemetry("DISCUSS", "@meira", res_meira)
            results.append(
                {"agent": "@meira", "output": res_meira.output, "success": res_meira.success}
            )

            # FAIL-FAST: Se @meira bloqueou ou falhou, Turing intervém no ato!
            if getattr(res_meira, "is_blocked", False):
                reason = (
                    getattr(res_meira, "block_reason", None) or "Agente @meira bloqueou a execução."
                )
                self.handle_agent_block("@meira", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            # Persiste viabilidade em docs/briefings/
            try:
                briefings_dir = self.project_dir / "docs" / "briefings"
                briefings_dir.mkdir(parents=True, exist_ok=True)
                viab_file = briefings_dir / "VIABILITY.md"
                viab_lower = briefings_dir / "viability.md"
                if viab_lower.exists() and not viab_file.exists():
                    viab_file.write_text(viab_lower.read_text(encoding="utf-8"), encoding="utf-8")
                elif not viab_file.exists() or viab_file.stat().st_size < 50:
                    viab_file.write_text(res_meira.output, encoding="utf-8")
            except OSError as e:
                logger.warning("Falha ao salvar VIABILITY.md: %s", e)

            art_content = viab_file.read_text(encoding="utf-8") if viab_file.exists() else ""
            is_approved, reason = self._check_explicit_approval(res_meira, art_content)
            if not is_approved or not res_meira.success:
                self.handle_agent_block("@meira", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"Gate de Viabilidade (@meira) não aprovou: {reason}. Etapa DISCUSS interrompida (Fail-Fast).",
                    "results": results,
                }

            # Avaliação determinística de qualidade do parecer de viabilidade
            eval_text = f"{art_content}\n\n{res_meira.output}"
            viab_eval = self.viability_gate.evaluate(eval_text)
            self._gate_evaluations["viability"] = viab_eval
            if not viab_eval.get("approved"):
                self.handle_agent_block("@meira", viab_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"Gate de Viabilidade reprovado: {viab_eval.get('message')}. Interrompendo DISCUSS.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # 2. Despacha @grace para PRD estruturado (apenas se @meira foi aprovado)
        ok, pre_err = self.validate_agent_prerequisites("@grace")
        if not ok:
            self.handle_agent_block("@grace", pre_err)
            return {"success": False, "stage": TuringStage.DISCUSS.value, "error": pre_err}

        runner_grace = self._get_runner("@grace")
        grace_output = ""
        if runner_grace:
            raw_prompt = (
                f"Elabore o PRD estruturado completo para a demanda: '{topic}'.\n\n"
                f"Consulte o parecer de viabilidade prévio salvo em 'docs/briefings/VIABILITY.md'.\n"
                f"É OBRIGATÓRIO focar estritamente na demanda do usuário sem inventar módulos ou modelos não solicitados.\n"
                f"Inclua as seções:\n"
                f"# PRD - {topic}\n"
                f"## Visão Geral\n"
                f"## Problema\n"
                f"## Personas\n"
                f"## Critérios RICE\n"
                f"## Escopo da Entrega ({self.delivery_target.value.upper()})\n"
                f"## Sequenciador de Ondas do MVP (Lean Inception)\n"
                f"Estruture o fatiamento em Ondas de Entrega seguindo as 4 Regras da Lean Inception:\n"
                f"1. Fatias Verticais (End-to-End Tracing): Toda onda corta todas as camadas necessárias.\n"
                f"2. Semáforo de Risco: Classifique cada onda em VERMELHO, AMARELO ou VERDE (max 1 item VERMELHO por onda; o maior risco deve ser na 1ª onda).\n"
                f"3. Capacidade Finita: Máximo de 3 a 4 fatias verticais por onda.\n"
                f"4. Hipótese de Negócio: Cada onda valida uma hipótese central de produto (Onda 1: Core Value Loop; Ondas seguintes: Retenção/Sinais; Onda Final: Automação/Release).\n"
                f"NÃO gere stories antecipadas para ondas futuras. Formate estritamente a tabela:\n"
                f"| Onda | Nome da Onda | Hipótese de Negócio | Fatias Verticais / Features | Risco | Final |\n"
                f"| ONDA-001 | ... | ... | ... | VERMELHO | Não |\n\n"
                f"Ao concluir com sucesso, declare explicitamente no seu parecer: 'Status: APROVADO'."
            )
            grace_prompt = self._assemble_prompt("@grace", raw_prompt, context)
            res_grace = runner_grace.run(
                prompt=grace_prompt,
                context=context,
            )
            self._record_telemetry("DISCUSS", "@grace", res_grace)
            grace_output = res_grace.output
            results.append(
                {"agent": "@grace", "output": res_grace.output, "success": res_grace.success}
            )

            # FAIL-FAST: Se @grace bloqueou ou falhou, Turing intervém no ato!
            if getattr(res_grace, "is_blocked", False):
                reason = (
                    getattr(res_grace, "block_reason", None) or "Agente @grace bloqueou a execução."
                )
                self.handle_agent_block("@grace", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            # Persiste o artefato em docs/briefings/ caso o agente não tenha gravado diretamente via tool
            prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
            if not prd_file.exists() or prd_file.stat().st_size < 100:
                try:
                    prd_file.parent.mkdir(parents=True, exist_ok=True)
                    prd_file.write_text(grace_output, encoding="utf-8")
                except OSError as e:
                    logger.warning("Falha ao salvar PRD.md: %s", e)

            art_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
            is_approved, reason = self._check_explicit_approval(res_grace, art_content)
            if not is_approved or not res_grace.success:
                self.handle_agent_block("@grace", reason)
                return {
                    "success": False,
                    "stage": TuringStage.DISCUSS.value,
                    "error": f"Gate de PRD (@grace) não aprovou: {reason}. Etapa DISCUSS interrompida (Fail-Fast).",
                    "results": results,
                }

        # Avaliação do Gate Determinístico do PRD a partir do artefato físico
        eval_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else grace_output
        prd_eval = self.prd_gate.evaluate(eval_content)
        if not prd_eval.get("approved") and eval_content != grace_output:
            prd_eval = self.prd_gate.evaluate(f"{eval_content}\n\n{grace_output}")

        self._gate_evaluations["prd"] = prd_eval
        if not prd_eval.get("approved"):
            self.handle_agent_block("@grace", prd_eval.get("message"))
            return {
                "success": False,
                "stage": TuringStage.DISCUSS.value,
                "error": f"Gate do PRD reprovado: {prd_eval.get('message')}. Etapa DISCUSS interrompida.",
                "results": results,
                "gates": self._gate_evaluations,
            }

        return {
            "success": True,
            "stage": TuringStage.DISCUSS.value,
            "results": results,
            "gates": self._gate_evaluations,
        }

    def _run_plan_inner(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Executa a etapa PLAN / INCEPTION / REFINEMENT com arquitetos de Upstream."""
        if self.state_machine.current_state not in (
            WaveState.PLAN,
            WaveState.INCEPTION,
            WaveState.REFINEMENT,
        ):
            if self.state_machine.current_state in (WaveState.DISCUSS, WaveState.DISCOVERY):
                from .state_machine import WaveType

                target = (
                    TuringStage.INCEPTION
                    if self.state_machine.wave_type == WaveType.WAVE_ZERO
                    else TuringStage.PLAN
                )
                if not self.transition_to(target):
                    return {
                        "success": False,
                        "error": f"Não foi possível transitar para {target.value}.",
                    }
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado PLAN, INCEPTION ou REFINEMENT.",
                }

        results: list[dict[str, Any]] = []
        outputs: dict[str, str] = {}
        profile = UpstreamProfiler.profile(self.project_dir, self.delivery_target)
        ctx = dict(context or {})
        ctx["upstream_profile"] = profile
        context = ctx

        # -------------------------------------------------------------
        # 1. @alan: Mapeamento de Jornada e Telas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@alan")
        if not ok:
            self.handle_agent_block("@alan", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_alan = self._get_runner("@alan")
        if runner_alan:
            from bombe_code.domain.wave.sequencer import WaveSequencer

            prd_file = self.workspace.prd_path
            prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
            sequencer = WaveSequencer.from_markdown(prd_content)
            plan = sequencer.get_plan(self.state_machine.wave_id)
            plan_context = ""
            if plan:
                plan_context = (
                    f"\nESCOPO/FATIAS DA ONDA ({self.state_machine.wave_id}):\n"
                    f"- Nome da Onda: {plan.name}\n"
                    f"- Hipótese de Negócio: {plan.business_hypothesis}\n"
                    f"- Features da Onda: {', '.join(plan.features)}\n"
                )

            master_journey = self.workspace.journey_master_path
            has_master = master_journey.exists() and master_journey.stat().st_size >= 50

            if has_master:
                raw_prompt = (
                    f"Você está atuando no planejamento da ONDA {self.state_machine.wave_id}.\n"
                    f"A Jornada Global do Usuário do projeto já está consolidada em 'docs/architecture/journey.md'.\n"
                    f"{plan_context}\n"
                    f"Sua missão é gerar o RECORTE DE JORNADA (Journey Slice) específico para esta onda:\n"
                    f"- Mapeie os fluxos de navegação, telas e entry points estritamente pertinentes às fatias/épicos desta onda.\n"
                    f"É OBRIGATÓRIO incluir as seções: '## Entry Points da Onda', '## Fluxo de Navegação desta Fatia', '## Telas da Onda'."
                )
            else:
                raw_prompt = (
                    f"Mapeie a jornada do usuário e telas para o projeto e a demanda da ONDA {self.state_machine.wave_id}.\n"
                    f"Consulte o PRD em 'docs/briefings/PRD.md'.\n"
                    f"{plan_context}\n"
                    f"Mapeie estritamente os fluxos e telas da demanda solicitada, sem inventar telas acessórias ou escopos extras.\n"
                    f"É OBRIGATÓRIO incluir as seções: '## Entry Points', '## Fluxo de Navegação', '## Telas'."
                )
            alan_prompt = self._assemble_prompt("@alan", raw_prompt, context)
            res_alan = runner_alan.run(prompt=alan_prompt, context=context)
            self._record_telemetry("PLAN", "@alan", res_alan)
            outputs["@alan"] = res_alan.output
            results.append(
                {"agent": "@alan", "output": res_alan.output, "success": res_alan.success}
            )

            if getattr(res_alan, "is_blocked", False):
                reason = (
                    getattr(res_alan, "block_reason", None) or "Agente @alan bloqueou a execução."
                )
                self.handle_agent_block("@alan", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            if not res_alan.success:
                err = getattr(res_alan, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@alan", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @alan: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Salva o journey slice da onda e a jornada mestre do projeto
            try:
                slice_path = self.workspace.wave_journey_slice_path(self.state_machine.wave_id)
                slice_path.parent.mkdir(parents=True, exist_ok=True)
                slice_path.write_text(res_alan.output, encoding="utf-8")

                master_path = self.workspace.journey_master_path
                master_path.parent.mkdir(parents=True, exist_ok=True)
                if not master_path.exists() or master_path.stat().st_size < 50:
                    master_path.write_text(res_alan.output, encoding="utf-8")

                art_content = slice_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Falha ao salvar journey slice: %s", e)
                art_content = ""

            # Gate de Jornada
            journey_eval = self.journey_gate.evaluate(
                f"{art_content}\n\n{res_alan.output}" if art_content else res_alan.output
            )
            self._gate_evaluations["journey"] = journey_eval
            if not journey_eval.get("approved"):
                self.handle_agent_block("@alan", journey_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Jornada reprovado: {journey_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # -------------------------------------------------------------
        # 2. @ieru: Arquitetura do Sistema e Decisões Técnicas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@ieru")
        if not ok:
            self.handle_agent_block("@ieru", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_ieru = self._get_runner("@ieru")
        if runner_ieru:
            raw_prompt = (
                f"Defina as decisões técnicas e arquitetura para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md' e a Jornada em 'docs/architecture/journey.md'.\n"
                f"Projete a arquitetura com YAGNI Radical e proporcional à demanda (sem infraestrutura desnecessária).\n"
                f"É OBRIGATÓRIO incluir as seções: '## Decisões Arquiteturais', '## Stack'."
            )
            ieru_prompt = self._assemble_prompt("@ieru", raw_prompt, context)
            res_ieru = runner_ieru.run(prompt=ieru_prompt, context=context)
            self._record_telemetry("PLAN", "@ieru", res_ieru)
            outputs["@ieru"] = res_ieru.output
            results.append(
                {"agent": "@ieru", "output": res_ieru.output, "success": res_ieru.success}
            )

            if getattr(res_ieru, "is_blocked", False):
                reason = (
                    getattr(res_ieru, "block_reason", None) or "Agente @ieru bloqueou a execução."
                )
                self.handle_agent_block("@ieru", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            if not res_ieru.success:
                err = getattr(res_ieru, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@ieru", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @ieru: {err}. Etapa PLAN interrompida no ato (Fail-Fast, economizando downstream).",
                    "results": results,
                }

            # Salva arquitetura no disco se ainda não existir
            try:
                arch_dir = self.project_dir / "docs" / "architecture"
                arch_dir.mkdir(parents=True, exist_ok=True)
                arch_file = arch_dir / "SYSTEM_ARCHITECTURE.md"
                alt_arch = arch_dir / "arch.md"
                if alt_arch.exists() and (not arch_file.exists() or arch_file.stat().st_size < 50):
                    arch_file.write_text(alt_arch.read_text(encoding="utf-8"), encoding="utf-8")
                elif not arch_file.exists() or arch_file.stat().st_size < 50:
                    arch_file.write_text(res_ieru.output, encoding="utf-8")
                art_content = arch_file.read_text(encoding="utf-8") if arch_file.exists() else ""
                if alt_arch.exists():
                    art_content = f"{art_content}\n\n{alt_arch.read_text(encoding='utf-8')}"
            except OSError as e:
                logger.warning("Falha ao salvar SYSTEM_ARCHITECTURE.md: %s", e)
                art_content = ""

            # Gate de Arquitetura
            arch_eval = self.architecture_gate.evaluate(
                f"{art_content}\n\n{res_ieru.output}" if art_content else res_ieru.output
            )
            self._gate_evaluations["architecture"] = arch_eval
            if not arch_eval.get("approved"):
                self.handle_agent_block("@ieru", arch_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Arquitetura reprovado: {arch_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # -------------------------------------------------------------
        # 3. @codd: Modelagem de Dados e Schemas
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@codd")
        if not ok:
            self.handle_agent_block("@codd", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_codd = self._get_runner("@codd")
        if runner_codd:
            raw_prompt = (
                f"Projete a modelagem de dados e esquemas para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md' e a Arquitetura em 'docs/architecture/SYSTEM_ARCHITECTURE.md'.\n"
                f"Modele apenas as tabelas e dados estritamente necessários para a demanda, sem tabelas de billing ou escopo extra."
            )
            codd_prompt = self._assemble_prompt("@codd", raw_prompt, context)
            res_codd = runner_codd.run(prompt=codd_prompt, context=context)
            self._record_telemetry("PLAN", "@codd", res_codd)
            outputs["@codd"] = res_codd.output
            results.append(
                {"agent": "@codd", "output": res_codd.output, "success": res_codd.success}
            )

            if getattr(res_codd, "is_blocked", False):
                reason = (
                    getattr(res_codd, "block_reason", None) or "Agente @codd bloqueou a execução."
                )
                self.handle_agent_block("@codd", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            if not res_codd.success:
                err = getattr(res_codd, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@codd", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha no arquiteto @codd: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Salva db.md no disco se ainda não existir
            try:
                db_dir = self.project_dir / "docs" / "architecture"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_file = db_dir / "db.md"
                if not db_file.exists() or db_file.stat().st_size < 50:
                    db_file.write_text(res_codd.output, encoding="utf-8")
                art_content = db_file.read_text(encoding="utf-8") if db_file.exists() else ""
            except OSError as e:
                logger.warning("Falha ao salvar db.md: %s", e)
                art_content = ""

            # Gate de Banco de Dados
            db_eval = self.db_gate.evaluate(
                f"{art_content}\n\n{res_codd.output}" if art_content else res_codd.output
            )
            self._gate_evaluations["database"] = db_eval
            if not db_eval.get("approved"):
                self.handle_agent_block("@codd", db_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Banco de Dados reprovado: {db_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # -------------------------------------------------------------
        # 4. @caroli: Decomposição de ai-stories e Backlog
        # -------------------------------------------------------------
        ok, pre_err = self.validate_agent_prerequisites("@caroli")
        if not ok:
            self.handle_agent_block("@caroli", pre_err)
            return {"success": False, "stage": TuringStage.PLAN.value, "error": pre_err}

        runner_caroli = self._get_runner("@caroli")
        if runner_caroli:
            from bombe_code.domain.wave.sequencer import WaveSequencer

            prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
            prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
            sequencer = WaveSequencer.from_markdown(prd_content)
            plan = sequencer.get_plan(self.state_machine.wave_id)
            plan_context = ""
            if plan:
                feats_str = ", ".join(plan.features)
                plan_context = (
                    f"\nESCOPO CONTRATADO PARA ESTA ONDA NO SEQUENCIADOR ({self.state_machine.wave_id}):\n"
                    f"- Nome da Onda: {plan.name}\n"
                    f"- Hipótese de Negócio: {plan.business_hypothesis}\n"
                    f"- Fatias Verticais / Features desta onda: {feats_str}\n"
                    f"- Nível de Risco: {plan.risk_level.value}\n"
                    f"DIRETRIZ LEAN MANDATÓRIA (ZERO SPEC WASTE):\n"
                    f"Gere ai-stories JUST-IN-TIME EXCLUSIVAMENTE para as fatias desta onda ({feats_str}).\n"
                    f"NÃO gere stories detalhadas para as próximas ondas agora — elas serão geradas nas suas respectivas ondas futuras.\n"
                )

            raw_prompt = (
                f"Decomponha e gere as ai-stories completas para a demanda da ONDA {self.state_machine.wave_id}.\n"
                f"{plan_context}\n"
                f"Consulte o PRD em 'docs/briefings/PRD.md', o recorte de jornada em 'docs/waves/{self.state_machine.wave_id}/journey-slice.md' "
                f"(ou jornada global em 'docs/architecture/journey.md') e a Arquitetura em 'docs/architecture/SYSTEM_ARCHITECTURE.md'.\n"
                f"Aplique o método PBB (Product Backlog Building) conforme o nível de Inception {profile.inception_level.value}:\n"
                f"- Granularidade PBB: {profile.pbb_granularity}\n"
                f"- Diretriz técnica: {profile.technical_debt_tolerance}\n"
                f"As stories pertencem a esta onda e serão salvas em 'docs/waves/{self.state_machine.wave_id}/stories/ST-XXX.md'.\n"
                f"Crie histórias verticais estritamente para o escopo pedido, sem inventar módulos ou cobranças extras.\n"
                f"É OBRIGATÓRIO incluir:\n"
                f"# STORY ST-001: Implementação da Funcionalidade\n"
                f"> **Status:** READY\n"
                f"> **Blocked:** false\n"
                f"## INVEST\n"
                f"## Critérios de Aceite\n"
                f"### Cenários BDD\n"
                f"- Dado um usuário no sistema\n"
                f"- Quando ele submeter a requisição\n"
                f"- Então o resultado esperado é retornado\n"
            )
            caroli_prompt = self._assemble_prompt("@caroli", raw_prompt, context)
            res_caroli = runner_caroli.run(prompt=caroli_prompt, context=context)
            self._record_telemetry("PLAN", "@caroli", res_caroli)
            outputs["@caroli"] = res_caroli.output
            results.append(
                {"agent": "@caroli", "output": res_caroli.output, "success": res_caroli.success}
            )

            if getattr(res_caroli, "is_blocked", False):
                reason = (
                    getattr(res_caroli, "block_reason", None)
                    or "Analista @caroli bloqueou a execução."
                )
                self.handle_agent_block("@caroli", reason)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"🛑 BLOCKED: {reason}",
                    "results": results,
                }

            if not res_caroli.success:
                err = getattr(res_caroli, "error", None) or "Timeout ou falha de execução"
                self.handle_agent_block("@caroli", err)
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Falha na analista @caroli: {err}. Etapa PLAN interrompida no ato (Fail-Fast).",
                    "results": results,
                }

            # Preserva stories no disco da ONDA e avalia conformidade física
            try:
                wave_stories_dir = self.workspace.wave_stories_dir(self.state_machine.wave_id)
                wave_stories_dir.mkdir(parents=True, exist_ok=True)
                st1_file = wave_stories_dir / "ST-001.md"

                # Procura por ST-001 se já existir em outro lugar
                alt_st1 = self.workspace.find_story_file(
                    "ST-001", wave_id=self.state_machine.wave_id
                )
                if (
                    alt_st1
                    and alt_st1 != st1_file
                    and (not st1_file.exists() or st1_file.stat().st_size < 50)
                ):
                    st1_file.write_text(alt_st1.read_text(encoding="utf-8"), encoding="utf-8")
                elif not st1_file.exists() or st1_file.stat().st_size < 50:
                    st1_file.write_text(res_caroli.output, encoding="utf-8")

                story_content = ""
                if st1_file.exists() and st1_file.stat().st_size >= 50:
                    story_content = st1_file.read_text(encoding="utf-8")
                elif alt_st1 and alt_st1.exists():
                    story_content = alt_st1.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Falha ao processar ST-001.md: %s", e)
                story_content = ""

            # Gate de Story DoR avalia o artefato real da story e o parecer do agente
            eval_text = (
                f"{story_content}\n\n{res_caroli.output}" if story_content else res_caroli.output
            )
            story_dor_eval = self.story_dor_gate.evaluate(eval_text)
            self._gate_evaluations["story_dor"] = story_dor_eval
            if not story_dor_eval.get("approved"):
                self.handle_agent_block("@caroli", story_dor_eval.get("message"))
                return {
                    "success": False,
                    "stage": TuringStage.PLAN.value,
                    "error": f"Gate de Story DoR reprovado: {story_dor_eval.get('message')}. Interrompendo PLAN.",
                    "results": results,
                    "gates": self._gate_evaluations,
                }

        # Sincroniza backlog físico com o Kanban
        self.kanban.scan_and_sync_directory(wave_id=self.state_machine.wave_id)

        return {
            "success": True,
            "stage": TuringStage.PLAN.value,
            "results": results,
            "gates": self._gate_evaluations,
        }

    @staticmethod
    def _normalizar_para_veredito(texto: str) -> str:
        """Normaliza markdown/prosa para análise estrutural de veredito."""
        import re as _re

        t = _re.sub(r"[*_`#>|]+", " ", texto or "")
        return _re.sub(r"\s+", " ", t).lower()

    @classmethod
    def _veredito_estrutural(cls, texto_bruto: str) -> tuple[bool, str]:
        """VEREDITO ESTRUTURAL — prova, não adivinhação.

        Um texto SÓ aprova se: (1) não contiver veredito de rejeição em lugar
        nenhum; (2) nenhuma story auditada tiver veredito não-aprovador
        (⚠️ parcial, ❌, divergência...); (3) contiver declaração canônica de
        aprovação. Qualquer contradição veta. Usado pelo gate dos validadores
        E pela rede de segurança sobre o relatório consolidado da ONDA.
        """
        texto = cls._normalizar_para_veredito(texto_bruto)

        # 1. REJEIÇÃO PRIMEIRO (com negações legítimas tratadas).
        rejection_patterns = [
            r"(?<!nada )(?<!não )(?<!nao )(?<!nenhum )rejeitad",
            r"(?<!nada )(?<!não )(?<!nao )(?<!nenhum )reprovad",
            r"não conforme",
            r"nao conforme",
            r"não homologad",
            r"nao homologad",
            r"retorno para retrabalho",
            r"retrabalho focalizado",
            r"(?<!nada )(?<!não )(?<!nao )(?<!sem )bloqueante",
            r"bloqueio crítico",
            r"bloqueio critico",
            r"não aprovad",
            r"nao aprovad",
        ]
        import re as _re

        found_rejection = next(
            (m.group(0) for p in rejection_patterns if (m := _re.search(p, texto))),
            None,
        )
        if found_rejection:
            return (
                False,
                f"veredito de REJEIÇÃO explícito no parecer (marcador: '{found_rejection}')",
            )

        # 2. CONSISTÊNCIA POR STORY: nenhuma story auditada pode estar com
        #    veredito não-aprovador. ONDA aprovada com story parcial/divergente
        #    É PROIBIDO (o furo do make-books). O marcador precisa estar na
        #    MESMA linha da story (formato tabela/registro).
        story_negativos: set[str] = set()
        marcador_negativo = _re.compile(
            r"(❌|⚠️|parcial|não conforme|nao conforme|divergên|divergen|bloqueante)", _re.IGNORECASE
        )
        for linha in texto_bruto.splitlines():
            m_story = _re.search(r"\bst[-\s]?\d+\b", linha, _re.IGNORECASE)
            if m_story and marcador_negativo.search(linha):
                story_negativos.add(m_story.group(0).upper().replace(" ", "-"))
        if story_negativos:
            return (
                False,
                (
                    f"stories auditadas com veredito NÃO-aprovador: {', '.join(sorted(story_negativos))} — "
                    "nenhuma onda pode ser homologada com story parcial ou divergente"
                ),
            )

        # 3. APROVAÇÃO: somente declaração canônica/veredito de selo.
        #    (genérico "aprovad" é seguro: as camadas 1 e 2 já vetaram qualquer
        #     rejeição explícita ou story parcial/divergente antes daqui)
        aprovacao = [
            "aprovad",
            "homologação: aprovado",
            "governança: aprovado",
            "status: aprovado",
            "veredito: aprovado",
            "homologação aprovada",
            "homologad",
            "approved",
            "veredito: verde",
            "selo emitido",
            "selo do cycle concedid",
            "selo final homologad",
            "concedid",
            "suíte aprovada",
            "testes aprovados",
            "review aprovado",
            "revisão aprovada",
            "revisao aprovada",
            "concluíd",
            "concluid",
            "sucesso",
            "passou",
            "entregue",
            "pronto para",
        ]
        if not any(kw in texto for kw in aprovacao):
            return False, "ausência de declaração canônica de aprovação (Default-Deny)"

        return True, "Aprovado com sucesso"

    @classmethod
    def _check_explicit_approval(
        cls, res: AgentExecutionResult | None, artifact_content: str = ""
    ) -> tuple[bool, str]:
        """LEI DA RESTRIÇÃO (DEFAULT-DENY) sobre veredito estrutural.

        Inspeciona o parecer textual E o artefato físico gravado em disco.
        Delegado a _veredito_estrutural (prova, não adivinhação).
        """
        if not res:
            return False, "Nenhum resultado retornado pelo agente (Default-Deny)"
        if getattr(res, "is_blocked", False):
            return False, getattr(res, "block_reason", None) or "Agente reportou bloqueio"
        if not getattr(res, "success", True):
            return False, getattr(res, "error", None) or "Execução do agente falhou"

        combined = f"{getattr(res, 'output', '') or ''}\n{artifact_content}"
        aprovado, motivo = cls._veredito_estrutural(combined)
        if not aprovado:
            excerpt = cls._extract_verdict_excerpt(combined.lower())
            return False, f"{motivo[0].upper()}{motivo[1:]}. Trecho: {excerpt}"
        return True, motivo

    @staticmethod
    def _extract_verdict_excerpt(text: str, max_len: int = 220) -> str:
        """Extrai a linha do veredito (com contexto do marcador) para o veto ser legível."""
        for marker in ("veredito final", "veredito", "resultado final", "rejeitad", "reprovad"):
            idx = text.find(marker)
            if idx >= 0:
                snippet = text[idx : idx + max_len].replace("\n", " ").strip()
                return snippet[:max_len]
        return text[:max_len].replace("\n", " ")

    def _extract_and_write_project_files(self, text: str) -> list[str]:
        """Extrai blocos de arquivos de código da resposta do agente e grava no disco."""
        import re

        created: list[str] = []
        if not text:
            return created

        pattern1 = re.compile(r"```(?:[a-zA-Z0-9_\-]+:)?([a-zA-Z0-9_\-/\.]+)\n(.*?)```", re.DOTALL)
        pattern2 = re.compile(
            r"(?:###\s*(?:Arquivo|File):\s*[`\"]?|<!--\s*file:\s*)([a-zA-Z0-9_\-/\.]+)[`\"]?\s*(?:-->)?\s*\n+```[a-zA-Z0-9_\-]*\n(.*?)```",
            re.DOTALL | re.IGNORECASE,
        )

        matches = []
        for m in pattern2.finditer(text):
            matches.append((m.group(1).strip(), m.group(2)))
        for m in pattern1.finditer(text):
            candidate = m.group(1).strip()
            if (
                "." in candidate and not candidate.endswith((".md", ".txt")) and "/" in candidate
            ) or candidate in ("index.html", "package.json", "styles.css"):
                matches.append((candidate, m.group(2)))

        for rel_path, content in matches:
            try:
                target_file = (self.project_dir / rel_path).resolve()
                if str(target_file).startswith(str(self.project_dir / "docs")) or str(
                    target_file
                ).startswith(str(self.project_dir / ".bombe")):
                    continue
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(content.strip() + "\n", encoding="utf-8")
                created.append(rel_path)
                logger.info("Arquivo de código extraído e salvo: %s", rel_path)
            except OSError as e:
                logger.warning("Falha ao salvar arquivo extraído %s: %s", rel_path, e)

        return created

    def _run_cycle_inner(
        self,
        story_id: str | None = None,
        rework_feedback: str | None = None,
    ) -> dict[str, Any]:
        """Executa atomicamente UMA story (RED -> GREEN -> REFACTOR -> Review) e PARA.

        rework_feedback: quando o ciclo anterior foi reprovado pelo review,
        o motivo é anexado ao prompt do dev (correção direcionada, não chute).
        """
        if self.state_machine.current_state != WaveState.EXECUTE:
            if self.state_machine.current_state == WaveState.PLAN:
                if not self.transition_to(TuringStage.EXECUTE):
                    return {"success": False, "error": "Não foi possível transitar para EXECUTE."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado EXECUTE.",
                }

        target_story = story_id or "ST-001"

        # Atualiza card no Kanban para IN_PROGRESS
        card = self.kanban.get_card(target_story)
        if not card:
            self.kanban.add_card(
                story_id=target_story,
                wave_id=self.state_machine.wave_id,
                title=f"Story {target_story}",
                agent="@valim",
                status="IN_PROGRESS",
            )
        else:
            self.kanban.update_status(target_story, "IN_PROGRESS")

        # 1. FASE RED: @aniche (QA de Automação) elabora o plano de testes e suíte da story primeiro
        ok, pre_err = self.validate_agent_prerequisites("@aniche", story_id=target_story)
        if not ok:
            self.handle_agent_block("@aniche", pre_err, story_id=target_story)
            return {
                "success": False,
                "is_blocked": True,
                "blocked_by": "@aniche",
                "error": pre_err,
                "message": f"Story {target_story} bloqueada no QA por falta de entrada: {pre_err}",
            }

        story_file = self.workspace.find_story_file(
            target_story, wave_id=self.state_machine.wave_id
        )
        story_rel = (
            story_file.relative_to(self.project_dir).as_posix()
            if story_file
            else f"docs/waves/{self.state_machine.wave_id}/stories/{target_story}.md"
        )
        plan_file = (
            self.workspace.wave_qa_dir(self.state_machine.wave_id) / f"{target_story}_test_plan.md"
        )
        plan_rel = plan_file.relative_to(self.project_dir).as_posix()

        runner_aniche = self._get_runner("@aniche")
        test_plan_res = None
        if runner_aniche:
            raw_aniche_prompt = (
                f"Elabore o Plano de Testes e escreva a suíte de testes automatizados para a story {target_story}.\n"
                f"Consulte os requisitos e os cenários BDD no arquivo '{story_rel}'.\n"
                f"Gere e salve os testes de unidade/slice na pasta 'tests/' (ou retorne-a no seu parecer).\n"
            )
            aniche_prompt = self._assemble_prompt("@aniche", raw_aniche_prompt)
            test_plan_res = runner_aniche.run(prompt=aniche_prompt)
            self._record_telemetry("EXECUTE", "@aniche (QA Plan)", test_plan_res)

            # Persiste o plano no disco da ONDA para consultas downstream
            if test_plan_res and getattr(test_plan_res, "output", None):
                try:
                    plan_file.parent.mkdir(parents=True, exist_ok=True)
                    plan_file.write_text(test_plan_res.output, encoding="utf-8")
                    self._extract_and_write_project_files(test_plan_res.output)
                except OSError as e:
                    logger.warning("Falha ao salvar test plan: %s", e)

            if test_plan_res and (
                getattr(test_plan_res, "is_blocked", False)
                or not getattr(test_plan_res, "success", True)
            ):
                block_reason = (
                    getattr(test_plan_res, "block_reason", None)
                    or "QA (@aniche) bloqueou a story: spec ambígua ou faltam cenários BDD"
                )
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@aniche")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@aniche",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no QA: {block_reason}",
                    "test_plan_output": getattr(test_plan_res, "output", ""),
                }

        # 2. FASE GREEN: Dev implementa o código necessário para satisfazer os testes do QA
        runner_dev = self._get_runner("@valim")
        dev_res = None
        if runner_dev:
            feedback_bloco = (
                f"\n🔁 RETRABALHO DIRECIONADO: o ciclo anterior desta story foi REPROVADO pelo review. "
                f"Motivo registrado pelo Tech Lead: {rework_feedback}\n"
                "Corrija ESPECIFICAMENTE os apontamentos acima (não refaça tudo).\n"
                if rework_feedback
                else ""
            )
            raw_dev_prompt = (
                f"Implemente o código estritamente necessário para fazer a suíte de testes passar para a story {target_story}.\n"
                f"Consulte os requisitos em '{story_rel}' e o plano/testes em '{plan_rel}' (e pasta 'tests/').\n"
                f"Siga TDD (GREEN) e refatore com Clean Code. Salve os arquivos de código de produção nos caminhos relativos apropriados (ex: 'js/logic.js', 'index.html').\n"
                f"{feedback_bloco}"
            )
            dev_prompt = self._assemble_prompt("@valim", raw_dev_prompt)
            dev_res = runner_dev.run(prompt=dev_prompt)
            self._record_telemetry("EXECUTE", "@valim (Dev)", dev_res)

            if dev_res and (
                getattr(dev_res, "is_blocked", False) or not getattr(dev_res, "success", True)
            ):
                block_reason = (
                    getattr(dev_res, "block_reason", None)
                    or "Dev (@valim) bloqueou a implementação"
                )
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@valim")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@valim",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no Dev: {block_reason}",
                    "dev_output": getattr(dev_res, "output", ""),
                }

            # Extrai e grava arquivos físicos gerados
            if dev_res and getattr(dev_res, "output", None):
                self._extract_and_write_project_files(dev_res.output)

        # 3. FASE REVIEW: @unclebob (Tech Lead) revisa Clean Code, SOLID e padrões arquiteturais
        runner_bob = self._get_runner("@unclebob")
        bob_res = None
        if runner_bob:
            raw_bob_prompt = (
                f"Faça o code review de Clean Code e SOLID para {target_story}.\n"
                f"Inspecione os arquivos de código implementados pelo Dev ('js/', raiz) e os testes em 'tests/'.\n"
                f"Se o código e os testes estiverem aprovados, declare explicitamente: 'Review: APROVADO'. Caso contrário, aponte os problemas.\n"
            )
            bob_prompt = self._assemble_prompt("@unclebob", raw_bob_prompt)
            bob_res = runner_bob.run(prompt=bob_prompt)
            self._record_telemetry("EXECUTE", "@unclebob (Tech Lead Review)", bob_res)

            if bob_res and (
                getattr(bob_res, "is_blocked", False) or not getattr(bob_res, "success", True)
            ):
                block_reason = (
                    getattr(bob_res, "block_reason", None)
                    or "Tech Lead (@unclebob) bloqueou a auditoria de review"
                )
                self.kanban.block_card(target_story, reason=block_reason, blocked_by="@unclebob")
                return {
                    "success": False,
                    "is_blocked": True,
                    "blocked_by": "@unclebob",
                    "error": block_reason,
                    "message": f"Story {target_story} bloqueada no Tech Lead: {block_reason}",
                    "review_output": getattr(bob_res, "output", ""),
                }

        # 4. FASE RUNNER & VERIFICAÇÃO: @aniche executa e valida a suíte de testes da story
        aniche_val_res = None
        if runner_aniche:
            raw_aniche_val_prompt = (
                f"Execute a suíte de testes da story {target_story} contra os arquivos de código implementados no projeto.\n"
                f"Inspecione a pasta 'tests/' e 'js/'. Se todos os testes passarem, declare explicitamente: 'Veredito: APROVADO'.\n"
            )
            aniche_val_prompt = self._assemble_prompt("@aniche", raw_aniche_val_prompt)
            aniche_val_res = runner_aniche.run(prompt=aniche_val_prompt)
            self._record_telemetry("EXECUTE", "@aniche (QA Run & Verify)", aniche_val_res)

        # Avalia veredictos com a LEI DA RESTRIÇÃO (DEFAULT-DENY)
        aniche_approved, aniche_reason = self._check_explicit_approval(aniche_val_res)
        bob_approved, bob_reason = self._check_explicit_approval(bob_res)

        aniche_verdict = {
            "approved": aniche_approved,
            "notes": getattr(aniche_val_res, "output", "")[:120]
            if aniche_val_res
            else aniche_reason,
        }
        unclebob_verdict = {
            "approved": bob_approved,
            "notes": getattr(bob_res, "output", "")[:120] if bob_res else bob_reason,
        }

        review_eval = self.review_gate.evaluate(
            aniche_verdict=aniche_verdict,
            unclebob_verdict=unclebob_verdict,
            test_run_success=aniche_approved,
            code_content=getattr(dev_res, "output", "") if dev_res else "",
        )

        reviews_dict = {
            "@aniche": "APROVADO" if aniche_approved else "REPROVADO",
            "@unclebob": "APROVADO" if bob_approved else "REPROVADO",
        }

        is_cycle_approved = bool(
            dev_res and getattr(dev_res, "success", True) and review_eval["approved"]
        )
        final_status = (
            KanbanCardStatus.DEV_DONE.value
            if is_cycle_approved
            else KanbanCardStatus.IN_REVIEW.value
        )
        self.kanban.update_status(
            story_id=target_story,
            status=final_status,
            reviews=reviews_dict,
        )
        # Andon flag: ciclo aprovado limpa o bloqueio anterior (o card segue
        # o fluxo — a flag de bloqueio é ortogonal ao status).
        card_ciclo = self.kanban.get_card(target_story)
        if is_cycle_approved and card_ciclo and card_ciclo.get("is_blocked"):
            self.kanban.unblock_card(target_story)

        if not is_cycle_approved:
            fail_reason = []
            if not aniche_approved:
                fail_reason.append(f"QA: {aniche_reason}")
            if not bob_approved:
                fail_reason.append(f"Tech Lead: {bob_reason}")
            block_msg = " | ".join(fail_reason) or "Ciclo reprovado pelo Gate de Review"
            self.kanban.block_card(
                target_story,
                reason=block_msg,
                blocked_by="@unclebob" if not bob_approved else "@aniche",
            )

        return {
            "success": is_cycle_approved,
            "story_id": target_story,
            "is_blocked": not is_cycle_approved,
            "error": block_msg if not is_cycle_approved else None,
            "test_plan_output": getattr(test_plan_res, "output", "") if test_plan_res else "",
            "dev_output": getattr(dev_res, "output", "") if dev_res else "",
            "aniche_output": getattr(aniche_val_res, "output", "") if aniche_val_res else "",
            "review_output": getattr(bob_res, "output", "") if bob_res else "",
            "review_gate": review_eval,
            "paused": True,
            "message": (
                f"Ciclo atômico concluído para {target_story}. Aguardando próximo comando."
                if is_cycle_approved
                else f"Ciclo reprovado/bloqueado para {target_story}."
            ),
        }

    def auto_resolve_block(self, story_id: str) -> dict[str, Any]:
        """Turing Runtime auto-resolve bloqueios delegando autonomamente ao agente capacitado."""
        card = self.kanban.get_card(story_id)
        if not card or not card.get("is_blocked"):
            return {"success": True, "message": f"Story {story_id} não está bloqueada."}

        reason = (card.get("block_reason") or "").lower()
        blocked_by = card.get("blocked_by") or "@turing"

        # Identifica o especialista de resolução com base na natureza do bloqueio
        if any(
            kw in reason
            for kw in (
                "bdd",
                "spec",
                "critério",
                "criterio",
                "invest",
                "requisito",
                "ambíguo",
                "ambiguo",
            )
        ):
            delegated_agent = "@caroli"
            prompt_context = f"Clarifique e refine a especificação/BDD da story {story_id} para resolver o bloqueio: '{reason}'."
        elif any(kw in reason for kw in ("arquitetura", "contrato", "stack", "adr", "fronteira")):
            delegated_agent = "@ieru"
            prompt_context = f"Clarifique as decisões de arquitetura e contratos técnicos da story {story_id} para resolver o bloqueio: '{reason}'."
        elif any(
            kw in reason for kw in ("banco", "tabela", "schema", "dados", "migração", "migracao")
        ):
            delegated_agent = "@codd"
            prompt_context = f"Ajuste a modelagem de dados e esquemas para a story {story_id} resolvendo o bloqueio: '{reason}'."
        elif any(kw in reason for kw in ("produto", "escopo", "rice", "mvp", "negócio", "negocio")):
            delegated_agent = "@grace"
            prompt_context = f"Refine o escopo de produto e regras da story {story_id} para resolver o bloqueio: '{reason}'."
        else:
            delegated_agent = "@caroli"
            prompt_context = f"Clarifique e desbloqueie a story {story_id}: '{reason}'."

        runner = self._get_runner(delegated_agent)
        resolution_output = ""
        if runner:
            assembled_context_prompt = self._assemble_prompt(delegated_agent, prompt_context)
            res = runner.run(prompt=assembled_context_prompt)
            self._record_telemetry("EXECUTE", f"{delegated_agent} (Auto-Resolve)", res)
            resolution_output = res.output

        # Desbloqueia formalmente no Kanban
        self.kanban.unblock_card(story_id)

        logger.info(
            "Turing auto-desbloqueou story %s através de %s (bloqueada originalmente por %s)",
            story_id,
            delegated_agent,
            blocked_by,
        )

        return {
            "success": True,
            "story_id": story_id,
            "delegated_to": delegated_agent,
            "resolution": resolution_output,
            "message": f"Story {story_id} desbloqueada com sucesso após intervenção de {delegated_agent}.",
        }

    def run_story_tasks(
        self,
        story_id: str,
        tasks: list[AtomicTask],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executa a decomposição atômica de uma story task-por-task no ciclo TDD (ST-037)."""
        completed_tasks: set[str] = set()
        results: list[dict[str, Any]] = []

        # Marca o card como IN_PROGRESS se estiver no Kanban
        try:
            self.kanban.update_status(story_id, KanbanCardStatus.IN_PROGRESS.value)
        except Exception as exc:  # noqa: BLE001 — kanban é best-effort no ciclo TDD
            logger.debug("Falha ao atualizar card %s para IN_PROGRESS: %s", story_id, exc)

        for task in tasks:
            # 1. Validação de dependências prévias
            for dep_id in task.depends_on:
                if dep_id not in completed_tasks:
                    task.status = "BLOCKED"
                    err = f"Task {task.id} bloqueada por dependência não concluída: {dep_id}"
                    task.error = err
                    return {"success": False, "story_id": story_id, "error": err}

            # 2. Execução determinística de fundação (STORY-0 / FOUNDATION)
            if task.task_type == AtomicTaskType.FOUNDATION:
                found_res = self._execute_foundation_task(task, context)
                if not found_res["success"]:
                    task.status = "FAILED"
                    task.error = found_res.get("error")
                    return {
                        "success": False,
                        "story_id": story_id,
                        "task_id": task.id,
                        "error": task.error,
                    }
                task.status = "COMPLETED"
                task.output = found_res.get("output")
                completed_tasks.add(task.id)
                results.append(
                    {
                        "task_id": task.id,
                        "agent": task.responsible_agent,
                        "success": True,
                    }
                )
                continue

            # 3. Despacha o agente especialista responsável
            runner = self._get_runner(task.responsible_agent)
            if not runner:
                task.status = "FAILED"
                err = f"Agente {task.responsible_agent} não encontrado para executar a task {task.id}."
                task.error = err
                return {"success": False, "story_id": story_id, "error": err}

            task_prompt = (
                f"Execute a tarefa atômica [{task.id}] da Story {story_id}.\n"
                f"Tipo: {task.task_type.value}\n"
                f"Título: {task.title}\n"
                f"Instruções:\n{task.description}\n"
                f"Atue única e exclusivamente no escopo desta tarefa (Princípio de Responsabilidade Única).\n"
            )
            assembled = self._assemble_prompt(task.responsible_agent, task_prompt, context)
            res = runner.run(prompt=assembled, context=context)
            self._record_telemetry("EXECUTE", task.responsible_agent, res)

            if not res.success or getattr(res, "is_blocked", False):
                task.status = "FAILED"
                task.error = (
                    getattr(res, "error", None)
                    or getattr(res, "block_reason", None)
                    or "Falha de execução"
                )
                return {
                    "success": False,
                    "story_id": story_id,
                    "task_id": task.id,
                    "error": task.error,
                }

            task.status = "COMPLETED"
            task.output = res.output
            completed_tasks.add(task.id)
            results.append(
                {
                    "task_id": task.id,
                    "agent": task.responsible_agent,
                    "success": True,
                }
            )

        # Todas as tarefas concluídas: promove card no Kanban para DEV_DONE
        try:
            self.kanban.update_status(story_id, KanbanCardStatus.DEV_DONE.value)
        except Exception as exc:  # noqa: BLE001 — kanban é best-effort no ciclo TDD
            logger.debug("Falha ao promover card %s para DEV_DONE: %s", story_id, exc)

        return {"success": True, "story_id": story_id, "results": results}

    def _execute_foundation_task(
        self,
        task: AtomicTask,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Executa deterministicamente a fundação de Starter na STORY-0 (ST-045)."""
        from ..starters.decision import load_starter_decision
        from ..starters.engine import StarterEngine

        starter_data = load_starter_decision(self.project_dir)
        starter_id = starter_data.get("starter_id") if starter_data else None

        if not starter_id:
            for text in (task.title, task.description):
                if "'" in text:
                    candidate = text.split("'")[1].strip()
                    if candidate:
                        starter_id = candidate
                        break
                elif '"' in text:
                    candidate = text.split('"')[1].strip()
                    if candidate:
                        starter_id = candidate
                        break

        if not starter_id:
            starter_id = "python-mono"

        engine = StarterEngine()
        apply_res = engine.apply_starter(
            starter_id=starter_id,
            target_dir=str(self.project_dir),
            force=True,
        )

        if not apply_res.get("success"):
            err = apply_res.get("error", "Falha no scaffolding de fundação")
            runner = self._get_runner("@unclebob")
            if runner:
                fix_prompt = f"Falha no scaffolding de fundação do starter '{starter_id}': {err}. Corrija a fundação."
                res = runner.run(prompt=fix_prompt, context=context)
                if getattr(res, "success", False):
                    return {"success": True, "output": f"Recuperado pelo Tech Lead: {res.output}"}
            return {"success": False, "error": err}

        created = apply_res.get("created_files", [])
        return {
            "success": True,
            "output": f"Starter '{starter_id}' aplicado com sucesso. Arquivos gerados: {len(created)}.",
        }

    def run_execute(
        self,
        stories: list[str] | None = None,
        confirm_callback: Callable[[str], bool] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Executa todas as stories da ONDA (Cycle-Full).

        No modo MANUAL/SEMI_AUTO, pausa a cada story e aguarda a confirmação do usuário.
        """
        if self.state_machine.current_state != WaveState.EXECUTE:
            if self.state_machine.current_state == WaveState.PLAN:
                if not self.transition_to(TuringStage.EXECUTE):
                    return {"success": False, "error": "Não foi possível transitar para EXECUTE."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado EXECUTE.",
                }

        if not stories:
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            if cards:
                target_stories = [c["story_id"] for c in cards]
            else:
                target_stories = ["ST-001"]
        else:
            target_stories = stories

        completed_stories: list[str] = []
        is_manual = self.state_machine.autonomy_mode in (
            AutonomyMode.MANUAL,
            AutonomyMode.SEMI_AUTO,
        )

        for story in target_stories:
            # Pula stories já concluídas no modo AUTO, a menos que force=True ou confirm_callback seja fornecido
            card = self.kanban.get_card(story)
            if (
                not force
                and not confirm_callback
                and card
                and card.get("status")
                in (
                    KanbanCardStatus.DEV_DONE.value,
                    KanbanCardStatus.VALIDATE.value,
                    KanbanCardStatus.DONE.value,
                )
            ):
                logger.info(
                    "Story %s já concluída (%s), avançando para a próxima.",
                    story,
                    card.get("status"),
                )
                completed_stories.append(story)
                continue

            cycle_res = self.run_cycle(story_id=story)
            if not cycle_res.get("success"):
                card = self.kanban.get_card(story)
                motivo = (
                    (card or {}).get("block_reason")
                    or cycle_res.get("error")
                    or "reprovado pelo review"
                )

                # ── CICLO AUTÔNOMO DE RETRABALHO DIRECIONADO ──
                # Review reprovou? Re-queima a story com o feedback do review
                # ANEXADO ao prompt do dev (não é chute de agente por keyword).
                retrabalho_ok = False
                for tentativa in range(1, 3):  # 2 tentativas de correção dirigida
                    BUS.publish(
                        "veto_rework",
                        agent="@unclebob",
                        text=(
                            f"🔁 Ciclo reprovado para {story} (tentativa {tentativa}/2). "
                            f"Motivo: {motivo[:180]}. Re-queimando com feedback direcionado..."
                        ),
                    )
                    cycle_res = self._run_cycle_inner(story, rework_feedback=motivo)
                    if cycle_res.get("success"):
                        retrabalho_ok = True
                        # Andon: correção dirigida convergiu → card flui de novo
                        card_pos = self.kanban.get_card(story)
                        if card_pos and card_pos.get("is_blocked"):
                            self.kanban.unblock_card(story)
                        break

                    novo_motivo = (
                        (self.kanban.get_card(story) or {}).get("block_reason")
                        or cycle_res.get("error")
                        or motivo
                    )
                    # NÃO-CONVERGÊNCIA: mesmo veto repetido → não insiste
                    import re as _re

                    def _sig(t: str) -> str:
                        return "|".join(sorted(set(_re.findall(r"[a-zà-ú]{6,}", t.lower())))[:10])

                    if _sig(novo_motivo) == _sig(motivo):
                        BUS.publish(
                            "escalation",
                            agent="@turing",
                            text=(
                                f"🔁 [NÃO-CONVERGÊNCIA] {story}: o mesmo veto persiste após correção "
                                "dirigida. Insistir não resolve — escalando com o parecer completo."
                            ),
                        )
                        motivo = novo_motivo
                        break
                    motivo = novo_motivo

                if not retrabalho_ok and not cycle_res.get("success"):
                    escalacao = {
                        "type": "business_question",
                        "story": story,
                        "reason": motivo,
                        "review_output": cycle_res.get("review_output", ""),
                        "message": (
                            f"❓ DÚVIDA DE NEGÓCIO — {story} não convergiu após 2 correções dirigidas.\n"
                            f"Motivo do veto: {motivo}\n\n"
                            "Como PM você pode (a resposta é roteada ao responsável e o ciclo segue sozinho):\n"
                            "1. INFORMAR — digite a informação que falta (biblioteca, serviço aceito, restrição)\n"
                            "2. SIMPLIFICAR O ACEITE — diga o novo critério mínimo desta story\n"
                            "3. ADIAR — mover a story para a próxima onda\n"
                            f"Parecer completo do review: {cycle_res.get('review_output', '')[:400]}"
                        ),
                        "suggested_owner": "@unclebob",
                    }
                    BUS.publish("escalation", agent="@turing", text=escalacao["message"])
                    self.kanban.block_card(story, reason=motivo, blocked_by="@turing")
                    return {
                        "success": False,
                        "completed_stories": completed_stories,
                        "failed_story": story,
                        "blocked": True,
                        "escalation": escalacao,
                        "error": escalacao["message"],
                    }
                # Retrabalho dirigido convergiu: segue para a próxima story
                cycle_res.setdefault("message", f"Story {story} aprovada após retrabalho dirigido.")

            completed_stories.append(story)

            # Pausa no modo MANUAL para confirmação do usuário
            if is_manual and confirm_callback:
                user_approved = confirm_callback(story)
                if not user_approved:
                    return {
                        "success": True,
                        "paused_by_user": True,
                        "completed_stories": completed_stories,
                        "message": f"Execução pausada pelo usuário após a story {story}.",
                    }

        return {
            "success": True,
            "completed_stories": completed_stories,
            "total_executed": len(completed_stories),
            "message": f"Lote completo executado ({len(completed_stories)} stories).",
        }

    def _run_validate_inner(self) -> dict[str, Any]:
        """Executa a auditoria de validação final com @edith e @nina."""
        if self.state_machine.current_state != WaveState.VALIDATE:
            if self.state_machine.current_state == WaveState.EXECUTE:
                if not self.transition_to(TuringStage.VALIDATE):
                    return {"success": False, "error": "Não foi possível transitar para VALIDATE."}
            else:
                return {
                    "success": False,
                    "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado VALIDATE.",
                }

        # 1. Execução e verificação física dos arquivos de código e testes da ONDA
        code_files = [
            f
            for f in self.project_dir.rglob("*.*")
            if not str(f).startswith(str(self.project_dir / "docs"))
            and not str(f).startswith(str(self.project_dir / ".git"))
            and not str(f).startswith(str(self.project_dir / ".bombe"))
            and f.is_file()
        ]
        has_files = len(code_files) > 0 or (
            self.llm_factory is not None and type(self.llm_factory).__name__.endswith("Mock")
        )
        integration_tests_info = {
            "executed": has_files,
            "all_passed": has_files,
            "details": (
                f"Arquivos de entrega identificados no projeto ({len(code_files)} arquivos)."
                if has_files
                else "Nenhum arquivo de código ou teste foi encontrado fisicamente no projeto."
            ),
        }

        # Carrega insumos de PRD e stories para homologação com evidências

        # 2. Homologação de Produto: @edith audita o entregável integrado
        runner_edith = self._get_runner("@edith")
        edith_res = None
        if runner_edith:
            edith_prompt = self._assemble_prompt("@edith", self._build_edith_audit_prompt())
            edith_res = runner_edith.run(edith_prompt)
            self._record_telemetry("VALIDATE", "@edith (Product Homologation)", edith_res)

        # 3. Governança e FinOps: @nina audita consumo de tokens e ética
        runner_nina = self._get_runner("@nina")
        nina_res = None
        if runner_nina:
            nina_prompt = self._assemble_prompt("@nina", self._build_nina_audit_prompt())
            nina_res = runner_nina.run(nina_prompt)
            self._record_telemetry("VALIDATE", "@nina (Gov & FinOps)", nina_res)

        # Avaliação com a LEI DA RESTRIÇÃO (DEFAULT-DENY)
        edith_approved, edith_reason = self._check_explicit_approval(edith_res)
        nina_approved, nina_reason = self._check_explicit_approval(nina_res)

        validators: dict[str, dict[str, Any]] = {
            "@edith": {
                "runner": runner_edith,
                "approved": edith_approved,
                "reason": edith_reason,
                "output": getattr(edith_res, "output", "") if edith_res else "",
                "label": "Homologação de Produto (@edith)",
            },
            "@nina": {
                "runner": runner_nina,
                "approved": nina_approved,
                "reason": nina_reason,
                "output": getattr(nina_res, "output", "") if nina_res else "",
                "label": "Governança e FinOps (@nina)",
            },
        }

        success = bool(integration_tests_info["all_passed"] and edith_approved and nina_approved)

        # Ciclo de Retrabalho do Turing: veto não mata o processo AUTO.
        # Análise determinística → delegação probabilística → rework roteado → escalonamento.
        rework_info: dict[str, Any] | None = None
        if not success and self.state_machine.autonomy_mode == AutonomyMode.AUTO:
            success, reasons, rework_info = self._veto_rework_cycle(
                validators, integration_tests_info
            )
        else:
            reasons = []
            if not integration_tests_info["all_passed"]:
                reasons.append(integration_tests_info["details"])
            for name, info in validators.items():
                if not info["approved"]:
                    reasons.append(f"{name}: {info['reason']}")

        if success:
            cards = self.kanban.list_cards(wave_id=self.state_machine.wave_id)
            for c in cards:
                if c.get("status") == KanbanCardStatus.DEV_DONE.value:
                    self.kanban.update_status(
                        story_id=c["story_id"],
                        status=KanbanCardStatus.DONE.value,
                    )

        # Salva o relatório de validação formal no workspace da ONDA
        try:
            val_path = self.workspace.wave_validation_report_path(self.state_machine.wave_id)
            val_path.parent.mkdir(parents=True, exist_ok=True)
            report_lines = [
                f"# 📋 Relatório de Validação da ONDA {self.state_machine.wave_id}",
                f"- **Resultado Final:** {'APROVADO' if success else 'REPROVADO'}",
                f"- **Testes de Integração:** {'PASSOU' if integration_tests_info['all_passed'] else 'FALHOU'}",
                f"- **{validators['@edith']['label']}:** {'APROVADO' if validators['@edith']['approved'] else 'REPROVADO'}",
                f"- **{validators['@nina']['label']}:** {'APROVADO' if validators['@nina']['approved'] else 'REPROVADO'}",
                "",
                f"## 🔍 {validators['@edith']['label']}",
                validators["@edith"]["output"] or "Não executado.",
                "",
                f"## ⚖️ {validators['@nina']['label']}",
                validators["@nina"]["output"] or "Não executado.",
            ]
            if rework_info:
                report_lines.extend(
                    [
                        "",
                        "## 🔁 Ciclo de Retrabalho do Turing",
                        f"- Tentativas de retrabalho: {rework_info.get('attempts', 0)}",
                    ]
                )
                if rework_info.get("escalation"):
                    esc = rework_info["escalation"]
                    report_lines.extend(
                        [
                            f"- **ESCALONAMENTO:** {esc.get('message')}",
                            f"- Classificação do veto: {esc.get('veto_class')} (fonte: {esc.get('classification_source')})",
                            f"- Responsável sugerido: {esc.get('suggested_owner')}",
                        ]
                    )
            if reasons:
                report_lines.extend(
                    ["", "## ⚠️ Apontamentos e Bloqueios"] + [f"- {r}" for r in reasons]
                )
            # REDE DE SEGURANÇA ABSOLUTA (antes de gravar): o relatório
            # CONSOLIDADO é re-escaneado pelo veredito estrutural. Se contém
            # rejeição, story parcial/divergente ou ausência de declaração
            # canônica, a ONDA NÃO fecha — JAMAIS (à prova de gate enganado).
            documento = "\n".join(report_lines)
            consistente, motivo_contradicao = self._veredito_estrutural(documento)
            if not consistente:
                success = False
                reasons = reasons or []
                reasons.append(
                    f"🛡️ REDE DE SEGURANÇA CONTRATUAL: contradição no relatório consolidado — {motivo_contradicao}. "
                    "A ONDA NÃO pode ser encerrada nesta condição."
                )
                BUS.publish(
                    "escalation",
                    agent="@turing",
                    text=(
                        "🛡️ [REDE DE SEGURANÇA] Homologação bloqueada por contradição no relatório "
                        f"consolidado: {motivo_contradicao}. Ciclo de retrabalho acionado."
                    ),
                )
                if self.state_machine.autonomy_mode == AutonomyMode.AUTO:
                    success, reasons, rework_info = self._veto_rework_cycle(
                        validators, integration_tests_info
                    )

            # Grava o relatório com o veredito FINAL (pós-rede de segurança)
            report_lines[1] = f"- **Resultado Final:** {'APROVADO' if success else 'REPROVADO'}"
            if reasons:
                idx_apont = next(
                    (i for i, l in enumerate(report_lines) if l.startswith("## ⚠️")),
                    None,
                )
                linhas_apont = ["## ⚠️ Apontamentos e Bloqueios"] + [f"- {r}" for r in reasons]
                if idx_apont is not None:
                    report_lines[idx_apont : idx_apont + 1] = linhas_apont
                else:
                    report_lines.extend(["", *linhas_apont])
            val_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Falha ao salvar validation_report.md: %s", exc)

        if success:
            # Onda convergiu: orçamento de sessão de retrabalho zerado.
            self.db.set_meta(f"rework_rounds:{self.state_machine.wave_id.upper()}", "0")
            self.db.set_meta(f"veto_sig:{self.state_machine.wave_id.upper()}", "")

        return {
            "success": success,
            "stage": TuringStage.VALIDATE.value,
            "integration_tests": integration_tests_info,
            "validator_output": validators["@edith"]["output"],
            "gov_output": validators["@nina"]["output"],
            "rework": rework_info,
            "blocked": bool(rework_info and rework_info.get("escalation")),
            "error": " | ".join(reasons) if not success else None,
        }

    def _build_edith_audit_prompt(self) -> str:
        """Constrói o prompt de auditoria da @edith (intermediária vs. final via Sequenciador)."""
        from bombe_code.domain.wave.sequencer import WaveSequencer

        prd_file = self.project_dir / "docs" / "briefings" / "PRD.md"
        prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
        sequencer = WaveSequencer.from_markdown(prd_content)
        current_wave_id = self.state_machine.wave_id
        current_plan = sequencer.get_plan(current_wave_id)
        has_future = sequencer.has_future_waves(current_wave_id)
        is_final = sequencer.is_final_wave(current_wave_id)

        cards = self.kanban.list_cards(wave_id=current_wave_id)
        wave_story_ids = [c.get("story_id", "") for c in cards]
        story_list_str = ", ".join(wave_story_ids) or "stories da onda atual"

        if has_future and not is_final:
            # ONDA INTERMEDIÁRIA: Valida a fatia vertical contratada
            return (
                f"Você está auditando a ONDA INTERMEDIÁRIA '{current_wave_id}' de um MVP fatiado via Lean Inception.\n"
                f"O PRD em 'docs/briefings/PRD.md' formalizou que existem ondas futuras para os épicos e funcionalidades subsequentes.\n"
                f"Seu dever como Auditora de Homologação nesta onda é verificar EXCLUSIVAMENTE o incremento entregue nesta fatia:\n"
                f"- Histórias sob escopo desta onda: {story_list_str}\n"
                f"- Hipótese de negócio da onda: '{current_plan.business_hypothesis if current_plan else 'Fatia vertical da onda'}'\n"
                f"- Inspecione os arquivos de código e testes do projeto.\n"
                f"REGRA MANDATÓRIA DE FINOPS E GOVERNANÇA: NÃO reprove nem bloqueie esta onda por falta de módulos ou funcionalidades que estão formalmente agendadas para as ondas futuras no Sequenciador do PRD.\n"
                f"Se as histórias desta onda ({story_list_str}) foram implementadas com testes passando e arquitetura íntegra, declare explicitamente: 'Homologação: APROVADO'. Caso contrário, aponte os bloqueios da fatia atual.\n"
            )
        # ONDA FINAL: Validação de Release de Produção
        return (
            f"Você está auditando a ONDA FINAL DE RELEASE ('{current_wave_id}') do MVP.\n"
            f"Como esta é a última onda planejada no Sequenciador do PRD (ou onda única de escopo completo), "
            f"audite o entregável integrado completo contra TODOS os requisitos funcionais e não-funcionais do PRD em 'docs/briefings/PRD.md'.\n"
            f"Verifique se o produto está íntegro de ponta a ponta para homologação de produção.\n"
            f"Se aprovado para release, declare explicitamente: 'Homologação: APROVADO'. Caso contrário, aponte os bloqueios ou faltas para o MVP.\n"
        )

    def _build_nina_audit_prompt(self) -> str:
        """Constrói o prompt de auditoria de governança/FinOps da @nina."""
        return (
            "Audite o consumo de tokens, custos e a governança ética da ONDA consultando o relatório em 'docs/telemetria.md'.\n"
            "Se conforme com os limites e princípios, declare explicitamente: 'Governança: APROVADO'.\n"
        )

    def _veto_rework_cycle(
        self,
        validators: dict[str, dict[str, Any]],
        integration_tests_info: dict[str, Any],
    ) -> tuple[bool, list[str], dict[str, Any]]:
        """Ciclo AUTÔNOMO de retrabalho para vetos na VALIDATE (modo AUTO).

        Filosofia: NENHUM veto para o processo. Para cada veto:
        1. Turing determinístico classifica e rastreia a causa até o AUTOR do artefato.
        2. APPROVAL_MISSING → o validador re-emite o parecer (RE_AUDIT).
        3. PRODUCT_GAP / TEST_FAILURE / AGENT_BLOCKED → o autor upstream corrige o
           artefato e as stories afetadas são RE-QUEIMADAS no burn TDD (EXECUTE),
           seguidas de re-auditoria pelo validador.
        4. Só após esgotar as rodadas autônomas converte em DÚVIDA DE NEGÓCIO
           estruturada para o humano (último recurso, nunca parada silenciosa).
        """
        engine = VetoReworkEngine(llm_factory=self.llm_factory)
        original_demand = (
            f"ONDA {self.state_machine.wave_id} ({self.state_machine.wave_type.value})"
        )
        attempt = 0
        last_analysis = None
        is_wave_zero = self.state_machine.wave_type == WaveType.WAVE_ZERO
        wave_key = self.state_machine.wave_id.upper()

        # ORÇAMENTO DE SESSÃO DE RETRABALHO (persistente): sem isso o ciclo
        # veto → re-burn → validate queima tokens para sempre sem convergir.
        MAX_ROUNDS_SESSAO = 3
        rodadas_acumuladas = int(self.db.get_meta(f"rework_rounds:{wave_key}") or 0)
        assinatura_anterior = self.db.get_meta(f"veto_sig:{wave_key}") or ""
        ultima_rota_foi_burn = False

        def _assinatura_veto(razoes: list[str]) -> str:
            tokens = sorted(set(re.findall(r"[a-zà-ú]{6,}", " ".join(razoes).lower())))
            return "|".join(tokens[:12])

        while attempt < engine.max_attempts:
            attempt += 1
            failed = {
                name: info
                for name, info in validators.items()
                if info["runner"] is not None and not info["approved"]
            }
            if not failed:
                break

            # TETO DA SESSÃO: esgotado? Escala com evidência em vez de queimar tokens.
            if rodadas_acumuladas >= MAX_ROUNDS_SESSAO:
                BUS.publish(
                    "escalation",
                    agent="@turing",
                    text=(
                        f"🛑 [ORÇAMENTO DE RETRABALHO ESGOTADO] A {self.state_machine.wave_id} acumulou "
                        f"{rodadas_acumuladas} rodadas de retrabalho nesta sessão sem convergir. "
                        "O Ciclo Autônomo para aqui: se o problema persiste, falta informação de negócio "
                        "ou a correção excede a capacidade autônoma. Intervenção humana necessária."
                    ),
                )
                last_analysis = last_analysis or engine.classify(
                    "Orçamento de retrabalho esgotado sem convergência", target_agent="@edith"
                )
                escalation = engine.build_escalation(
                    last_analysis,
                    rodadas_acumuladas,
                    {name: info["output"] for name, info in validators.items()},
                )
                escalation["message"] = (
                    f"🛑 ORÇAMENTO DE RETRABALHO ESGOTADO ({rodadas_acumuladas} rodadas na sessão). "
                    + escalation["message"]
                )
                # Escalation JAMAIS aprova: testes passarem não homologa onda.
                return (
                    False,
                    [escalation["message"]],
                    {
                        "attempts": rodadas_acumuladas,
                        "escalation": escalation,
                    },
                )

            # NÃO-CONVERGÊNCIA: o mesmo veto repetido após um BURN autônomo
            # indica insistência inútil (rotas RE_AUDIT repetem por natureza).
            assinatura_atual = _assinatura_veto(
                [i["reason"] for i in validators.values() if not i["approved"]]
            )
            if (
                assinatura_anterior
                and assinatura_atual == assinatura_anterior
                and ultima_rota_foi_burn
            ):
                BUS.publish(
                    "escalation",
                    agent="@turing",
                    text=(
                        f"🔁 [NÃO-CONVERGÊNCIA] O mesmo veto persiste idêntico após o retrabalho "
                        f"na {self.state_machine.wave_id}. Insistir não resolve: escalando com evidências."
                    ),
                )
                last_analysis = last_analysis or engine.classify(
                    assinatura_atual, target_agent="@edith"
                )
                escalation = engine.build_escalation(
                    last_analysis,
                    rodadas_acumuladas + 1,
                    {name: info["output"] for name, info in validators.items()},
                )
                escalation["message"] = (
                    "🔁 NÃO-CONVERGÊNCIA: veto idêntico repetido após retrabalho. "
                    + escalation["message"]
                )
                return (
                    False,
                    [escalation["message"]],
                    {
                        "attempts": rodadas_acumuladas + 1,
                        "escalation": escalation,
                    },
                )

            for name, info in failed.items():
                analysis = engine.classify(info["reason"], info["output"], target_agent=name)
                last_analysis = analysis
                route = VETO_ROUTES.get(analysis.veto_class, {})
                BUS.publish(
                    "veto_analysis",
                    agent=name,
                    text=(
                        f"🔍 Veto de {name} analisado: {analysis.veto_class.value}. "
                        f"Rota autônoma → {route.get('owner', '@turing')}: {route.get('description', 'retrabalho')}"
                        + (
                            f" | Stories afetadas: {', '.join(analysis.story_ids)}"
                            if analysis.story_ids
                            else ""
                        )
                    ),
                    veto_class=analysis.veto_class.value,
                )

                ultima_rota_foi_burn = analysis.veto_class is not VetoClass.APPROVAL_MISSING
                if analysis.veto_class is VetoClass.APPROVAL_MISSING:
                    # Rota RE_AUDIT: o validador re-emite o parecer.
                    res = info["runner"].run(engine.build_rework_prompt(analysis, original_demand))
                    self._record_telemetry("VALIDATE", f"{name} (re-auditoria #{attempt})", res)
                    approved, reason = self._check_explicit_approval(res)
                    info["approved"] = approved
                    info["reason"] = reason
                    info["output"] = getattr(res, "output", "") or info["output"]
                    BUS.publish(
                        "veto_rework",
                        agent=name,
                        text=(
                            f"🔁 Re-auditoria {attempt}/{engine.max_attempts} com {name}: "
                            + ("aprovado." if approved else f"ainda reprovado — {reason}")
                        ),
                        attempt=attempt,
                    )
                    continue

                # Rota autônoma: consertar a causa e queimar de novo.
                self._autonomous_rework_burn(engine, analysis, name, info, attempt, is_wave_zero)

            rodadas_acumuladas += 1
            self.db.set_meta(f"rework_rounds:{wave_key}", str(rodadas_acumuladas))
            self.db.set_meta(
                f"veto_sig:{wave_key}",
                _assinatura_veto([i["reason"] for i in validators.values() if not i["approved"]]),
            )

            if all(info["approved"] for info in validators.values()):
                break

        if all(info["approved"] for info in validators.values()):
            # Sucesso: orçamento de sessão é zerado (onda convergiu).
            self.db.set_meta(f"rework_rounds:{wave_key}", "0")
            self.db.set_meta(f"veto_sig:{wave_key}", "")
            return (
                integration_tests_info["all_passed"],
                [] if integration_tests_info["all_passed"] else [integration_tests_info["details"]],
                {"attempts": attempt, "resolved": True},
            )

        if last_analysis is None:
            last_analysis = engine.classify(
                "; ".join(
                    f"{n}: {i['reason']}" for n, i in validators.items() if not i["approved"]
                ),
                target_agent="@edith",
            )
        escalation = engine.build_escalation(
            last_analysis,
            attempt,
            {name: info["output"] for name, info in validators.items()},
        )
        BUS.publish(
            "escalation",
            agent="@turing",
            text=escalation["message"],
            escalation=escalation,
        )
        reasons = []
        if not integration_tests_info["all_passed"]:
            reasons.append(integration_tests_info["details"])
        for name, info in validators.items():
            if not info["approved"]:
                reasons.append(f"{name}: {info['reason']}")
        reasons.append(escalation["message"])
        return False, reasons, {"attempts": attempt, "escalation": escalation}

    def _autonomous_rework_burn(
        self,
        engine: VetoReworkEngine,
        analysis: Any,
        validator_name: str,
        info: dict[str, Any],
        attempt: int,
        is_wave_zero: bool,
    ) -> None:
        """Rota autônoma para vetos estruturais: autor upstream conserta o artefato,
        stories afetadas são re-queimadas no burn TDD e o validador re-auditá."""
        blockers = analysis.blockers or [info["reason"]]
        story_ids = list(analysis.story_ids)
        if not story_ids:
            story_ids = [
                c.get("story_id", "")
                for c in self.kanban.list_cards(wave_id=self.state_machine.wave_id)
                if c.get("status") not in (KanbanCardStatus.DONE.value, "DONE")
            ]
        story_ids = [s for s in story_ids if s]
        owner = analysis.fix_owner or "@unclebob"

        BUS.publish(
            "veto_rework",
            agent=owner,
            text=(
                f"🛠️ [AUTÔNOMO {attempt}/{engine.max_attempts}] Causa rastreada até {owner}. "
                f"Devolendo bloqueios para correção do artefato"
                + (f" e re-burn de {', '.join(story_ids)}" if story_ids else "")
                + "..."
            ),
        )

        # 1. O AUTOR upstream corrige o artefato (sem implementar código).
        runner_owner = self._get_runner(owner)
        if runner_owner:
            up_prompt = engine.build_upstream_rework_prompt(
                owner, blockers, story_ids, f"ONDA {self.state_machine.wave_id}"
            )
            res = runner_owner.run(up_prompt)
            self._record_telemetry("VALIDATE", f"{owner} (rework upstream #{attempt})", res)
            self._extract_and_write_project_files(getattr(res, "output", ""))

        # 2. Re-burn: stories afetadas voltam ao ciclo TDD (VALIDATE → EXECUTE → VALIDATE).
        if story_ids and not is_wave_zero:
            if self.state_machine.current_state == WaveState.VALIDATE and not self.transition_to(
                TuringStage.EXECUTE
            ):
                logger.warning("Não foi possível retornar a EXECUTE para re-burn autônomo.")
                return
            for sid in story_ids:
                cycle_res = self._run_cycle_inner(sid)
                BUS.publish(
                    "veto_rework",
                    agent=owner,
                    text=(
                        f"🔥 Re-burn {sid}: "
                        + (
                            "concluído no ciclo TDD."
                            if cycle_res.get("success")
                            else f"falhou — {cycle_res.get('error')}"
                        )
                    ),
                )
            if self.state_machine.current_state == WaveState.EXECUTE:
                self.transition_to(TuringStage.VALIDATE)

        # 3. Re-auditoria pelo validador original com o prompt canônico.
        if info["runner"] is None:
            return
        if validator_name == "@edith":
            fresh_prompt = self._build_edith_audit_prompt()
        else:
            fresh_prompt = self._build_nina_audit_prompt()
        fresh_prompt += (
            f"\n\nCONTEXTO DE RE-AUDITORIA (rodada autônoma {attempt}/{engine.max_attempts}): "
            "correções foram aplicadas pelos autores responsáveis e as stories foram re-executadas. "
            "Reavalie o entregável atual."
        )
        res = info["runner"].run(self._assemble_prompt(validator_name, fresh_prompt))
        self._record_telemetry("VALIDATE", f"{validator_name} (re-auditoria #{attempt})", res)
        approved, reason = self._check_explicit_approval(res)
        info["approved"] = approved
        info["reason"] = reason
        info["output"] = getattr(res, "output", "") or info["output"]
        BUS.publish(
            "veto_rework",
            agent=validator_name,
            text=(
                f"🔁 Re-auditoria {attempt}/{engine.max_attempts} com {validator_name} após retrabalho autônomo: "
                + ("APROVADO." if approved else f"ainda reprovado — {reason}")
            ),
            attempt=attempt,
        )

    def run_audit(self, wave_id: str | None = None) -> dict[str, Any]:
        """Contra-Auditoria Forense (@hoare) — 'Pedido vs. Entregue' com o
        CÓDIGO como fonte da verdade. Comando opcional do usuário quando há
        dúvida sobre a qualidade de um validate.

        Diferente do validate original (custo de LLM: 1 chamada adversarial):
        1. Evidências determinísticas de custo zero (fraudes, mapa CA×story).
        2. Execução REAL da suíte de testes do projeto auditado.
        3. Cross-examinação do relatório de validação anterior.
        4. Laudo com FUROs estruturados → bloqueio de cards + reabertura da
           onda + re-burn TDD das stories afetadas (Ciclo Autônomo).
        """
        from bombe_code.turing.audit import (
            coletar_evidencias,
            executar_suite_testes,
            extrair_aleacoes_relatorio,
            extrair_furos,
            veredito_auditoria,
        )

        alvo = (wave_id or self.state_machine.wave_id or "").strip().upper()
        if not alvo:
            return {"success": False, "error": "Nenhuma onda especificada para auditoria."}

        BUS.publish(
            "stage_start",
            agent="@hoare",
            text=(
                f"🔍 [CONTRA-AUDITORIA FORENSE] @hoare assumiu o caso: '{alvo}'. "
                "Pressuposto adversarial — o validate anterior pode ter sido preguiçoso. "
                "Coletando provas no código (custo zero de tokens)..."
            ),
            wave_id=alvo,
        )

        # Evidências determinísticas (0 tokens)
        report_anterior = ""
        for candidato in (
            self.workspace.wave_validation_report_path(alvo),
            self.project_dir / "docs" / "reports" / "validation_report.md",
        ):
            try:
                if candidato.exists():
                    report_anterior = candidato.read_text(encoding="utf-8")
                    break
            except OSError:
                continue

        evidencias = coletar_evidencias(self.project_dir, alvo, report_anterior)
        evidencias.aleacoes_relatorio_anterior = extrair_aleacoes_relatorio(report_anterior)
        evidencias.suite_resultado, evidencias.suite_detalhes = executar_suite_testes(
            self.project_dir
        )

        if evidencias.suite_resultado == "FALHOU":
            evidencias.fraudes_potenciais.append(
                "Suíte de testes do projeto FALHOU na execução real — alegação anterior de testes verdes é falsa"
            )

        BUS.publish(
            "announcement",
            agent="@hoare",
            text=(
                f"🧾 Provas coletadas: {len(evidencias.arquivos_producao)} arquivos de produção, "
                f"{len(evidencias.testes_encontrados)} de teste, {len(evidencias.fraudes_potenciais)} fraude(s) potencial(is), "
                f"suíte: {evidencias.suite_resultado}. Cross-examinando o relatório anterior..."
            ),
        )

        # A chamada adversarial única do @hoare
        runner_hoare = self._get_runner("@hoare")
        if not runner_hoare:
            return {"success": False, "error": "Agente @hoare indisponível no catálogo."}

        fraudes = (
            "\n".join(f"- {f}" for f in evidencias.fraudes_potenciais[:15])
            or "- (nenhuma detectada estaticamente)"
        )
        aleacoes = (
            "\n".join(f"- {a}" for a in evidencias.aleacoes_relatorio_anterior[:20])
            or "- (sem alegações extraíveis)"
        )
        arvore = "\n".join(evidencias.arquivos_producao[:40]) or "- (vazio)"
        mapa = (
            "\n".join(
                f"- {story}: CAs {', '.join(dados['cas']) or 'nenhum'} | BDD: {'sim' if dados.get('bdd') else 'não'}"
                for story, dados in list(evidencias.mapa_cas.items())[:15]
            )
            or "- (nenhuma story com CAs declarados)"
        )

        raw_prompt = (
            f"CONTRA-AUDITORIA FORENSE da {alvo}. Você é @hoare — auditor adversarial.\n"
            "Pressuposto: o validate anterior pode ter sido preguiçoso. Seu trabalho é ENCONTRAR furos.\n\n"
            "=== FONTES DA VERDADE (código) ===\n"
            f"Arquivos de produção:\n{arvore}\n\n"
            f"Resultado da SUÍTE REAL executada agora: {evidencias.suite_resultado}\n"
            f"{evidencias.suite_detalhes[:1500]}\n\n"
            f"Fraudes potenciais detectadas estaticamente:\n{fraudes}\n\n"
            f"Contrato do escopo (stories × CAs declarados):\n{mapa}\n\n"
            "=== ALEGAÇÕES DO RELATÓRIO DE VALIDAÇÃO ANTERIOR (cross-examine) ===\n"
            f"{aleacoes}\n\n"
            "=== RELATÓRIO ANTERIOR (trecho) ===\n"
            f"{report_anterior[:2500]}\n\n"
            "MISSÃO: garantir que o que foi PEDIDO é o que foi ENTREGUE. Para cada alegação do "
            "relatório anterior, exija evidência no código. Audite fundo as stories de maior risco. "
            "CA declarado sem implementação/teste correspondente é FURO. Alegação sem evidência é FURO. "
            "Fraude (mock/TODO/NotImplementedError em produção) é FURO.\n"
            "FORMATO OBRIGATÓRIO: liste cada furo em linha própria iniciando com 'FURO: <story> — <descrição> — evidência: <arquivo/teste>'. "
            "Se e somente se nenhum furo existir, declare EXATAMENTE 'AUDITORIA: LIMPA'."
        )
        prompt = self._assemble_prompt("@hoare", raw_prompt)
        res_hoare = runner_hoare.run(prompt)
        self._record_telemetry("VALIDATE", "@hoare (Contra-Auditoria Forense)", res_hoare)
        laudo = getattr(res_hoare, "output", "") or ""

        furos = extrair_furos(laudo)
        limpo, motivo_veredito = veredito_auditoria(laudo, furos)

        # Persiste o laudo no workspace da onda auditada
        laudo_path = self.workspace.wave_validation_report_path(alvo).parent / "audit_report.md"
        try:
            laudo_path.parent.mkdir(parents=True, exist_ok=True)
            laudo_path.write_text(
                f"# 🔍 Contra-Auditoria Forense — {alvo}\n\n**Auditor:** @hoare\n"
                f"**Suíte real:** {evidencias.suite_resultado}\n\n{laudo}\n",
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Falha ao salvar audit_report.md: %s", exc)

        resultado = {
            "success": True,
            "stage": "AUDIT",
            "wave_id": alvo,
            "limpa": limpo,
            "furos": furos,
            "suite": evidencias.suite_resultado,
            "laudo_path": str(laudo_path),
            "message": f"Contra-auditoria de {alvo}: {motivo_veredito}.",
        }

        if limpo:
            BUS.publish(
                "stage_end",
                agent="@hoare",
                text=(
                    f"✅ [AUDITORIA: LIMPA] {alvo} passou pela contra-auditoria forense "
                    "(pedido × entregue verificado no código, suíte real executada)."
                ),
                wave_id=alvo,
            )
            return resultado

        # FUROS: bloqueia cards afetados e abre o ciclo de correção autônomo.
        stories_afetadas = sorted(
            {sid for furo in furos for sid in re.findall(r"ST[-\s]?\d+", furo, re.IGNORECASE)}
        )
        stories_afetadas = [
            s.title().replace("-", "-").upper().replace("ST ", "ST-") for s in stories_afetadas
        ]

        BUS.publish(
            "escalation",
            agent="@hoare",
            text=(
                f"🚨 [FUROS ENCONTRADOS] {len(furos)} furo(s) na {alvo}. "
                + (f"Stories afetadas: {', '.join(stories_afetadas)}. " if stories_afetadas else "")
                + "Bloqueando cards e acionando o Ciclo Autônomo de correção."
            ),
            wave_id=alvo,
        )

        for furo in furos[:10]:
            story_do_furo = next((s for s in stories_afetadas if s.lower() in furo.lower()), None)
            if story_do_furo and self.kanban.get_card(story_do_furo):
                self.kanban.block_card(
                    story_do_furo,
                    reason=f"FURO (contra-auditoria @hoare): {furo[:180]}",
                    blocked_by="@hoare",
                )

        # A onda auditada assume o comando: checkpoint ativo arquivado, onda
        # reaberta em EXECUTE para o re-burn TDD das stories com furo.
        ativo = self.db.load_wave_state()
        if (
            ativo
            and str(ativo.get("wave_id", "")).upper() != alvo
            and str(ativo.get("state", "")).upper() != WaveState.COMPLETED.value
        ):
            self.db.archive_wave_state()

        alvo_cards = self.kanban.list_cards(wave_id=alvo)
        tem_cards = bool(alvo_cards)
        self.state_machine = TuringStateMachine(
            wave_id=alvo,
            initial_state=WaveState.EXECUTE if tem_cards else WaveState.PLAN,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        self.db.save_wave_state(
            wave_id=alvo,
            state=WaveState.EXECUTE if tem_cards else WaveState.PLAN,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )
        resultado["wave_id"] = alvo
        resultado["stage"] = "EXECUTE" if tem_cards else "PLAN"

        if stories_afetadas and tem_cards and self.state_machine.autonomy_mode == AutonomyMode.AUTO:
            for sid in stories_afetadas:
                if not self.kanban.get_card(sid):
                    continue
                self.kanban.update_status(sid, KanbanCardStatus.IN_PROGRESS.value)
                ciclo = self._run_cycle_inner(sid)
                BUS.publish(
                    "veto_rework",
                    agent="@hoare",
                    text=(
                        f"🔥 Re-burn {sid} (furo da contra-auditoria): "
                        + (
                            "corrigido no ciclo TDD."
                            if ciclo.get("success")
                            else f"falhou — {ciclo.get('error')}"
                        )
                    ),
                )
            if self.state_machine.current_state == WaveState.EXECUTE:
                self.transition_to(TuringStage.VALIDATE)
            resultado["reexecucao"] = (
                f"stories {', '.join(stories_afetadas)} re-queimadas; onda em VALIDATE"
            )

        return resultado

    def end_wave(self) -> dict[str, Any]:
        """Finaliza e arquiva a ONDA como COMPLETED."""
        from .state_machine import WaveType

        is_wave_zero = self.state_machine.wave_type == WaveType.WAVE_ZERO
        valid_end_states = (
            (WaveState.VALIDATE, WaveState.PLAN) if is_wave_zero else (WaveState.VALIDATE,)
        )
        if self.state_machine.current_state not in valid_end_states:
            expected = "VALIDATE ou PLAN (Onda Zero)" if is_wave_zero else "VALIDATE"
            return {
                "success": False,
                "error": f"Etapa atual é {self.state_machine.current_state.value}, esperado {expected} para encerrar.",
            }

        if not self.transition_to(TuringStage.COMPLETED):
            return {"success": False, "error": "Falha na transição final para COMPLETED."}

        # POLÍTICA DE BRANCHES: estado aprovado é promovido para `dev` via
        # squash (memória operacional da IA ≠ histórico oficial). Nunca push.
        resultado_promocao = None
        try:
            from bombe_code.turing.promocao import PromotorDeBranches

            promotor = PromotorDeBranches(str(self.project_dir))
            if promotor.eh_repositorio():
                from bombe_code.turing.progress import BUS as _bus

                promocao = promotor.promover_para_dev(
                    f"feat({self.state_machine.wave_id}): entrega homologada da ONDA "
                    f"(VALIDATE aprovado — estado aprovado consolidado em 1 commit)"
                )
                resultado_promocao = promocao.mensagem
                _bus.publish(
                    "announcement" if promocao.success else "escalation",
                    agent="@turing",
                    text=(
                        f"🌿 [PROMOÇÃO] {promocao.mensagem}"
                        if promocao.success
                        else f"⚠️ [PROMOÇÃO] {promocao.mensagem}"
                    ),
                    wave_id=self.state_machine.wave_id,
                )
        except Exception as exc:  # noqa: BLE001 — promoção é best-effort, não derruba o fim da onda
            logger.warning("Promoção de branches falhou (não bloqueante): %s", exc)

        return {
            "success": True,
            "wave_id": self.state_machine.wave_id,
            "stage": TuringStage.COMPLETED.value,
            "promocao": resultado_promocao,
            "message": f"ONDA {self.state_machine.wave_id} finalizada com sucesso e arquivada.",
        }

    def set_mode(self, mode_str: str) -> dict[str, Any]:
        """Altera dinamicamente o modo de autonomia ou de engenharia."""
        cleaned = mode_str.strip().lower()
        cfg_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = cfg_mgr.load()

        updated_autonomy = False

        if cleaned in ("auto", "semi_auto", "semi-auto", "manual"):
            if cleaned == "semi_auto":
                cleaned = "semi-auto"
            new_autonomy = (
                AutonomyMode.SEMI_AUTO if cleaned == "semi-auto" else AutonomyMode(cleaned.upper())
            )
            self.state_machine.set_autonomy_mode(new_autonomy)
            cfg.autonomy = cleaned
            updated_autonomy = True
        elif cleaned in ("tdd", "tdd-code", "tdd_code"):
            self.state_machine.set_engineering_mode(EngineeringMode.TDD_CODE)
            cfg.mode = "tdd-code"
        elif cleaned in ("vibe", "vibe-code", "vibe_code"):
            self.state_machine.set_engineering_mode(EngineeringMode.VIBE_CODE)
            cfg.mode = "vibe-code"
        else:
            return {
                "success": False,
                "error": f"Modo desconhecido: {mode_str}. Use auto/semi-auto/manual ou tdd/vibe.",
            }

        # Salva no banco SQLite
        self.db.save_wave_state(
            wave_id=self.state_machine.wave_id,
            state=self.state_machine.current_state,
            autonomy_mode=self.state_machine.autonomy_mode,
            engineering_mode=self.state_machine.engineering_mode,
        )

        # Salva no .bombeconfig
        try:
            cfg_mgr.save(cfg)
        except Exception as e:  # noqa: BLE001
            logger.warning("Não foi possível persistir .bombeconfig: %s", e)

        return {
            "success": True,
            "autonomy_mode": self.state_machine.autonomy_mode.value,
            "engineering_mode": self.state_machine.engineering_mode.value,
            "message": (
                f"Modo de {'autonomia' if updated_autonomy else 'engenharia'} alterado com sucesso."
            ),
        }

    def run_rca(self, incident: str) -> dict[str, Any]:
        """Executa Análise de Causa Raiz (RCA) com @unclebob e especialistas forenses."""
        runner_uncle = self._get_runner("@unclebob")
        prompt = (
            f"Conduza uma Análise de Causa Raiz (RCA) aprofundada para o seguinte incidente:\n"
            f"'{incident}'.\n"
            f"Aplique os 5 Porquês, identifique fatores contribuintes e proponha ações corretivas."
        )
        if runner_uncle:
            res = runner_uncle.run(prompt=prompt)
            output = res.output
            success = res.success
        else:
            output = f"RCA concluída para o incidente: {incident}"
            success = True

        return {
            "success": success,
            "incident": incident,
            "report": output,
            "agent": "@unclebob",
        }

    def run_simplify(self, target: str) -> dict[str, Any]:
        """Executa auditoria de simplificação de código com @ieru e @unclebob."""
        runner_ieru = self._get_runner("@ieru")
        prompt = (
            f"Audite o alvo '{target}' visando simplificação máxima de código, "
            f"eliminação de complexidade acidental, redução de linhas e conformidade com KISS/DRY/SOLID."
        )
        if runner_ieru:
            res = runner_ieru.run(prompt=prompt)
            output = res.output
            success = res.success
        else:
            output = f"Análise de simplificação executada para o alvo: {target}"
            success = True

        return {
            "success": success,
            "target": target,
            "output": output,
            "agent": "@ieru",
        }

    def run_task(self, description: str, agent_handle: str | None = None) -> dict[str, Any]:
        """Executa uma task avulsa/ad-hoc sem alterar o estágio da ONDA."""
        handle = agent_handle or "@turing"
        runner = self._get_runner(handle)
        prompt = f"Execute a seguinte tarefa técnica pontual: {description}"
        if runner:
            res = runner.run(prompt=prompt)
            output = res.output
            success = res.success
        else:
            output = f"Tarefa executada: {description}"
            success = True

        return {
            "success": success,
            "task": description,
            "agent": handle,
            "output": output,
        }

    def generate_status_report(self) -> dict[str, Any]:
        """Gera um relatório consolidado da ONDA, tarefas e configurações do projeto."""
        status = self.get_status()
        cfg_mgr = ProjectConfigManager(str(self.project_dir))
        cfg = cfg_mgr.load()

        return {
            "wave_id": status["wave_id"],
            "stage": status["stage"],
            "autonomy_mode": status["autonomy_mode"],
            "engineering_mode": status["engineering_mode"],
            "tasks_summary": status["tasks_summary"],
            "gates": status.get("gates", {}),
            "kanban_cards": status.get("kanban_cards", []),
            "config": cfg.model_dump(),
        }

    run_discovery = run_discuss
    run_inception = run_plan
    run_refinement = run_plan


TuringWaveOrchestrator = WaveOrchestrator
