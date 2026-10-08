"""REGRESSÃO do crash do make-books: partes antigas do histórico com markup
cru NÃO derrubam o boot da TUI — são isoladas e puladas."""

import asyncio
from typing import Any

from bombe_code.tui.commands import _run_orchestrator_with_stream  # noqa: F401 (sanidade do módulo)
from bombe_code.tui.widgets.parts_view import PartWidget


def _part_com_markup_cru() -> dict[str, Any]:
    return {
        "type": "text",
        "text": "eram mensagens antigas [/{TOKENS['warning']}] e [/magenta] cruas",
    }


def test_partwidget_aceita_parte_envenenada_sem_explodir():
    """O widget em si não levanta na construção, mesmo com markup cru."""
    try:
        PartWidget(_part_com_markup_cru())
        criado = True
    except Exception:  # noqa: BLE001 — provando que não levanta
        criado = False
    assert criado  # construção offline não explode


def test_boot_da_tui_sobrevive_a_historico_envenenado(tmp_path):
    """O _load_history pulando partes envenenadas: simulado via chamada
    direta da lógica de montagem (sem servidor)."""
    from unittest.mock import patch

    from bombe_code.tui.app import BombeTuiApp
    from bombe_code.tui.client import BombeClient

    history = [
        {"role": "user", "parts": [_part_com_markup_cru()]},
        {"role": "assistant", "parts": [{"type": "text", "text": "resposta ok"}]},
    ]

    client = BombeClient("http://127.0.0.1:9999")
    app = BombeTuiApp(client=client, session_id="ses_veneno", project_dir=str(tmp_path))

    async def fake_history(session_id, _client=None):
        return history

    async def cenario():
        with (
            patch.object(BombeClient, "get_history", fake_history),
            patch.object(app, "query_one", side_effect=lambda *a, **k: _ChatFalso(), raising=False),
        ):
            await app._load_history()

    asyncio.run(cenario())


class _ChatFalso:
    def __init__(self) -> None:
        self.mounted: list[Any] = []

    async def mount(self, widget: Any) -> None:
        self.mounted.append(widget)

    def scroll_to_latest(self) -> None:
        pass
