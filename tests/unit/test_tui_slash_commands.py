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


def test_command_help_catalog_has_all_commands():
    from bombe_code.tui.commands import COMMAND_HELP_CATALOG

    assert len(COMMAND_HELP_CATALOG) == 37
    commands = [c["name"].split()[0] for c in COMMAND_HELP_CATALOG]
    expected = [
        "/connect",
        "/models",
        "/sessions",
        "/new",
        "/compact",
        "/undo",
        "/redo",
        "/fork",
        "/share",
        "/unshare",
        "/export",
        "/copy",
        "/rename",
        "/timeline",
        "/help",
        "/init",
        "/review",
        "/themes",
        "/thinking",
        "/timestamps",
        "/details",
        "/editor",
        "/sidebar",
        "/agent",
        "/mcp",
        "/lsp",
        "/workspace",
        "/wave",
        "/project",
        "/snippet",
        "/mode",
        "/rca",
        "/simplify",
        "/task",
        "/report",
        "/exit",
        "/verbosity",
    ]
    for exp in expected:
        assert exp in commands


@pytest.mark.anyio
async def test_tui_slash_command_wave(tmp_path):
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test", project_dir=str(tmp_path))

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)

        # 1. /wave start ONDA-004
        inp.value = "/wave start ONDA-004"
        await pilot.press("enter")
        await pilot.pause(0.1)

        # 2. /wave status
        inp.value = "/wave status"
        await pilot.press("enter")
        await pilot.pause(0.1)


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


@pytest.mark.anyio
async def test_tui_slash_command_wave_plan_checks_prd_path_cleanly(tmp_path):
    """Valida que /wave plan avalia o caminho do PRD sem erro de NameError: Path is not defined."""
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")
    app.project_dir = str(tmp_path)

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        chat = app.query_one("#chat-view")

        inp.value = "/wave plan"
        await pilot.press("enter")
        await pilot.pause(0.1)

        # Sem PRD, deve exibir o aviso orientativo sem explodir NameError
        chat_texts = [str(w.render()) for w in chat.children]
        assert any("requer um PRD" in t for t in chat_texts)


@pytest.mark.anyio
async def test_tui_slash_command_wave_resume(tmp_path):
    """/wave resume retoma a onda persistida exatamente do checkpoint (subcomando literal)."""
    from bombe_code.storage.project_db import ProjectDatabase
    from bombe_code.turing.orchestrator import WaveOrchestrator
    from bombe_code.turing.state_machine import TuringStage

    db = ProjectDatabase(str(tmp_path))
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)
    orch.transition_to(TuringStage.EXECUTE)
    orch.transition_to(TuringStage.VALIDATE)

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test", project_dir=str(tmp_path))

    async with app.run_test() as pilot:
        chat = app.query_one("#chat-view", ChatView)
        inp = app.query_one("#prompt-input", PromptInput)

        inp.value = "/wave resume"
        await pilot.press("enter")
        await pilot.pause(0.3)

        conteudo = "\n".join(str(getattr(w, "content", "")) for w in chat.children)
        assert "retomada na etapa VALIDATE" in conteudo
        assert app.wave_station == "VALIDATE"

        # Onda inexistente → mensagem orientada, sem crash
        import sqlite3

        db2 = sqlite3.connect(str(tmp_path / ".bombe-code" / "state.db"))
        db2.execute("DELETE FROM wave_state")
        db2.commit()
        db2.close()

        inp.value = "/wave resume"
        await pilot.press("enter")
        await pilot.pause(0.3)
        conteudo = "\n".join(str(getattr(w, "content", "")) for w in chat.children)
        assert "Nenhuma ONDA persistida" in conteudo


@pytest.mark.anyio
async def test_tui_wave_resume_auto_cascateia_plan_sem_humano(tmp_path):
    """Em AUTO, o resume em PLAN encadeia /wave plan sozinho — o humano nunca
    digita o próximo comando (a plataforma não pede comando, só responde dúvida)."""
    from bombe_code.storage.project_db import ProjectDatabase
    from bombe_code.turing.orchestrator import WaveOrchestrator
    from bombe_code.turing.state_machine import TuringStage

    db = ProjectDatabase(str(tmp_path))
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="AUTO")
    orch.transition_to(TuringStage.PLAN)

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test", project_dir=str(tmp_path))

    async with app.run_test() as pilot:
        chat = app.query_one("#chat-view", ChatView)
        inp = app.query_one("#prompt-input", PromptInput)

        inp.value = "/wave resume"
        await pilot.press("enter")
        await pilot.pause(0.5)

        conteudo = "\n".join(str(getattr(w, "content", "")) for w in chat.children)
        # A cascatada disparou /wave plan sozinha (sem PRD → aviso didático da etapa,
        # que prova que o comando foi executado pela máquina, não pelo humano)
        assert "Retomando de PLAN — encadeando /wave plan" in conteudo
        assert "Etapa PLAN ativa — /wave plan" not in conteudo


@pytest.mark.anyio
async def test_tui_resume_semi_auto_cascata_continuacao(tmp_path):
    """SEMI-AUTO no resume: encadeia a continuação da etapa corrente (não é
    fronteira). MANUAL: nunca encadeia — apenas informa."""
    from bombe_code.storage.project_db import ProjectDatabase
    from bombe_code.turing.orchestrator import WaveOrchestrator
    from bombe_code.turing.state_machine import TuringStage

    db = ProjectDatabase(str(tmp_path))
    orch = WaveOrchestrator(project_dir=str(tmp_path), db=db)
    orch.start_wave("ONDA-001", autonomy_mode="SEMI_AUTO")
    orch.transition_to(TuringStage.PLAN)

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test", project_dir=str(tmp_path))

    async with app.run_test() as pilot:
        chat = app.query_one("#chat-view", ChatView)
        inp = app.query_one("#prompt-input", PromptInput)

        inp.value = "/wave resume"
        await pilot.press("enter")
        await pilot.pause(0.5)

        conteudo = "\n".join(str(getattr(w, "content", "")) for w in chat.children)
        assert "MODO SEMI-AUTO] Retomando de PLAN" in conteudo
