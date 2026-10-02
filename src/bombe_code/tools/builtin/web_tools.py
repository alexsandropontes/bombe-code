from __future__ import annotations

import re

import httpx
from pydantic import BaseModel

from ..base import ToolContext, ToolDef


class WebfetchArgs(BaseModel):
    url: str
    max_chars: int = 100_000


class WebsearchArgs(BaseModel):
    query: str
    max_results: int = 5


def _webfetch(args: dict, ctx: ToolContext) -> str:
    try:
        response = httpx.get(args["url"], timeout=30.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Erro ao buscar {args['url']}: {exc}"
    return response.text[: args["max_chars"]]


def _websearch(args: dict, ctx: ToolContext) -> str:
    try:
        response = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": args["query"]},
            timeout=20.0,
            headers={"User-Agent": "bombe-code"},
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return f"Erro na busca: {exc}"
    titles = re.findall(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>', response.text)
    limpo = [re.sub(r"<[^>]+>", "", title).strip() for title in titles]
    top = limpo[: args["max_results"]]
    return "\n".join(top) if top else f"Nenhum resultado para {args['query']!r}"


WEBFETCH_TOOL = ToolDef(
    id="webfetch", description="Busca conteudo de uma URL", parameters=WebfetchArgs, execute=_webfetch
)
WEBSEARCH_TOOL = ToolDef(
    id="websearch", description="Busca web (DuckDuckGo)", parameters=WebsearchArgs, execute=_websearch
)
