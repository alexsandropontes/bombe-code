"""Modelo de dados para manifestos de skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Extrai metadados do frontmatter YAML/chave-valor e o corpo do markdown."""
    raw = raw.strip()
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm_text = parts[1]
    body = parts[2].lstrip("\r\n")
    meta: dict[str, Any] = {}
    current_key: str | None = None

    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                items = [it.strip().strip("'\"") for it in val[1:-1].split(",") if it.strip()]
                meta[key] = items
                current_key = None
            elif not val:
                current_key = key
                meta[key] = []
            else:
                meta[key] = val.strip("'\"")
                current_key = None
        elif line.startswith("- ") and current_key:
            meta[current_key].append(line[2:].strip().strip("'\""))

    return meta, body


class SkillManifest(BaseModel):
    """Manifesto estruturado de uma skill do framework."""

    name: str
    description: str = ""
    path: str = ""
    content: str = ""
    triggers: list[str] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path) -> SkillManifest:
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        name = str(meta.get("name") or p.parent.name)
        desc = str(meta.get("description") or "")
        triggers = meta.get("triggers")
        if isinstance(triggers, list):
            trig_list = [str(t) for t in triggers]
        elif isinstance(triggers, str):
            trig_list = [triggers]
        else:
            trig_list = []

        return cls(
            name=name,
            description=desc,
            path=str(p.resolve()),
            content=body,
            triggers=trig_list,
        )
