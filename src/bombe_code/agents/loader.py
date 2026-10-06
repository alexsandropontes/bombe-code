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

COUNTRY_MAP = {
    "turing": "Reino Unido",
    "meira": "Brasil",
    "grace": "Estados Unidos",
    "alan": "Estados Unidos",
    "norman": "Estados Unidos",
    "ieru": "Brasil",
    "codd": "Reino Unido",
    "claudia": "Brasil",
    "barreto": "Brasil",
    "caroli": "Brasil",
    "nelson": "Brasil",
    "valim": "Brasil",
    "barbara": "Estados Unidos",
    "scott": "Estados Unidos",
    "ryan": "Estados Unidos",
    "james": "Canadá",
    "ada": "Reino Unido",
    "unclebob": "Estados Unidos",
    "diego": "Brasil",
    "aniche": "Brasil",
    "demi": "Brasil",
    "edith": "Brasil",
    "nina": "Brasil",
}

HOMAGE_MAP = {
    "turing": "Alan Turing - Pioneiro da computação teórica, inteligência artificial e máquina universal de estados (Reino Unido).",
    "meira": "Silvio Meira - Pioneiro do ecossistema de software brasileiro, cofundador do CESAR e do Porto Digital (Brasil).",
    "grace": "Grace Hopper - Pioneira da programação de computadores, inventora dos primeiros compiladores e precursora do COBOL (Estados Unidos).",
    "alan": "Alan Cooper - Criador do Visual Basic, pioneiro do Goal-Directed Design e pai das Personas (Estados Unidos).",
    "norman": "Don Norman - Cientista cognitivo, cofundador do Nielsen Norman Group e pioneiro do Design Centrado no Usuário (Estados Unidos).",
    "ieru": "Roberto Ierusalimschy - Cientista da computação e professor da PUC-Rio, criador da linguagem de programação Lua (Brasil).",
    "codd": "Edgar F. Codd - Cientista da computação na IBM, inventor do modelo relacional e das 12 regras de Codd (Reino Unido).",
    "claudia": "Claudia Bauzer Medeiros - Professora titular da UNICAMP, pioneira em bancos de dados científicos e premiada pela ACM SIGMOD (Brasil).",
    "barreto": "Paulo Barreto - Criptógrafo, coautor das curvas elípticas BLS e BN e da função hash Whirlpool (Brasil).",
    "caroli": "Paulo Caroli - Criador do método Lean Inception e autoridade em facilitação ágil e fatiamento de MVP (Brasil).",
    "nelson": "Nelson Mattos - Cientista da computação brasileiro, ex-VP de Engenharia do Google e ex-IBM Fellow em sistemas de informação e IA (Brasil).",
    "valim": "José Valim - Criador da linguagem de programação Elixir sobre a BEAM e ex-membro do core team do Ruby on Rails (Brasil).",
    "barbara": "Barbara Liskov - Cientista pioneira do MIT, criadora do Princípio de Substituição de Liskov e vencedora do Prêmio Turing (Estados Unidos).",
    "scott": "Scott Guthrie - Criador original do ASP.NET e líder histórico do ecossistema .NET na Microsoft (Estados Unidos).",
    "ryan": "Ryan Dahl - Criador do Node.js e do runtime Deno, pioneiro em I/O assíncrono em servidores (Estados Unidos).",
    "james": "James Gosling - Criador e arquiteto original da linguagem de programação Java na Sun Microsystems (Canadá).",
    "ada": "Ada Lovelace - Matemática britânica pioneira, reconhecida historicamente como a primeira programadora da computação (Reino Unido).",
    "unclebob": "Robert C. Martin - Autor seminal de Clean Code e Clean Architecture e criador dos princípios SOLID (Estados Unidos).",
    "diego": "Diego Aranha - Pesquisador brasileiro de segurança e criptografia aplicada, líder de auditorias públicas independentes (Brasil).",
    "aniche": "Maurício Aniche - Cientista da computação brasileiro, autor do livro Effective Software Testing e líder técnico em testes (Brasil).",
    "demi": "Demi Getschko - Pioneiro da Internet no Brasil, diretor-presidente do NIC.br e membro do Internet Hall of Fame (Brasil).",
    "edith": "Edith Ranzini - Engenheira pioneira da USP, líder na engenharia do computador Patinho Feio (Brasil).",
    "nina": "Nina Silva - Executiva de tecnologia e governança, cofundadora do Movimento Black Money e eleita Top 100 MIPAD pela ONU (Brasil).",
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

        country = COUNTRY_MAP.get(
            slug, "Brasil" if origin == AgentOrigin.BRAZIL else "Estados Unidos"
        )
        historical_homage = HOMAGE_MAP.get(slug, background)

        return AgentDefinition(
            handle=handle,
            name=name,
            role=role,
            country=country,
            origin=origin,
            historical_homage=historical_homage,
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
