"""Ferramentas de busca e consulta de Snippets para agentes LLM (ST-026)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from ...snippets.registry import SnippetRegistry
from ..base import ToolContext, ToolDef


class SnippetSearchArgs(BaseModel):
    query: str = Field(description="Termo de busca do snippet (ex: cpf, cnpj, phone, hash, uuid)")
    platform: str | None = Field(
        default=None, description="Filtro opcional por linguagem (python, go, nodejs)"
    )


class SnippetGetArgs(BaseModel):
    name: str = Field(description="Identificador exato do snippet (ex: validar-cpf, hash-password)")
    platform: str = Field(default="python", description="Linguagem do snippet (python, go, nodejs)")


def _snippet_search(args: dict[str, Any], ctx: ToolContext) -> str:
    registry = SnippetRegistry()
    results = registry.search(query=args["query"], platform=args.get("platform"))
    return json.dumps(results, ensure_ascii=False, indent=2)


def _snippet_get(args: dict[str, Any], ctx: ToolContext) -> str:
    registry = SnippetRegistry()
    snippet = registry.get_snippet(name=args["name"], platform=args.get("platform", "python"))
    if not snippet:
        return json.dumps(
            {
                "error": f"Snippet '{args['name']}' não encontrado para a plataforma '{args.get('platform')}'."
            },
            ensure_ascii=False,
        )
    return json.dumps(snippet, ensure_ascii=False, indent=2)


SNIPPET_SEARCH_TOOL = ToolDef(
    id="snippet_search",
    description="Busca no catálogo de snippets reutilizáveis (LEGO) funções auditadas com testes prontos.",
    parameters=SnippetSearchArgs,
    execute=_snippet_search,
)

SNIPPET_GET_TOOL = ToolDef(
    id="snippet_get",
    description="Obtém o código-fonte integral, testes e documentação de um snippet específico do catálogo.",
    parameters=SnippetGetArgs,
    execute=_snippet_get,
)
