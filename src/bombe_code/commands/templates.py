"""Modelos e renderização de templates de comandos customizados."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from ..skills.manifest import parse_frontmatter


class CustomCommand(BaseModel):
    """Representa um comando customizado definido em Markdown."""

    name: str
    description: str = ""
    template: str = ""
    path: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> CustomCommand:
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        name = p.stem
        desc = str(meta.get("description") or f"Comando customizado {name}")
        return cls(
            name=name,
            description=desc,
            template=body.strip(),
            path=str(p.resolve()),
        )


def render_command_template(template: str, arguments: str = "", file_path: str = "") -> str:
    """Substitui variáveis dinâmicas no template do comando."""
    rendered = template

    # Substitui $ARGUMENTS e $ARGS
    rendered = rendered.replace("$ARGUMENTS", arguments).replace("$ARGS", arguments)

    # Substitui $FILE
    rendered = rendered.replace("$FILE", file_path)

    # Substitui argumentos posicionais $1, $2, etc.
    arg_parts = arguments.split()
    for idx, arg in enumerate(arg_parts, 1):
        rendered = rendered.replace(f"${idx}", arg)

    # Remove marcadores posicionais não preenchidos (ex: $3 sem terceiro argumento)
    rendered = re.sub(r"\$\d+", "", rendered)

    return rendered.strip()
