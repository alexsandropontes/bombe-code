"""Gestão e Persistência da Decisão de Template no Upstream (ST-043).

Registra a seleção de starter blueprint realizada pelo Tech Lead (@unclebob)
e Arquiteto (@ieru) em docs/arquitetura/TEMPLATE_STARTER.md, garantindo alinhamento
com o DBA (@codd) e acionamento obrigatório da STORY-0 no PBB.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .matcher import TemplateMatchResult

logger = logging.getLogger(__name__)

STARTER_DECISION_PATH = "docs/arquitetura/TEMPLATE_STARTER.md"


def save_starter_decision(
    project_dir: Path | str,
    match_result: TemplateMatchResult | dict[str, Any],
    adr_id: str = "ADR-001",
) -> Path:
    """Grava o documento de decisão do starter para balizar ADR, DBA e PBB."""
    root = Path(project_dir).resolve()
    target_file = root / STARTER_DECISION_PATH
    target_file.parent.mkdir(parents=True, exist_ok=True)

    data = (
        match_result.to_dict()
        if isinstance(match_result, TemplateMatchResult)
        else dict(match_result)
    )
    s_id = data.get("starter_id") or "custom-starter"
    name = data.get("name") or s_id
    manifest = data.get("manifest") or {}
    tables = manifest.get("suggested_tables", [])
    entities = manifest.get("expected_entities", [])
    endpoints = manifest.get("base_endpoints", [])
    guidelines = manifest.get("guidelines", [])

    lines = [
        f"# Decisão de Starter Blueprint — {name}",
        "",
        f"- **ADR Referência:** {adr_id}",
        f"- **Starter ID:** `{s_id}`",
        f"- **Blueprint:** `{data.get('blueprint') or s_id}`",
        f"- **Categoria:** {data.get('category', 'general')}",
        f"- **Tipo:** {data.get('type', 'server')}",
        f"- **Multitenancy:** {manifest.get('multitenancy_type', 'mono')}",
        "- **Protocolo:** `MANDATORY_STORY_0`",
        "",
        "## Manifesto Arquitetural e Anti-Drift",
        f"- **Entidades Canônicas Esperadas:** {', '.join(entities) if entities else 'Nenhuma'}",
        f"- **Tabelas Canônicas Sugeridas:** {', '.join(tables) if tables else 'Nenhuma'}",
        f"- **Endpoints Base:** {', '.join(endpoints) if endpoints else 'Nenhum'}",
        "",
        "### Diretrizes para DBA (@codd) e Tech Lead (@unclebob)",
    ]

    for g in guidelines:
        lines.append(f"- {g}")

    lines.extend(
        [
            "",
            "<!-- BOMBE_TEMPLATE_METADATA_START -->",
            "```json",
            json.dumps(data, ensure_ascii=False, indent=2),
            "```",
            "<!-- BOMBE_TEMPLATE_METADATA_END -->",
            "",
        ]
    )

    content = "\n".join(lines)
    target_file.write_text(content, encoding="utf-8")
    return target_file


def load_starter_decision(project_dir: Path | str) -> dict[str, Any] | None:
    """Lê a decisão de starter persistida no projeto, caso exista."""
    root = Path(project_dir).resolve()
    target_file = root / STARTER_DECISION_PATH
    if not target_file.is_file():
        return None

    content = target_file.read_text(encoding="utf-8")
    start_tag = "<!-- BOMBE_TEMPLATE_METADATA_START -->"
    end_tag = "<!-- BOMBE_TEMPLATE_METADATA_END -->"

    if start_tag in content and end_tag in content:
        try:
            json_block = content.split(start_tag)[1].split(end_tag)[0].strip()
            # Remove blocos markdown ```json
            if json_block.startswith("```"):
                json_block = json_block.split("\n", 1)[1]
            if json_block.endswith("```"):
                json_block = json_block.rsplit("```", 1)[0].strip()
            return json.loads(json_block)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            logger.warning(f"Erro ao parsear metadata de {target_file}: {e}")

    # Fallback: extrai do texto
    s_id = None
    for line in content.splitlines():
        if "Starter ID:" in line:
            s_id = line.split("`")[1] if "`" in line else line.split(":")[1].strip()
            break

    if s_id:
        return {"starter_id": s_id, "name": s_id, "matched": True}
    return None
