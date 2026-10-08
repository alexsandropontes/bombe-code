"""PARIDADE OPENCODE nas teclas:
- Ctrl+C fecha o aplicativo (keybind do binário original)
- Ctrl+Shift+C/W NUNCA chegam ao app (acelerador do VTE) — nada neles
- Mouse-tracking DESLIGADO (tea.DisableMouse): seleção nativa sempre ok"""

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient


def test_bindings_opencode(tmp_path):
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_teclas", project_dir=str(tmp_path))

    acoes = {b.action for b in BombeTuiApp.BINDINGS}
    assert "quit" in acoes
    # Nenhuma ação inventada sobrevive:
    for proibida in (
        "copiar_tela",
        "colar_clipboard",
        "toggle_mouse",
        "ctrl_c_press",
        "copy_or_quit",
        "noop",
    ):
        assert proibida not in acoes, f"binding inventado sobreviveu: {proibida}"
    # Nenhuma binding para teclas que o VTE consome antes do app:
    for tecla_proibida in ("ctrl+shift+c", "ctrl+shift+v", "ctrl+shift+w", "f2", "f4"):
        for b in BombeTuiApp.BINDINGS:
            assert tecla_proibida not in (b.key or "").lower(), (
                f"binding para tecla consumida pelo VTE: {b.key}"
            )
