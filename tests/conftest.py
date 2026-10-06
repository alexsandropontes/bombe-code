"""Fixtures globais de isolamento da suíte."""

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
