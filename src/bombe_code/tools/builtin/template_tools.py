"""Ferramentas determinísticas de Templates e Starters para agentes LLM (ST-042).

Permite que Tech Lead (@unclebob) e Arquiteto (@ieru) consultem starters compatíveis,
inspecionem o manifesto arquitetural e apliquem scaffolding determinístico.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from ...starters.engine import StarterEngine
from ...starters.matcher import TemplateMatcher
from ..base import ToolContext, ToolDef


class TemplateMatchArgs(BaseModel):
    product_type: str = Field(
        description="Tipo de produto (ex: saas, chatbot, api, web, whatsapp, bff, fullstack, backend)"
    )
    backend_language: str = Field(
        default="python",
        description="Linguagem principal do backend (python, go, nodejs, dotnet, java)",
    )
    frontend_stack: str | None = Field(
        default=None,
        description="Stack de frontend caso aplicável (react, streamlit, none)",
    )
    multitenancy: str | None = Field(
        default="mono",
        description="Tipo de multitenancy (mono, multi-logical, multi-physical)",
    )
    database: str | None = Field(
        default="postgresql",
        description="Banco de dados planejado (postgresql, none)",
    )


class TemplateInspectArgs(BaseModel):
    starter_id: str = Field(
        description="Identificador exato do starter (ex: python-mono, go-multi-logical, chatbot-py-streamlit)"
    )


class TemplateApplyArgs(BaseModel):
    starter_id: str = Field(description="Identificador do starter a aplicar")
    target_dir: str = Field(default=".", description="Diretório de destino do projeto")
    project_name: str | None = Field(default=None, description="Nome do projeto")
    force: bool = Field(default=False, description="Sobrescrever se diretório não estiver vazio")


def _template_match(args: dict[str, Any], ctx: ToolContext) -> str:
    matcher = TemplateMatcher()
    result = matcher.match(
        product_type=args.get("product_type", "saas"),
        backend_language=args.get("backend_language", "python"),
        frontend_stack=args.get("frontend_stack"),
        multitenancy=args.get("multitenancy"),
        database=args.get("database"),
    )
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)


def _template_inspect(args: dict[str, Any], ctx: ToolContext) -> str:
    engine = StarterEngine()
    starter = engine.get_starter(args["starter_id"])
    if not starter:
        return json.dumps(
            {"error": f"Starter '{args['starter_id']}' não encontrado no catálogo."},
            ensure_ascii=False,
            indent=2,
        )

    matcher = TemplateMatcher(engine)
    manifest = matcher._build_manifest(
        starter, starter.get("config", {}).get("multitenancy", "mono")
    )
    payload = dict(starter)
    payload["manifest"] = manifest.to_dict()
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _template_apply(args: dict[str, Any], ctx: ToolContext) -> str:
    engine = StarterEngine()
    target_dir = args.get("target_dir", ".")
    if target_dir == "." and ctx.project_dir:
        target_dir = ctx.project_dir

    result = engine.apply_starter(
        starter_id=args["starter_id"],
        target_dir=target_dir,
        project_name=args.get("project_name"),
        force=args.get("force", False),
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


TEMPLATE_MATCH_TOOL = ToolDef(
    id="template_match",
    description="Consulta o catálogo de starters oficiais e encontra o blueprint mais adequado com seu manifesto arquitetural.",
    parameters=TemplateMatchArgs,
    execute=_template_match,
)

TEMPLATE_INSPECT_TOOL = ToolDef(
    id="template_inspect",
    description="Inspeciona os detalhes técnicos, convenções de banco, entidades e arquivos de um starter do catálogo.",
    parameters=TemplateInspectArgs,
    execute=_template_inspect,
)

TEMPLATE_APPLY_TOOL = ToolDef(
    id="template_apply",
    description="Aplica o scaffolding determinístico de um starter oficial na pasta do projeto.",
    parameters=TemplateApplyArgs,
    execute=_template_apply,
)
