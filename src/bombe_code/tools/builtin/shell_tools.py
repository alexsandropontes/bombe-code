from __future__ import annotations

import subprocess

from pydantic import BaseModel

from ...permissions.shell_scan import scan_shell_command
from ..base import ToolContext, ToolDef


class ShellArgs(BaseModel):
    command: str
    timeout: int = 120


def _shell(args: dict, ctx: ToolContext) -> str:
    for base in scan_shell_command(args["command"]):
        if str(ctx.ask("bash", base)) == "deny":
            return f"Erro: permissao negada para bash: {base}"
    try:
        proc = subprocess.run(
            ["bash", "-c", args["command"]],
            capture_output=True,
            text=True,
            timeout=args["timeout"],
            cwd=ctx.project_dir or None,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"Erro: timeout apos {args['timeout']}s"
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        output += f"\n[exit code {proc.returncode}]"
    return output or "(sem output)"


SHELL_TOOL = ToolDef(
    id="shell", description="Executa comando shell no projeto", parameters=ShellArgs, execute=_shell
)
