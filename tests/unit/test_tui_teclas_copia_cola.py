"""PARIDADE OPENCODE nas teclas:
- Ctrl+C 2× fecha o aplicativo (1º avisa, não despeja a transcrição)
- Mouse da TUI ATIVO: roda/scrollbar rolam o chat; seleção nativa de texto
  via Shift+arrastar (VTE); Ctrl+Shift+C é consumido pelo VTE (seleção)
- F2 copia a transcrição (o hint de status aponta para tecla que EXISTE)
- Auto-follow: texto novo só arrasta a tela se o usuário está no fim"""

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient


def test_bindings_opencode(tmp_path):
    BombeTuiApp(
        client=BombeClient("http://127.0.0.1:9999"),
        session_id="ses_teclas",
        project_dir=str(tmp_path),
    )

    acoes = {b.action for b in BombeTuiApp.BINDINGS}
    assert "quit" in acoes  # Ctrl+C fecha (paridade opencode)
    # Rolagem do chat pelo teclado (a tela não fica mais presa no fim):
    assert "chat_page_up" in acoes
    assert "chat_page_down" in acoes
    assert "chat_page_top" in acoes
    assert "chat_page_bottom" in acoes
    # Copiar transcrição é ação REAL (F2): o hint não aponta mais o vazio:
    assert "copiar_tela" in acoes
    assert any((b.key or "").lower() == "f2" for b in BombeTuiApp.BINDINGS)
    # Nenhuma ação inventada sobrevive:
    for proibida in (
        "colar_clipboard",
        "toggle_mouse",
        "ctrl_c_press",
        "copy_text",
        "noop",
    ):
        assert proibida not in acoes, f"binding inventado sobreviveu: {proibida}"
    # Teclas que o VTE consome antes do app NÃO têm binding (seriam mortas):
    for tecla_proibida in ("ctrl+shift+c", "ctrl+shift+v", "ctrl+shift+w", "f4"):
        for b in BombeTuiApp.BINDINGS:
            assert tecla_proibida not in (b.key or "").lower(), (
                f"binding para tecla consumida pelo VTE: {b.key}"
            )
