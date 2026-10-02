"""Testes unitários para o roteamento de comandos de barra (slash commands) na TUI."""

from __future__ import annotations

import pytest

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient
from bombe_code.tui.widgets.parts_view import ChatView
from bombe_code.tui.widgets.prompt_input import PromptInput


@pytest.mark.anyio
async def test_tui_slash_command_help():
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/help"
        # Submete /help
        await pilot.press("enter")
        await pilot.pause(0.1)


@pytest.mark.anyio
async def test_tui_slash_command_models():
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/models openai/gpt-4o"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert app.model_name == "openai/gpt-4o"


@pytest.mark.anyio
@pytest.mark.anyio
async def test_tui_slash_command_models_modal_dialog():
    from bombe_code.tui.widgets.dialogs import ModelDialog

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/models"
        await pilot.press("enter")
        await pilot.pause(0.1)

        assert isinstance(app.screen, ModelDialog)
        await pilot.press("escape")
        await pilot.pause(0.1)
        assert not isinstance(app.screen, ModelDialog)


@pytest.mark.anyio
async def test_tui_slash_command_models_modal_selection(tmp_path, monkeypatch):
    from bombe_code.providers.auth import save_provider_url
    from bombe_code.tui.widgets.dialogs import ModelDialog

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    save_provider_url("llama.cpp", "http://127.0.0.1:8080/v1")

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/models"
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert isinstance(app.screen, ModelDialog)
        dialog = app.screen
        dialog.dismiss("llama.cpp/mimo-qwen-9b")
        await pilot.pause(0.1)

        assert app.model_name == "llama.cpp/mimo-qwen-9b"


@pytest.mark.anyio
async def test_tui_slash_command_clear():
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        chat = app.query_one("#chat-view", ChatView)
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/clear"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert len(chat.children) == 0


def test_command_help_catalog_has_28_commands():
    from bombe_code.tui.commands import COMMAND_HELP_CATALOG

    assert len(COMMAND_HELP_CATALOG) == 28
    commands = [c["name"].split()[0] for c in COMMAND_HELP_CATALOG]
    expected = [
        "/connect", "/models", "/sessions", "/new", "/compact",
        "/undo", "/redo", "/fork", "/share", "/unshare",
        "/export", "/copy", "/rename", "/timeline", "/help",
        "/init", "/review", "/themes", "/thinking", "/timestamps",
        "/details", "/editor", "/sidebar", "/agent", "/mcp",
        "/lsp", "/workspace", "/exit",
    ]
    for exp in expected:
        assert exp in commands


@pytest.mark.anyio
async def test_tui_slash_commands_toggles_and_agents():
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)

        # /thinking
        inp.value = "/thinking"
        await pilot.press("enter")
        await pilot.pause(0.05)

        # /timestamps
        inp.value = "/timestamps"
        await pilot.press("enter")
        await pilot.pause(0.05)

        # /details
        inp.value = "/details"
        await pilot.press("enter")
        await pilot.pause(0.05)

        # /agent plan
        inp.value = "/agent plan"
        await pilot.press("enter")
        await pilot.pause(0.05)
        assert app.agent_name == "plan"

        # /sidebar
        inp.value = "/sidebar"
        await pilot.press("enter")
        await pilot.pause(0.05)


@pytest.mark.anyio
async def test_tui_slash_command_connect_with_args(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from bombe_code.providers.auth import load_auth

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/connect llama.cpp http://127.0.0.1:8080/v1"
        await pilot.press("enter")
        await pilot.pause(0.1)

        auth = load_auth()
        assert "llama.cpp" in auth
        assert auth["llama.cpp"]["base_url"] == "http://127.0.0.1:8080/v1"


@pytest.mark.anyio
async def test_tui_connect_dialog_enter_submission(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    from textual.widgets import Input

    from bombe_code.providers.auth import load_auth
    from bombe_code.tui.widgets.dialogs import ConnectDialog

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/connect"
        await pilot.press("enter")
        await pilot.pause(0.1)

        assert isinstance(app.screen, ConnectDialog)
        prov_inp = app.screen.query_one("#connect-provider-input", Input)
        prov_inp.value = "ollama"
        await pilot.press("enter")  # deve focar no próximo campo
        await pilot.pause(0.05)

        val_inp = app.screen.query_one("#connect-value-input", Input)
        val_inp.value = "http://127.0.0.1:11434/v1"
        await pilot.press("enter")  # deve submeter o diálogo
        await pilot.pause(0.1)

        assert not isinstance(app.screen, ConnectDialog)
        auth = load_auth()
        assert "ollama" in auth
        assert auth["ollama"]["base_url"] == "http://127.0.0.1:11434/v1"


@pytest.mark.anyio
async def test_tui_slash_command_models_prioritizes_connected_and_recent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    from bombe_code.models.state import add_recent_model, get_recent_models
    from bombe_code.providers.auth import save_provider_url
    from bombe_code.tui.widgets.dialogs import ModelDialog

    # Configura servidor local e modelo recente
    save_provider_url("llama.cpp", "http://127.0.0.1:8080/v1")
    add_recent_model("llama.cpp/mimo-qwen-9b")

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "/models"
        await pilot.press("enter")
        await pilot.pause(0.2)

        assert isinstance(app.screen, ModelDialog)
        dialog = app.screen
        # Verifica se opções existem e recentes estão presentes
        categories = [opt[2] for opt in dialog.all_models]
        assert "Modelos Recentes" in categories

        # Submete selecionando via Enter
        await pilot.press("enter")
        await pilot.pause(0.1)

        # Verifica se o modelo selecionado foi registrado nos recentes
        assert "llama.cpp/mimo-qwen-9b" in get_recent_models()



