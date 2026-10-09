"""Rolagem do chat: o usuário controla a tela.

Regressão do efeito colateral do fix de copiar/colar: com o mouse da TUI
desligado, roda do mouse, scrollbar e PageUp morriam — a tela ficava presa
seguindo o texto novo. Agora: mouse ATIVO (roda/scrollbar), PageUp/PageDown/
Home/End no teclado, e auto-follow que respeita o usuário (texto novo só
arrasta a tela quando ele está no fim).
"""

import asyncio

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient
from bombe_code.tui.widgets.parts_view import ChatView


def _app(tmp_path):
    return BombeTuiApp(
        client=BombeClient("http://127.0.0.1:9999"),
        session_id="ses_rolagem",
        project_dir=str(tmp_path),
    )


def test_usuario_sobe_e_o_texto_novo_nao_arrasta(tmp_path):
    """PageUp → usuário saiu do fim → montagem de widget novo NÃO cola no fim;
    End (ou voltar ao fim) → auto-follow religa."""

    async def cenario():
        app = _app(tmp_path)
        async with app.run_test(size=(100, 30)) as pilot:
            chat = app.query_one("#chat-view", ChatView)
            for i in range(80):
                await chat.mount_await_se_necessario(i) if False else None
            # monta bastante conteúdo
            from textual.widgets import Static

            for i in range(80):
                chat.mount(Static(f"linha {i}\n" + "conteúdo\n" * 3))
            await pilot.pause()
            assert chat.scroll_offset.y > 0, "deveria ter seguido o conteúdo novo"

            # Usuário aperta PageUp: sai do fim, texto novo não arrasta
            chat.pagina("up")
            await pilot.pause()
            assert chat.scroll_offset.y < chat.max_scroll_y, "pageup não subiu"
            assert chat._seguir is False, "sair do fim deveria desligar o auto-follow"

            y_apos_pageup = chat.scroll_offset.y
            chat.mount(Static("texto novo que não deve arrastar\n" + "x\n" * 5))
            await pilot.pause()
            assert chat.scroll_offset.y == y_apos_pageup, (
                "texto novo arrastou a tela com o usuário longe do fim"
            )

            # Usuário volta ao fim (End): auto-follow religa
            chat.pagina("bottom")
            await pilot.pause()
            assert chat._seguir is True, "voltar ao fim deveria religar o auto-follow"
            chat.mount(Static("novo texto com follow ativo\n"))
            await pilot.pause()
            assert chat.scroll_offset.y >= chat.max_scroll_y - 2, "auto-follow não colou no fim"

    asyncio.run(cenario())


def test_pageup_pagedown_via_teclado(tmp_path):
    """Os bindings pageup/pagedown chegam ao ChatView (não morrem no input)."""

    async def cenario():
        app = _app(tmp_path)
        async with app.run_test(size=(100, 30)) as pilot:
            chat = app.query_one("#chat-view", ChatView)
            from textual.widgets import Static

            for i in range(80):
                chat.mount(Static(f"linha {i}\n" + "conteúdo\n" * 3))
            await pilot.pause()

            await pilot.press("pageup")
            await pilot.pause()
            assert chat.scroll_offset.y < chat.max_scroll_y, "pageup do teclado não subiu"
            assert chat._seguir is False

            await pilot.press("pagedown")
            await pilot.press("pagedown")
            await pilot.press("pagedown")
            await pilot.pause()
            assert chat._seguir is True, "voltar ao fim (pagedown) deveria religar o follow"

    asyncio.run(cenario())
