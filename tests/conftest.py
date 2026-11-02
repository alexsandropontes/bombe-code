"""Fixtures globais de isolamento da suíte."""

from pathlib import Path
import pytest

from bombe_code.turing.progress import ABORT_EVENT, BUS


@pytest.fixture(autouse=True)
def _isolar_estado_global():
    """ABORT_EVENT e verbosidade do BUS não vazam entre testes."""
    ABORT_EVENT.clear()
    BUS.set_verbosity("verbose")
    yield
    ABORT_EVENT.clear()
    BUS.set_verbosity("verbose")


@pytest.fixture(autouse=True)
def _isolar_models_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Garante que nenhum teste leia ou contamine a matriz de modelos persistida."""
    fake_matrix = tmp_path / "isolated_models_matrix.json"
    monkeypatch.setenv("BOMBE_MODELS_MATRIX_PATH", str(fake_matrix))
