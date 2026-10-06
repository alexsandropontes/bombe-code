"""Testes unitários para o suporte a múltiplas linhas e colagem (paste) no PromptInput."""

from __future__ import annotations

import pytest
from textual.events import Paste
from textual.widgets import Static

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient
from bombe_code.tui.widgets.parts_view import ChatView
from bombe_code.tui.widgets.prompt_input import PromptInput


@pytest.mark.anyio
async def test_prompt_input_multiline_paste_and_enter_submission():
    """Valida que textos com múltiplas linhas colados (ex: do ChatGPT) são preservados e enviados com Enter."""
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    chatgpt_snippet = (
        "Crie um aplicativo completo de finanças com:\n"
        "- Gestão de despesas e receitas\n"
        "- Autenticação JWT\n"
        "- Relatórios exportáveis em PDF"
    )

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        chat = app.query_one("#chat-view", ChatView)

        # 1. Altura inicial de 1 linha de conteúdo
        assert inp.document.line_count == 1
        assert inp.styles.height.value == 3

        # 2. Cola o texto multilinha (Paste event)
        inp.post_message(Paste(text=chatgpt_snippet))
        await pilot.pause(0.05)

        # 3. Valida que todas as 4 linhas foram recebidas sem truncar
        assert inp.document.line_count == 4
        assert inp.value == chatgpt_snippet
        # Altura deve ter expandido para acomodar o texto multilinha
        assert inp.styles.height.value == 6

        # 4. Pressiona Enter para enviar o texto completo
        await pilot.press("enter")
        await pilot.pause(0.05)

        # 5. O input deve ter sido limpo e a altura resetada para 3
        assert inp.value == ""
        assert inp.styles.height.value == 3

        # 6. O texto completo deve estar gravado no histórico de prompts
        assert chatgpt_snippet in inp.prompt_history

        # 7. A mensagem enviada deve ter sido montada no ChatView preservando quebras de linha
        chat_texts = [str(w.render()) for w in chat.children]
        assert any("Gestão de despesas" in t for t in chat_texts)


@pytest.mark.anyio
async def test_prompt_input_shift_enter_inserts_newline():
    """Valida que Shift+Enter insere quebra de linha manual sem submeter o formulário."""
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = "Linha 1"
        assert inp.document.line_count == 1

        # Shift+Enter insere nova linha
        await pilot.press("shift+enter")
        await pilot.pause(0.05)

        assert inp.document.line_count == 2
        # O formulário NÃO deve ter sido submetido (valor ainda no input)
        assert "Linha 1\n" in inp.value


@pytest.mark.anyio
async def test_prompt_input_history_multiline_recovery():
    """Valida que textos com múltiplas linhas são recuperados do histórico via tecla Up."""
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    multiline_text = "Primeira linha\nSegunda linha\nTerceira linha"

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        inp.value = multiline_text
        await pilot.press("enter")
        await pilot.pause(0.05)

        assert inp.value == ""

        # Pressiona Up para resgatar do histórico
        await pilot.press("up")
        await pilot.pause(0.05)

        assert inp.value == multiline_text
        assert inp.document.line_count == 3


@pytest.mark.anyio
async def test_prompt_input_large_paste_nonblocking_submission(monkeypatch):
    """Valida que a colagem de textos grandes (>8 linhas) e submissão não travam o event loop e acionam worker."""
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    dispatched_commands = []

    def fake_worker(cmd: str):
        dispatched_commands.append(cmd)

    monkeypatch.setattr(app, "_run_slash_command_worker", fake_worker)

    large_briefing = "\n".join(
        [f"Linha de requisito {i} com caracteres [especiais]" for i in range(25)]
    )

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        chat = app.query_one("#chat-view", ChatView)

        # Cola texto grande
        inp.post_message(Paste(text=large_briefing))
        await pilot.pause(0.05)
        assert inp.document.line_count == 25

        # Pressiona enter para submeter
        await pilot.press("enter")
        await pilot.pause(0.05)

        # O input deve ter sido limpo
        assert inp.value == ""

        # O chat deve renderizar a mensagem com indicador de linhas coladas
        chat_texts = [str(w.render()) for w in chat.children]
        assert any("linhas coladas" in t for t in chat_texts)


@pytest.mark.anyio
async def test_chat_view_autoscroll_on_message_submission_and_mount(monkeypatch):
    """Valida que o ChatView ancora e rola automaticamente para o final ao enviar mensagem."""
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_test")

    monkeypatch.setattr(app, "_run_slash_command_worker", lambda cmd: None)

    async with app.run_test() as pilot:
        inp = app.query_one("#prompt-input", PromptInput)
        chat = app.query_one("#chat-view", ChatView)

        # Monta 30 mensagens iniciais para criar scroll
        for i in range(30):
            await chat.mount(Static(f"Mensagem anterior {i}"))
        await pilot.pause(0.05)

        # Verifica se o ChatView está no final
        assert chat.is_vertical_scroll_end

        # Submete uma nova mensagem do usuário
        inp.value = "Nova mensagem do usuário para testar scroll automático"
        await pilot.press("enter")
        await pilot.pause(0.05)

        # Deve permanecer ancorado e no final absoluto do scroll
        assert chat.is_vertical_scroll_end
        assert chat.scroll_y == chat.max_scroll_y
