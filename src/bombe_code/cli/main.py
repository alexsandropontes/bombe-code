"""Entrypoint da CLI Bombe Code construída com Typer."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
import uvicorn

from .. import __version__
from ..config.paths import get_paths
from ..permissions.rules import PermissionService, Rule
from ..providers.models_dev import get_models
from ..server.app import create_app
from ..session import crud
from ..session.loop import run_prompt
from ..tools.registry import ToolRegistry, builtin_registry, load_custom_tools


def create_default_registry(project_dir: str = ".") -> ToolRegistry:
    reg = builtin_registry()
    load_custom_tools(reg, project_dir)
    return reg


class ServerThread:
    """Invólucro para o servidor uvicorn in-process."""

    def __init__(self, server: uvicorn.Server, thread: threading.Thread):
        self.server = server
        self.thread = thread

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5.0)


from ..providers.resolver import resolve_provider_adapter

resolve_default_adapter = resolve_provider_adapter


def start_server_in_process(
    host: str = "127.0.0.1",
    port: int = 0,
    project_dir: str = ".",
    adapter: Any = None,
) -> tuple[ServerThread, int, str]:
    """Inicia servidor uvicorn em thread secundária para uso in-process."""
    if adapter is None:
        adapter = resolve_default_adapter()

    permissions = PermissionService(
        rules=[Rule(permission="*", pattern="*", action="allow")],
        approved=[],
    )
    app_instance = create_app(
        adapter=adapter,
        permissions=permissions,
        project_dir=project_dir,
    )

    config = uvicorn.Config(app_instance, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 15.0
    bound_port = None
    while time.time() < deadline:
        if getattr(server, "servers", None):
            bound_port = server.servers[0].sockets[0].getsockname()[1]
            break
        time.sleep(0.05)

    if bound_port is None:
        raise RuntimeError("Servidor uvicorn in-process não iniciou a tempo.")

    auth_path = get_paths().state / "server-auth"
    password = auth_path.read_text(encoding="utf-8").strip() if auth_path.is_file() else ""
    return ServerThread(server, thread), bound_port, password


app = typer.Typer(
    name="bombe-code",
    help="Bombe Code — Agente de código autônomo com ciclo vibe.",
    no_args_is_help=False,
)

wave_cli = typer.Typer(name="wave", help="Comandos de orquestração do ciclo da ONDA.")
app.add_typer(wave_cli, name="wave")


@wave_cli.command("start")
def wave_start(
    wave_id: Annotated[
        str | None, typer.Argument(help="Identificador da ONDA (ex: ONDA-001)")
    ] = None,
    mode: Annotated[
        str, typer.Option("--mode", "-m", help="Modo de autonomia (auto, semi-auto, manual)")
    ] = "auto",
    target: Annotated[
        str,
        typer.Option(
            "--target",
            "-t",
            help="Nível de maturidade/objetivo da entrega (snippet, poc, prototype, mvp, production, enterprise)",
        ),
    ] = "mvp",
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Inicializa uma nova ONDA."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    target_wave = wave_id
    if not target_wave:
        saved = orch.db.load_wave_state()
        if saved and saved.get("wave_id"):
            target_wave = str(saved["wave_id"])
        else:
            target_wave = "ONDA-001"
    res = orch.start_wave(target_wave, delivery_target=target)
    if mode:
        orch.set_mode(mode)
    typer.echo(res["message"])


@wave_cli.command("run")
def wave_run(
    topic: Annotated[
        str | None, typer.Option("--topic", "-t", help="Demanda/tópico de produto")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa o pipeline completo da ONDA ativa de acordo com seu modo de autonomia."""
    from bombe_code.domain.wave.sequencer import WaveSequencer
    from bombe_code.turing.orchestrator import WaveOrchestrator
    from bombe_code.turing.state_machine import WaveType

    while True:
        orch = WaveOrchestrator(project_dir=project_dir)
        st = orch.get_status()
        is_wave_zero = orch.state_machine.wave_type == WaveType.WAVE_ZERO
        typer.echo(
            f"\n🚀 [TURING AUTO] Executando ONDA {st['wave_id']} (Modo: {st['autonomy_mode']} | Etapa: {st['stage']})..."
        )

        # 1. DISCOVERY / DISCUSS
        if st["stage"] in ("DISCOVERY", "DISCUSS"):
            final_topic = topic
            if not final_topic:
                # Checa se existe briefing humano prévio em docs/briefings/
                briefing_dir = Path(project_dir) / "docs" / "briefings"
                human_briefings = list(briefing_dir.glob("*.md")) if briefing_dir.exists() else []
                human_briefings = [
                    b for b in human_briefings if b.name not in ("VIABILITY.md", "PRD.md")
                ]
                if human_briefings:
                    final_topic = human_briefings[0].read_text(encoding="utf-8")
                else:
                    prd_file = Path(project_dir) / "docs" / "briefings" / "PRD.md"
                    if prd_file.exists():
                        final_topic = "Execução baseada no PRD existente"
                    else:
                        typer.echo(
                            "⚠️ Nenhum tópico informado e nenhum briefing prévio encontrado em docs/briefings/.\n"
                            "Para iniciar a execução, informe a missão usando:\n"
                            '  bombe-code wave run --topic "Descreva sua ideia aqui"',
                            err=True,
                        )
                        raise typer.Exit(code=1)

            typer.echo(f"📋 Executando DISCOVERY para: {final_topic[:80]}...")
            res_disc = orch.run_discovery(final_topic)
            if not res_disc.get("success"):
                typer.echo(f"❌ Falha em DISCOVERY: {res_disc.get('error')}", err=True)
                return
            typer.echo("✅ DISCOVERY concluído com sucesso e PRD gerado.")
            if st.get("autonomy_mode", "").upper().replace("-", "_") == "MANUAL":
                typer.echo(
                    "⏸ Etapa DISCOVERY concluída (modo MANUAL). Continua com: bombe-code wave run"
                )
                return

        # 2. INCEPTION / PLAN
        st = orch.get_status()
        if st["stage"] in ("DISCOVERY", "DISCUSS", "INCEPTION", "PLAN"):
            stage_to_run = "INCEPTION" if is_wave_zero else "PLAN"
            typer.echo(f"📐 Executando {stage_to_run} e arquitetura de upstream...")
            res_plan = orch.run_inception() if is_wave_zero else orch.run_plan()
            if not res_plan.get("success"):
                typer.echo(f"❌ Falha em {stage_to_run}: {res_plan.get('error')}", err=True)
                return
            typer.echo(f"✅ {stage_to_run} concluído.")
            if st.get("autonomy_mode", "").upper().replace("-", "_") == "MANUAL":
                typer.echo(
                    "⏸ Etapa PLAN concluída (modo MANUAL). Continua com: bombe-code wave run"
                )
                return

        # Na Onda Zero, concluímos aqui e passamos para a Onda 1
        if is_wave_zero:
            res_end = orch.end_wave()
            typer.echo(f"🎉 Onda Zero concluída: {res_end.get('message', 'Upstream OK')}")
            if st["autonomy_mode"] == "AUTO":
                typer.echo("⚡ [TURING MODO AUTO] Encadeando automaticamente para a ONDA-001...")
                orch.start_wave("ONDA-001", autonomy_mode="AUTO")
                continue
            else:
                break

        # 3. EXECUTE (Ondas de Entrega)
        st = orch.get_status()
        if st["stage"] in ("PLAN", "REFINEMENT", "EXECUTE"):
            typer.echo("⚡ Executando ciclo de engenharia TDD...")
            cards = orch.kanban.list_cards(wave_id=st["wave_id"])
            stories = [c["story_id"] for c in cards] if cards else ["ST-001"]
            res_exec = orch.run_execute(stories=stories)
            if not res_exec.get("success"):
                typer.echo(f"❌ Falha em EXECUTE: {res_exec.get('error')}", err=True)
                return
            typer.echo("✅ Ciclos de engenharia concluídos (DEV_DONE).")
            if st.get("autonomy_mode", "").upper().replace("-", "_") == "MANUAL":
                typer.echo(
                    "⏸ Etapa EXECUTE concluída (modo MANUAL). Homologa com: bombe-code wave validate"
                )
                return

        # 4. VALIDATE (Ondas de Entrega)
        st = orch.get_status()
        if st["stage"] in ("EXECUTE", "VALIDATE"):
            typer.echo(f"🔍 Executando VALIDATE para {st['wave_id']}...")
            res_val = orch.run_validate()
            if not res_val.get("success"):
                typer.echo(f"❌ Falha em VALIDATE: {res_val.get('error')}", err=True)
                return
            typer.echo(
                f"✅ VALIDATE aprovado com sucesso para {st['wave_id']}! Stories marcadas como DONE."
            )

        # 5. END / COMPLETED
        if st.get("autonomy_mode", "").upper().replace("-", "_") == "MANUAL":
            typer.echo("⏸ Etapa VALIDATE concluída (modo MANUAL). Arquiva com: bombe-code wave end")
            return
        res_end = orch.end_wave()
        typer.echo(f"🎉 {res_end.get('message', 'ONDA concluída!')}")

        # Checa se há ondas futuras mapeadas no Sequenciador do PRD
        prd_file = Path(project_dir) / "docs" / "briefings" / "PRD.md"
        prd_content = prd_file.read_text(encoding="utf-8") if prd_file.exists() else ""
        sequencer = WaveSequencer.from_markdown(prd_content)

        if st["autonomy_mode"] == "AUTO" and sequencer.has_future_waves(st["wave_id"]):
            current_idx = sequencer.get_plan_index(st["wave_id"])
            next_plan = sequencer.plans[current_idx + 1]
            typer.echo(
                f"\n⚡ [TURING MODO AUTO] Encadeando para a próxima onda: {next_plan.wave_id} ({next_plan.name})..."
            )
            orch.start_wave(next_plan.wave_id, autonomy_mode="AUTO")
            continue
        else:
            typer.echo("\n🏆 Ciclo completo de todas as ondas finalizado com sucesso!")
            break


