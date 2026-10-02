"""Carregador de definições de agentes no padrão PDW 4.0 a partir de arquivos Markdown."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from bombe_code.agents.models import AgentDefinition, AgentOrigin
from bombe_code.turing.state_machine import TuringStage

logger = logging.getLogger(__name__)

BRAZILIAN_HANDLES = {
    "meira",
    "ieru",
    "barreto",
    "diego",
    "caroli",
    "valim",
    "aniche",
    "edith",
    "demi",
    "claudia",
    "nelson",
    "nina",
}

STAGE_MAP = {
    "turing": TuringStage.COMPLETED,
    "meira": TuringStage.DISCUSS,
    "grace": TuringStage.DISCUSS,
    "alan": TuringStage.PLAN,
    "norman": TuringStage.PLAN,
    "ieru": TuringStage.PLAN,
    "codd": TuringStage.PLAN,
    "claudia": TuringStage.PLAN,
    "caroli": TuringStage.PLAN,
    "barreto": TuringStage.PLAN,
    "nelson": TuringStage.PLAN,
    "valim": TuringStage.EXECUTE,
    "barbara": TuringStage.EXECUTE,
    "scott": TuringStage.EXECUTE,
    "ryan": TuringStage.EXECUTE,
    "james": TuringStage.EXECUTE,
    "ada": TuringStage.EXECUTE,
    "unclebob": TuringStage.EXECUTE,
    "diego": TuringStage.EXECUTE,
    "aniche": TuringStage.EXECUTE,
    "demi": TuringStage.EXECUTE,
    "edith": TuringStage.VALIDATE,
    "nina": TuringStage.VALIDATE,
}

INPUT_OUTPUT_MAP = {
    "turing": (
        ["Objetivo da ONDA ou Intenção do Usuário"],
        ["Transições de Estado da ONDA", "Relatórios de Gates"],
    ),
    "meira": (
        ["Ideia Bruta ou Demanda do Usuário"],
        ["docs/briefings/viability.md"],
    ),
    "grace": (
        ["docs/briefings/viability.md"],
        ["docs/briefings/PRD.md"],
    ),
    "alan": (
        ["docs/briefings/PRD.md"],
        ["docs/architecture/journey.md"],
    ),
    "norman": (
        ["docs/briefings/PRD.md", "docs/architecture/journey.md"],
        ["docs/architecture/ui-ux.md"],
    ),
    "ieru": (
        ["docs/briefings/PRD.md"],
        ["docs/architecture/arch.md", "docs/architecture/adr/"],
    ),
    "codd": (
        ["docs/architecture/arch.md"],
        ["docs/architecture/db.md", "migrations/"],
    ),
    "claudia": (
        ["docs/architecture/arch.md"],
        ["docs/architecture/db-nosql.md"],
    ),
    "barreto": (
        ["docs/architecture/arch.md", "docs/briefings/PRD.md"],
        ["docs/security/threat-model.md"],
    ),
    "caroli": (
        ["docs/briefings/PRD.md", "docs/architecture/arch.md"],
        ["docs/backlog/stories/ST-*.md"],
    ),
    "valim": (
        ["docs/backlog/stories/ST-XXX.md com DoR"],
        ["tests/ (testes passando)", "src/ (código de produção)"],
    ),
    "barbara": (
        ["docs/backlog/stories/ST-XXX.md com DoR"],
        ["tests/ (pytest / go test)", "src/ (código Python/Go)"],
    ),
    "scott": (
        ["docs/backlog/stories/ST-XXX.md com DoR"],
        ["tests/ (xUnit)", "src/ (código C# / ASP.NET)"],
    ),
    "ryan": (
        ["docs/backlog/stories/ST-XXX.md com DoR"],
        ["tests/ (Vitest / Jest)", "src/ (código Fastify / Node / TS)"],
    ),
    "james": (
        ["docs/backlog/stories/ST-XXX.md com DoR"],
        ["tests/ (JUnit / MockMvc)", "src/ (código Java / Spring)"],
    ),
    "ada": (
        ["docs/backlog/stories/ST-XXX.md", "Contratos de API Backend"],
        ["src/ui/ (componentes reais integrados à API)"],
    ),
    "unclebob": (
        ["Código implementado", "Suíte de testes", "ST-XXX.md"],
        ["Selo do Tech Lead na Story ST-XXX.md ou Parecer de Correção"],
    ),
    "diego": (
        ["Código implementado", "Rotas de API"],
        ["docs/security/appsec-audit.md com Veredito de Segurança"],
    ),
    "aniche": (
        ["Story ST-XXX.md", "Código implementado"],
        ["tests/integration/", "tests/e2e/", "docs/qa/test-strategy.md"],
    ),
    "edith": (
        ["docs/briefings/PRD.md", "docs/backlog/stories/"],
        ["docs/reports/validation_report.md com Selo Final da ONDA"],
    ),
    "demi": (
        ["Requisitos de Infraestrutura e Runtime"],
        ["docker-compose.yml", "Dockerfile", "docs/infra/"],
    ),
    "nelson": (
        ["Especificações de Agentes ou Prompts do Sistema"],
        ["Prompts validados no padrão PDW 4.0"],
    ),
    "nina": (
        ["Traces de execução e consumo de tokens da ONDA"],
        ["docs/governance/finops-audit.md"],
    ),
}


def load_agent_from_file(file_path: Path) -> AgentDefinition | None:
    """Lê um arquivo .md no formato PDW 4.0 e constrói o AgentDefinition correspondente."""
    try:
        content = file_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        fm_text, body = match.groups()
        fm = yaml.safe_load(fm_text) or {}

        slug = fm.get("name", file_path.stem).lower()
        handle = f"@{slug}"

        identity = fm.get("identity") or {}
        name = identity.get("name", fm.get("name", slug.capitalize()))
        role = identity.get("role", fm.get("description", "Especialista"))
        background = identity.get("background", fm.get("description", ""))

        if slug == "turing":
            origin = AgentOrigin.UNIVERSAL
        elif slug in BRAZILIAN_HANDLES:
            origin = AgentOrigin.BRAZIL
        else:
            origin = AgentOrigin.WORLD

        primary_stage = STAGE_MAP.get(slug, TuringStage.PLAN)

        if primary_stage in (TuringStage.DISCUSS, TuringStage.PLAN):
            phase = "UPSTREAM"
        elif primary_stage in (TuringStage.EXECUTE, TuringStage.VALIDATE):
            phase = "DOWNSTREAM"
        else:
            phase = "ALL"

        req_inputs, exp_outputs = INPUT_OUTPUT_MAP.get(
            slug, (["Entrada da Story"], ["Saída do Artefato"])
        )

        skills = fm.get("skills", [])

        return AgentDefinition(
            handle=handle,
            name=name,
            role=role,
            origin=origin,
            historical_homage=background,
            primary_stage=primary_stage,
            phase=phase,
            required_inputs=req_inputs,
            expected_outputs=exp_outputs,
            skills_allowed=skills,
            system_prompt=body.strip(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao carregar agente de %s: %s", file_path, exc)
        return None


def load_all_agents(definitions_dir: Path | None = None) -> list[AgentDefinition]:
    """Carrega todos os agentes definidos na pasta definitions/."""
    if definitions_dir is None:
        definitions_dir = Path(__file__).parent / "definitions"

    agents: list[AgentDefinition] = []
    if not definitions_dir.is_dir():
        return agents

    for md_file in sorted(definitions_dir.glob("*.md")):
        agent = load_agent_from_file(md_file)
        if agent:
            agents.append(agent)

    return agents
