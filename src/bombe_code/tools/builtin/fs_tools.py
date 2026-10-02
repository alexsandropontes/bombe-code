from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel

from ...permissions.shell_scan import is_external
from ...permissions.stage_guard import validate_stage_permission
from ..base import ToolContext, ToolDef


class ReadArgs(BaseModel):
    path: str


class WriteArgs(BaseModel):
    path: str
    content: str


class EditArgs(BaseModel):
    path: str
    old_string: str
    new_string: str


class GlobArgs(BaseModel):
    pattern: str
    path: str = ""


class GrepArgs(BaseModel):
    pattern: str
    path: str = ""


class ApplyPatchArgs(BaseModel):
    path: str
    diff: str


def _check_external(path: str, ctx: ToolContext) -> str | None:
    denied = (
        ctx.project_dir
        and is_external(path, ctx.project_dir)
        and str(ctx.ask("external_directory", path)) == "deny"
    )
    if denied:
        return f"Erro: permissao negada para fora do worktree: {path}"
    return None


def _read(args: dict, ctx: ToolContext) -> str:
    target = Path(args["path"])
    denied = _check_external(str(target), ctx)
    if denied:
        return denied
    if not target.is_file():
        return f"Erro: arquivo nao encontrado: {target}"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(f"{index:6}\t{line}" for index, line in enumerate(lines, 1))


def _write(args: dict, ctx: ToolContext) -> str:
    target = Path(args["path"])
    denied = _check_external(str(target), ctx)
    if denied:
        return denied
    allowed, stage_reason = validate_stage_permission(
        getattr(ctx, "stage", "DISCUSS"), "write", str(target), ctx.project_dir
    )
    if not allowed:
        return stage_reason or "Erro: operacao bloqueada pelas regras da etapa atual"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(args["content"], encoding="utf-8")
    from ...formatters.runner import format_code_file

    format_code_file(target, cwd=ctx.project_dir or ".")
    return f"Arquivo escrito: {target} ({len(args['content'])} chars)"


def _edit(args: dict, ctx: ToolContext) -> str:
    target = Path(args["path"])
    denied = _check_external(str(target), ctx)
    if denied:
        return denied
    allowed, stage_reason = validate_stage_permission(
        getattr(ctx, "stage", "DISCUSS"), "edit", str(target), ctx.project_dir
    )
    if not allowed:
        return stage_reason or "Erro: operacao bloqueada pelas regras da etapa atual"
    if not target.is_file():
        return f"Erro: arquivo nao encontrado: {target}"

    text = target.read_text(encoding="utf-8")
    old = args["old_string"]
    count = text.count(old)
    if count == 0:
        return f"Erro: old_string nao encontrada em {target}: {old!r}"
    if count > 1:
        return f"Erro: old_string ambigua ({count} ocorrencias) em {target}"
    target.write_text(text.replace(old, args["new_string"], 1), encoding="utf-8")
    from ...formatters.runner import format_code_file

    format_code_file(target, cwd=ctx.project_dir or ".")
    return f"Editado: {target}"


def _glob(args: dict, ctx: ToolContext) -> str:
    base = Path(args["path"]) if args["path"] else Path(ctx.project_dir or ".")
    denied = _check_external(str(base), ctx)
    if denied:
        return denied
    matches = sorted(str(p) for p in base.glob(args["pattern"]))
    return "\n".join(matches) if matches else "Nenhum arquivo"


def _grep(args: dict, ctx: ToolContext) -> str:
    base = Path(args["path"]) if args["path"] else Path(ctx.project_dir or ".")
    denied = _check_external(str(base), ctx)
    if denied:
        return denied
    pattern = args["pattern"]
    if shutil.which("rg"):
        proc = subprocess.run(
            ["rg", "-n", "--no-heading", "-e", pattern, str(base)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.stdout.strip():
            return proc.stdout
        return f"Nenhum resultado para {pattern!r}"
    return _grep_python(base, pattern)


def _grep_python(base: Path, pattern: str) -> str:
    out: list[str] = []
    try:
        regex = re.compile(pattern)
    except re.error:
        regex = re.compile(re.escape(pattern))
    for file in sorted(base.rglob("*")):
        if not file.is_file():
            continue
        try:
            content = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for index, line in enumerate(content.splitlines(), 1):
            if regex.search(line):
                try:
                    shown = file.relative_to(base)
                except ValueError:
                    shown = file
                out.append(f"{shown}:{index}:{line}")
    return "\n".join(out) if out else f"Nenhum resultado para {pattern!r}"


def _parse_hunks(diff: str) -> list[tuple[int, list[str], list[str]]]:
    hunks: list[tuple[int, list[str], list[str]]] = []
    rows = diff.splitlines()
    index = 0
    while index < len(rows):
        line = rows[index]
        if line.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", line)
            if match is None:
                raise ValueError(f"cabecalho de hunk invalido: {line!r}")
            old_start = int(match.group(1))
            index += 1
            old_rows: list[str] = []
            new_rows: list[str] = []
            while index < len(rows) and not rows[index].startswith("@@"):
                row = rows[index]
                if row.startswith(" "):
                    old_rows.append(row[1:])
                    new_rows.append(row[1:])
                elif row.startswith("-"):
                    old_rows.append(row[1:])
                elif row.startswith("+"):
                    new_rows.append(row[1:])
                elif row.startswith("\\"):
                    pass
                else:
                    break
                index += 1
            hunks.append((old_start, old_rows, new_rows))
        else:
            index += 1
    return hunks


def _apply_unified(lines: list[str], diff: str) -> list[str]:
    out = list(lines)
    delta = 0
    for old_start, old_rows, new_rows in _parse_hunks(diff):
        start = old_start - 1 + delta
        current = out[start : start + len(old_rows)]
        if current != old_rows:
            raise ValueError(
                f"diff nao confere com o arquivo no hunk @{old_start}: "
                f"esperado {old_rows!r}, obtido {current!r}"
            )
        out[start : start + len(old_rows)] = new_rows
        delta += len(new_rows) - len(old_rows)
    return out


def _apply_patch(args: dict, ctx: ToolContext) -> str:
    target = Path(args["path"])
    denied = _check_external(str(target), ctx)
    if denied:
        return denied
    allowed, stage_reason = validate_stage_permission(
        getattr(ctx, "stage", "DISCUSS"), "patch", str(target), ctx.project_dir
    )
    if not allowed:
        return stage_reason or "Erro: operacao bloqueada pelas regras da etapa atual"
    if not target.is_file():
        return f"Erro: arquivo nao encontrado: {target}"

    lines = target.read_text(encoding="utf-8").splitlines()
    try:
        updated = _apply_unified(lines, args["diff"])
    except ValueError as exc:
        return f"Erro ao aplicar patch: {exc}"
    target.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return f"Patch aplicado: {target}"


READ_TOOL = ToolDef(id="read", description="Le um arquivo", parameters=ReadArgs, execute=_read)
WRITE_TOOL = ToolDef(
    id="write", description="Escreve um arquivo", parameters=WriteArgs, execute=_write
)
EDIT_TOOL = ToolDef(
    id="edit", description="Substitui string exata", parameters=EditArgs, execute=_edit
)
GLOB_TOOL = ToolDef(
    id="glob", description="Lista arquivos por padrao", parameters=GlobArgs, execute=_glob
)
GREP_TOOL = ToolDef(
    id="grep", description="Busca texto com caminho:linha", parameters=GrepArgs, execute=_grep
)
APPLY_PATCH_TOOL = ToolDef(
    id="apply_patch",
    description="Aplica diff unificado",
    parameters=ApplyPatchArgs,
    execute=_apply_patch,
)
