"""TESTE NA TUI VIVA (app real):
1º Ctrl+C → só AVISA (não despeja a transcrição) e o app CONTINUA aberto.
2º Ctrl+C seguido → sai graceful.
Copiar a transcrição é F2 (tecla que existe de verdade)."""

import pyperclip
import pytest

from bombe_code.tui.app import BombeTuiApp
from bombe_code.tui.client import BombeClient


@pytest.mark.anyio
async def test_primeiro_ctrl_c_nao_copia_e_app_continua_vivo(tmp_path, monkeypatch):
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_ctrl", project_dir=str(tmp_path))
    copiado: dict[str, str] = {}
    monkeypatch.setattr(type(app), "copy_to_clipboard", lambda self, t: copiado.update(text=t))
    monkeypatch.setattr(pyperclip, "copy", lambda t: copiado.update(local=t))

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.press("ctrl+c")
        await pilot.pause(0.3)
        assert app.is_running, "app fechou no 1º Ctrl+C!"
        assert not copiado, "1º Ctrl+C NÃO deve despejar a transcrição (só avisa)"

    # app seguiu vivo após o contexto (fechamento explícito fora dele)


@pytest.mark.anyio
async def test_ctrl_c_duplo_sai(tmp_path):
    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_ctrl", project_dir=str(tmp_path))

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.press("ctrl+c")
        await pilot.pause(0.1)
        await pilot.press("ctrl+c")
        await pilot.pause(1.0)

    # Fora do run_test: o 2º Ctrl+C fechou o app (graceful)
    assert not app.is_running, "2º Ctrl+C deveria fechar"
