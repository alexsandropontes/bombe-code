"""Testes unitários para a Feature 20: custom-commands (RED phase)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bombe_code.commands.loader import load_custom_commands
from bombe_code.commands.templates import CustomCommand, render_command_template


def test_render_command_template_variables():
    tmpl = "Explique o código em $FILE para $ARGUMENTS. Detalhe: $1 e $2."
    rendered = render_command_template(
        tmpl,
        arguments="um iniciante e avançado",
        file_path="src/main.py",
    )
    assert "src/main.py" in rendered
    assert "um iniciante e avançado" in rendered
    assert "Detalhe: um e iniciante." in rendered


def test_load_custom_commands_from_directory(tmp_path: Path):
    cmd_dir = tmp_path / ".bombe" / "commands"
    cmd_dir.mkdir(parents=True)

    test_cmd = cmd_dir / "explain.md"
    test_cmd.write_text(
        """---
description: Explicar arquivo de código
---
Por favor explique detalhadamente o arquivo $FILE com foco em $ARGUMENTS.
""",
        encoding="utf-8",
    )

    cmds = load_custom_commands(str(tmp_path))
    assert "explain" in cmds
    cmd = cmds["explain"]
    assert isinstance(cmd, CustomCommand)
    assert cmd.name == "explain"
    assert cmd.description == "Explicar arquivo de código"
    assert "$FILE" in cmd.template


@pytest.mark.anyio
async def test_tui_executes_custom_command(tmp_path: Path):
    cmd_dir = tmp_path / ".bombe" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "audit.md").write_text("Auditar escopo: $ARGUMENTS", encoding="utf-8")

    from bombe_code.tui.app import BombeTuiApp
    from bombe_code.tui.client import BombeClient

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test", project_dir=str(tmp_path))

    async with app.run_test():
        from bombe_code.tui.commands import handle_slash_command

        handled = await handle_slash_command(app, "/audit segurança e autenticação")
        assert handled is True