@wave_cli.command("status")
def wave_status(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Exibe o status da ONDA ativa, Gates do Turing e Kanban de Stories."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    st = orch.get_status()
    summary = st["tasks_summary"]
    gates = st.get("gates", {})
    cards = st.get("kanban_cards", [])

    typer.echo(f"ONDA: {st['wave_id']} | Etapa: {st['stage']}")
    typer.echo(f"Modo: {st['autonomy_mode']} | Engenharia: {st['engineering_mode']}")
    typer.echo(
        f"Tasks: {summary['completed']} concluídas, {summary['pending']} pendentes, {summary['failed']} falhas"
    )

    if gates:
        typer.echo("\nGates do Turing Runtime:")
        for gate_name, gate_info in gates.items():
            status_icon = "✓" if gate_info.get("approved") else "✗"
            typer.echo(f"  [{status_icon}] {gate_name.upper()}: {gate_info.get('message', '')}")

    if cards:
        typer.echo("\nKanban de Stories:")
        for c in cards:
            blocked_tag = f" 🛑 [BLOCKED: {c.get('block_reason')}]" if c.get("is_blocked") else ""
            typer.echo(
                f"  • [{c['status']}] {c['story_id']}: {c['title']} ({c.get('agent', '')}){blocked_tag}"
            )


@wave_cli.command("discuss")
def wave_discuss(
    topic: Annotated[
        str | None, typer.Argument(help="Tópico para discussão de viabilidade e PRD")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa a etapa DISCUSS com @meira e @grace."""
    if not topic or not topic.strip():
        typer.echo(
            "⚠️ O comando 'bombe-code wave discuss' requer a descrição da missão ou produto.\n"
            'Exemplo: bombe-code wave discuss "App de Onboarding com Quiz Financeiro"',
            err=True,
        )
        raise typer.Exit(code=1)

    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_discuss(topic)
    if res.get("success"):
        typer.echo("Etapa DISCUSS concluída com sucesso.")
    else:
        typer.echo(f"Erro em DISCUSS: {res.get('error')}", err=True)


@wave_cli.command("plan")
def wave_plan(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa a etapa PLAN com os arquitetos de Upstream."""
    prd_file = Path(project_dir) / "docs" / "briefings" / "PRD.md"
    if not prd_file.exists():
        typer.echo(
            "⚠️ Não é possível executar a etapa PLAN sem um PRD aprovado.\n"
            "Execute primeiro a etapa DISCUSS com sua ideia:\n"
            '  bombe-code wave discuss "Descreva sua ideia aqui"',
            err=True,
        )
        raise typer.Exit(code=1)

    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_plan()
    if res.get("success"):
        typer.echo("Etapa PLAN concluída com sucesso.")
    else:
        typer.echo(f"Erro em PLAN: {res.get('error')}", err=True)


@wave_cli.command("cycle")
def wave_cycle(
    story_id: Annotated[
        str | None, typer.Argument(help="ID da story para execução atômica")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa o ciclo atômico de uma story e pausa."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_cycle(story_id)
    typer.echo(res.get("message", "Ciclo executado."))


@wave_cli.command("execute")
def wave_execute(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa o lote total de stories da ONDA (Cycle-Full)."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_execute()
    typer.echo(res.get("message", "Execução de stories finalizada."))


@wave_cli.command("validate")
def wave_validate(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa a validação formal da ONDA com @edith e @nina (com ciclo de retrabalho em AUTO)."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_validate()
    if res.get("success"):
        typer.echo("ONDA homologada com sucesso.")
    elif res.get("blocked"):
        escalation = (res.get("rework") or {}).get("escalation") or {}
        typer.echo(
            "❓ DÚVIDA DE NEGÓCIO — intervenção humana solicitada (último recurso).", err=True
        )
        typer.echo(
            f"Responsável técnico sugerido: {escalation.get('suggested_owner', '@turing')}",
            err=True,
        )
        for bloqueio in escalation.get("blockers", []):
            typer.echo(f"  • {bloqueio}", err=True)
        typer.echo(res.get("error") or "", err=True)
        typer.echo("Resolva e reexecute: bombe-code wave validate", err=True)
    else:
        typer.echo(f"Validação não aprovada: {res.get('error')}", err=True)


@wave_cli.command("audit")
def wave_audit(
    wave_id: Annotated[str | None, typer.Argument(help="ONDA alvo (padrão: onda ativa)")] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Contra-Auditoria Forense (@hoare): 'pedido vs. entregue' com o código como verdade."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_audit(wave_id)
    typer.echo(res.get("message", "Auditoria concluída."))
    if res.get("success") and res.get("limpa"):
        typer.echo(
            f"✅ AUDITORIA: LIMPA (suíte real: {res.get('suite')}). Laudo: {res.get('laudo_path')}"
        )
    elif res.get("success"):
        typer.echo("🚨 FUROS ENCONTRADOS:")
        for furo in res.get("furos", []):
            typer.echo(f"  • {furo}")
        if res.get("reexecucao"):
            typer.echo(res["reexecucao"])


@wave_cli.command("resume")
def wave_resume(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Retoma a ONDA ativa exatamente do checkpoint onde o processo anterior parou."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    saved = orch.db.load_wave_state() or {}
    wave_id_salvo = str(saved.get("wave_id") or "").strip()
    estado_salvo = str(saved.get("state") or "").strip().upper()
    if not wave_id_salvo:
        typer.echo(
            "Nenhuma ONDA persistida para retomar. Inicie com: bombe-code wave start ONDA-001",
            err=True,
        )
        raise typer.Exit(code=1)
    if estado_salvo in ("COMPLETED", ""):
        typer.echo(
            f"A {wave_id_salvo} está concluída ou sem checkpoint válido — nada a retomar. "
            f"Use: bombe-code wave start {wave_id_salvo}",
            err=True,
        )
        raise typer.Exit(code=1)
    res = orch.start_wave(wave_id_salvo)
    typer.echo(res.get("message", "ONDA retomada."))
    diagnostico = (res.get("diagnosis") or {}).get("summary")
    if diagnostico:
        typer.echo(f"Diagnóstico do Kanban: {diagnostico}")
    typer.echo(f"Etapa ativa: {res.get('stage')}. Continue com: bombe-code wave run")


@wave_cli.command("promote")
def wave_promote(
    destino: Annotated[str, typer.Argument(help="Destino da promoção: dev | hml | main")],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
    mensagem: Annotated[
        str | None, typer.Option("--mensagem", "-m", help="Mensagem do squash (destino dev)")
    ] = None,
) -> None:
    """Promove estados pela política de branches: working→dev (squash), dev→hml, hml→main."""
    from bombe_code.turing.promocao import PromotorDeBranches

    promotor = PromotorDeBranches(project_dir)
    destino_norm = destino.strip().lower()
    if destino_norm == "dev":
        res = promotor.promover_para_dev(
            mensagem or "feat: promoção manual do estado aprovado da IA (squash)"
        )
    else:
        res = promotor.promover_fase(destino_norm)
    if res.success:
        typer.echo(f"✅ {res.mensagem}")
        for d in res.detalhes:
            typer.echo(f"  • {d}")
    else:
        typer.echo(f"❌ {res.mensagem}", err=True)
        raise typer.Exit(code=1)


@wave_cli.command("end")
def wave_end(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Finaliza e arquiva a ONDA."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.end_wave()
    typer.echo(res.get("message", "ONDA finalizada."))


project_cli = typer.Typer(
    name="project", help="Comandos de configuração do projeto (.bombeconfig)."
)
app.add_typer(project_cli, name="project")


@project_cli.command("detect")
def project_detect(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Autodetecta a stack tecnológica e salva no .bombeconfig."""
    from bombe_code.config.project_config import ProjectConfigManager

    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.detect_stack()
    mgr.save(cfg)
    typer.echo("Stack autodetectada e salva em .bombeconfig:")
    typer.echo(f"- Backend: {cfg.backend_language} ({cfg.backend_path})")
    typer.echo(f"- Frontend: {cfg.frontend_stack} ({cfg.frontend_path})")


@project_cli.command("config")
def project_config(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Exibe a configuração ativa do projeto."""
    from bombe_code.config.project_config import ProjectConfigManager

    mgr = ProjectConfigManager(project_dir=project_dir)
    cfg = mgr.load()
    typer.echo(f"Configuração do Projeto ({cfg.name}):")
    typer.echo(f"- Tipo: {cfg.type}")
    typer.echo(f"- Backend: {cfg.backend_language}")
    typer.echo(f"- Frontend: {cfg.frontend_stack}")
    typer.echo(f"- Modo de Engenharia: {cfg.mode}")
    typer.echo(f"- Autonomia: {cfg.autonomy}")


starter_cli = typer.Typer(name="starter", help="Gerenciador de starters e scaffolds de projetos.")
project_cli.add_typer(starter_cli, name="starter")


@starter_cli.command("list")
def starter_list() -> None:
    """Lista todos os starters disponíveis no catálogo."""
    from bombe_code.starters.engine import StarterEngine

    engine = StarterEngine()
    starters = engine.list_starters()
    typer.echo("Starters Disponíveis no Bombe Code:")
    for s in starters:
        typer.echo(f"• {s['id']} [{s['stack']}] — {s['name']}: {s['description']}")


@starter_cli.command("apply")
def starter_apply(
    starter_id: Annotated[str, typer.Argument(help="ID do starter a aplicar")],
    target_dir: Annotated[
        str, typer.Option("--target-dir", "-t", help="Diretório de destino")
    ] = ".",
    name: Annotated[str | None, typer.Option("--name", "-n", help="Nome do projeto")] = None,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Sobrescrever arquivos existentes")
    ] = False,
) -> None:
    """Aplica o scaffolding do starter no diretório de destino."""
    from bombe_code.starters.engine import StarterEngine

    engine = StarterEngine()
    res = engine.apply_starter(
        starter_id=starter_id,
        target_dir=target_dir,
        project_name=name,
        force=force,
    )
    if res.get("success"):
        typer.echo(res.get("message", "Starter aplicado com sucesso."))
        typer.echo(f"Arquivos gerados: {len(res.get('created_files', []))}")
    else:
        typer.echo(f"Erro ao aplicar starter: {res.get('error')}", err=True)
        raise typer.Exit(code=1)


snippet_cli = typer.Typer(name="snippet", help="Gerencia snippets de código (Fábrica de LEGO).")
app.add_typer(snippet_cli, name="snippet")


@snippet_cli.command("list")
def snippet_list(
    platform: Annotated[
        str | None,
        typer.Option("--platform", "-p", help="Filtrar por linguagem (python, go, nodejs)"),
    ] = None,
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Filtrar por categoria")
    ] = None,
) -> None:
    """Lista snippets disponíveis no catálogo."""
    from bombe_code.snippets.registry import SnippetRegistry

    reg = SnippetRegistry()
    snippets = reg.list_snippets(platform=platform, category=category)
    typer.echo(f"Snippets Disponíveis ({len(snippets)}):")
    for s in snippets:
        typer.echo(f"• {s['name']} [{s['platform']}] ({s['category']}): {s['description']}")


@snippet_cli.command("search")
def snippet_search(
    query: Annotated[str, typer.Argument(help="Termo de pesquisa")],
    platform: Annotated[
        str | None, typer.Option("--platform", "-p", help="Filtrar por linguagem")
    ] = None,
) -> None:
    """Pesquisa snippets por termo no nome, descrição ou tags."""
    from bombe_code.snippets.registry import SnippetRegistry

    reg = SnippetRegistry()
    results = reg.search(query=query, platform=platform)
    typer.echo(f"Snippets Encontrados para '{query}' ({len(results)}):")
    for s in results:
        typer.echo(f"• {s['name']} [{s['platform']}]: {s['description']}")


@snippet_cli.command("install")
def snippet_install(
    name: Annotated[str, typer.Argument(help="Nome do snippet")],
    to: Annotated[
        str, typer.Option("--to", "-t", help="Diretório de destino no projeto")
    ] = "src/utils",
    platform: Annotated[str, typer.Option("--platform", "-p", help="Linguagem")] = "python",
) -> None:
    """Instala o código e testes do snippet no diretório especificado."""
    from bombe_code.snippets.registry import SnippetRegistry

    reg = SnippetRegistry()
    res = reg.copy_snippet(name=name, to_dir=to, platform=platform)
    if res.get("success"):
        typer.echo(res.get("message", "Snippet instalado com sucesso."))
    else:
        typer.echo(f"Erro ao instalar snippet: {res.get('error')}", err=True)
        raise typer.Exit(code=1)


@app.command("mode")
def set_mode_cmd(
    mode_str: Annotated[
        str,
        typer.Argument(
            help="Modo de autonomia (auto, semi-auto, manual) ou engenharia (tdd, vibe)"
        ),
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Alterna modo de autonomia ou modo de engenharia."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.set_mode(mode_str)
    if res.get("success"):
        typer.echo(res.get("message", "Modo atualizado com sucesso."))
    else:
        typer.echo(f"Erro: {res.get('error')}", err=True)


@app.command("rca")
def rca_cmd(
    incident: Annotated[
        str, typer.Argument(help="Descrição do incidente para análise de causa raiz")
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa Análise de Causa Raiz determinística com @unclebob."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_rca(incident)
    typer.echo(f"RCA executada por {res.get('agent')}:")
    typer.echo(res.get("report"))


@app.command("simplify")
def simplify_cmd(
    target: Annotated[
        str, typer.Argument(help="Caminho do arquivo ou módulo para auditoria de simplificação")
    ],
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa auditoria de simplificação de código com @ieru e @unclebob."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_simplify(target)
    typer.echo(f"Simplificação executada por {res.get('agent')}:")
    typer.echo(res.get("output"))


@app.command("task")
def task_cmd(
    description: Annotated[str, typer.Argument(help="Descrição da tarefa avulsa")],
    agent: Annotated[
        str | None,
        typer.Option("--agent", "-a", help="Especialista para despachar (ex: @unclebob)"),
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Executa uma tarefa técnica avulsa sem alterar o estágio da ONDA."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    res = orch.run_task(description, agent_handle=agent)
    typer.echo(f"Task executada ({res.get('agent')}):")
    typer.echo(res.get("output"))


@app.command("report")
def report_cmd(
    project_dir: Annotated[str, typer.Option("--project-dir", help="Pasta do projeto")] = ".",
) -> None:
    """Gera um relatório consolidado do projeto e da ONDA ativa."""
    from bombe_code.turing.orchestrator import WaveOrchestrator

    orch = WaveOrchestrator(project_dir=project_dir)
    rep = orch.generate_status_report()
    typer.echo(f"Relatório Consolidado — ONDA {rep['wave_id']} (Estágio: {rep['stage']}):")
    typer.echo(f"- Modo: Autonomia={rep['autonomy_mode']}, Engenharia={rep['engineering_mode']}")
    typer.echo(
        f"- Projeto: {rep['config']['name']} ({rep['config']['backend_language']}/{rep['config']['frontend_stack']})"
    )
    typer.echo(f"- Total de Tasks Registradas: {rep['tasks_summary']['total']}")


@app.command("version")
def version() -> None:
    """Exibe a versão instalada do Bombe Code."""
    typer.echo(f"bombe-code {__version__}")


@app.command("upgrade")
def upgrade_cmd(
    branch: Annotated[
        str | None,
        typer.Option(
            "--branch",
            "-b",
            help="Branch do repositório Git para upgrade (ex: main, dev-working-ia)",
        ),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag", "-t", help="Tag/Release específica do Git (ex: v0.1.2)"),
    ] = None,
    git_url: Annotated[
        str | None,
        typer.Option("--git-url", "-g", help="URL do repositório Git (padrão: oficial no GitHub)"),
    ] = None,
    local: Annotated[
        bool,
        typer.Option("--local", "-l", help="Atualiza a partir do diretório local atual"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Força a reinstalação mesmo se a versão for a mesma"),
    ] = True,
    check_only: Annotated[
        bool,
        typer.Option(
            "--check",
            "-c",
            help="Apenas verifica se há novas versões disponíveis no Git sem instalar",
        ),
    ] = False,
) -> None:
    """Atualiza a instalação do Bombe Code via Git usando uv tool install."""
    from .updater import ha_sessao_ativa

    sessoes = ha_sessao_ativa()
    if sessoes:
        detalhes = ", ".join(f"PID {s['pid']}" for s in sessoes)
        typer.echo(
            f"⏸ Deploy BLOQUEADO: há sessão(ões) do Bombe Code rodando ({detalhes}).\n"
            "Feche-a(s) antes de atualizar — deploy por cima derruba trabalho em voo "
            "e deixa o usuário na versão velha sem saber.",
            err=True,
        )
        raise typer.Exit(code=1)
    from .updater import run_upgrade

    typer.echo("🔄 Verificando atualizações do Bombe Code...")
    res = run_upgrade(
        git_url=git_url,
        branch=branch,
        tag=tag,
        local=local,
        force=force,
        check_only=check_only,
    )

    if not res.get("success"):
        typer.echo(f"❌ Erro durante o upgrade: {res.get('error')}", err=True)
        raise typer.Exit(code=1)

    if res.get("check_only"):
        typer.echo(f"ℹ️ {res.get('message')}")
        return

    typer.echo(f"✅ {res.get('message')}")
    if res.get("remote_sha"):
        typer.echo(f"   Commit SHA: {res.get('remote_sha')[:10]}")


@app.command("models")
def models() -> None:
    """Lista catálogo de modelos suportados."""
    try:
        catalog = get_models()
        typer.echo("Catálogo de Modelos (models.dev):")
        for prov, info in catalog.items():
            if isinstance(info, dict) and "models" in info:
                mod_names = ", ".join(list(info["models"].keys())[:5])
                typer.echo(f"  • {prov}: {mod_names}...")
    except (OSError, RuntimeError, httpx.HTTPError):
        # Fallback offline
        typer.echo("Catálogo de Modelos (offline):")
        typer.echo("  • openai: gpt-4o, gpt-4o-mini, o1")
        typer.echo("  • anthropic: claude-3-5-sonnet, claude-3-5-haiku")
        typer.echo("  • google: gemini-1.5-pro, gemini-2.0-flash")


@app.command("providers")
def providers() -> None:
    """Lista provedores de LLM suportados."""
    provs = [
        "anthropic",
        "openai",
        "google",
        "azure",
        "bedrock",
        "copilot",
        "openrouter",
        "xai",
        "openai-compatible",
    ]
    typer.echo("Provedores suportados:")
    for p in provs:
        typer.echo(f"  • {p}")


@app.command("run")
def run_command(
    prompt: Annotated[str, typer.Argument(help="Instrução para o agente")],
    model: Annotated[str | None, typer.Option("--model", "-m", help="Modelo a utilizar")] = None,
    agent: Annotated[str | None, typer.Option("--agent", "-a", help="Nome do agente")] = None,
    session: Annotated[
        str | None, typer.Option("--session", "-s", help="ID da sessão existente")
    ] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Diretório do projeto")] = ".",
) -> None:
    """Executa um prompt diretamente no terminal e imprime a resposta."""
    s_obj = (
        crud.load_session(session)
        if session
        else crud.create_session(title="CLI Run", directory=project_dir)
    )
    adapter = resolve_default_adapter(model)
    registry = create_default_registry(project_dir=project_dir)

    def on_event(ev: dict[str, Any]) -> None:
        if ev.get("type") == "text-delta":
            sys.stdout.write(ev.get("text", ""))
            sys.stdout.flush()

    output = run_prompt(
        session=s_obj,
        user_text=prompt,
        adapter=adapter,
        registry=registry,
        on_event=on_event,
    )
    if not output:
        typer.echo("")
    else:
        typer.echo("")


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option("--host", "-h", help="Host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Porta HTTP")] = 4096,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Diretório")] = ".",
) -> None:
    """Inicia o servidor HTTP Bombe Code em primeiro plano."""
    adapter = resolve_default_adapter()
    permissions = PermissionService(
        rules=[Rule(permission="*", pattern="*", action="allow")],
        approved=[],
    )
    app_instance = create_app(
        adapter=adapter,
        permissions=permissions,
        project_dir=project_dir,
    )
    typer.echo(f"Iniciando Bombe Code Server em http://{host}:{port}")
    uvicorn.run(app_instance, host=host, port=port)


@app.command("tui")
def tui(
    port: Annotated[int | None, typer.Option("--port", "-p", help="Porta do servidor")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Modelo")] = None,
    agent: Annotated[str | None, typer.Option("--agent", "-a", help="Agente")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s", help="ID da sessão")] = None,
    project_dir: Annotated[str, typer.Option("--project-dir", help="Diretório")] = ".",
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Modo menos verboso: apenas anúncios de onda, etapas e vetos (padrão é verboso: streama tudo)",
        ),
    ] = False,
) -> None:
    """Abre a interface interativa de terminal (TUI Textual)."""
    from ..tui.app import BombeTuiApp
    from ..tui.client import BombeClient
    from ..turing.progress import BUS

    def _restaurar_terminal() -> None:
        """Desliga modos de rastreio (mouse/bracketed) deixados por um crash.

        Sem isso, após uma morte abrupta o shell ecoa códigos como
        '35;100;2M' a cada movimento do mouse (opencode original sofre igual).
        """
        try:
            sys.stdout.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?2004l\x1b[?25h")
            sys.stdout.flush()
        except (OSError, ValueError):
            pass

    if quiet:
        BUS.set_verbosity("quiet")
        os.environ["BOMBE_VERBOSITY"] = "quiet"

    server_thread: ServerThread | None = None
    if port is None:
        server_thread, bound_port, password = start_server_in_process(
            port=0, project_dir=project_dir
        )
        base_url = f"http://127.0.0.1:{bound_port}"
        auth = ("bombe", password)
    else:
        auth_path = get_paths().state / "server-auth"
        password = auth_path.read_text(encoding="utf-8").strip() if auth_path.is_file() else ""
        base_url = f"http://127.0.0.1:{port}"
        auth = ("bombe", password)

    import atexit

    atexit.register(_restaurar_terminal)
    try:
        try:
            client = BombeClient(base_url, auth=auth)
            tui_app = BombeTuiApp(
                client=client, session_id=session, model=model, agent=agent, project_dir=project_dir
            )
            tui_app.run()
        finally:
            _restaurar_terminal()
            if server_thread:
                server_thread.stop()
    except Exception as exc:
        from ..errors import format_error_panel, is_debug_mode, record_exception

        if is_debug_mode():
            raise
        log_file = record_exception(exc, context="CLI TUI Runner")
        from rich.console import Console

        console = Console(stderr=True)
        console.print(format_error_panel(exc, log_file))
        sys.exit(1)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Ponto de entrada padrão: se nenhum comando for fornecido, executa 'tui'."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(tui)
