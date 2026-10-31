from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bombe_code.local.contracts import ModelProfile, ModelStatus
from bombe_code.local.local_manager import LocalModelManager
from bombe_code.local.profiles import ModelKey
from bombe_code.routing.router import HybridRouter


def test_ensure_local_model_ready_raises_when_no_manager() -> None:
    """Valida que chamar ensure_local_model_ready sem local_manager configurado levanta RuntimeError."""
    router = HybridRouter()
    with pytest.raises(RuntimeError, match="LocalModelManager is not configured on this HybridRouter"):
        router.ensure_local_model_ready("gemma-4b")


def test_ensure_local_model_ready_noop_when_already_ready_and_healthy() -> None:
    """Valida que não faz nada se o modelo correto já estiver com status READY e endpoint saudável."""
    manager = MagicMock(spec=LocalModelManager)
    manager.status = ModelStatus.READY
    active_profile = MagicMock(spec=ModelProfile)
    active_profile.name = "gemma-4-e4b"
    active_profile.port = 18094
    active_profile.host = "127.0.0.1"
    manager.active_profile = active_profile

    http_get_fn = MagicMock(return_value=200)

    router = HybridRouter(local_manager=manager, http_get_fn=http_get_fn)
    router.ensure_local_model_ready("gemma-4b", port=18094)

    # Não deve ter chamado start nem stop
    manager.start_model.assert_not_called()
    manager.stop_model.assert_not_called()
    http_get_fn.assert_called_once_with("http://127.0.0.1:18094/health")


def test_ensure_local_model_ready_starts_when_stopped() -> None:
    """Valida inicialização do modelo com MTP ativo quando o servidor está parado."""
    manager = MagicMock(spec=LocalModelManager)
    manager.status = ModelStatus.STOPPED
    manager.active_profile = None

    http_get_fn = MagicMock(return_value=0)

    router = HybridRouter(local_manager=manager, http_get_fn=http_get_fn)
    router.ensure_local_model_ready("gemma-4b", port=18094, timeout_seconds=60.0)

    manager.stop_model.assert_not_called()
    manager.start_model.assert_called_once()
    called_profile = manager.start_model.call_args[0][0]
    assert called_profile.port == 18094
    assert called_profile.name == "gemma-4-e4b"
    # MTP habilitado
    assert called_profile.spec_type == "draft-mtp"


def test_ensure_local_model_ready_switches_when_different_model_active() -> None:
    """Valida que para o modelo anterior e inicia o novo se houver modelo divergente ativo."""
    manager = MagicMock(spec=LocalModelManager)
    manager.status = ModelStatus.READY
    active_profile = MagicMock(spec=ModelProfile)
    active_profile.name = "qwen-3.8-9b"
    active_profile.port = 18094
    active_profile.host = "127.0.0.1"
    manager.active_profile = active_profile

    http_get_fn = MagicMock(return_value=200)

    router = HybridRouter(local_manager=manager, http_get_fn=http_get_fn)
    router.ensure_local_model_ready(ModelKey.GEMMA_4_E4B, port=18094)

    manager.stop_model.assert_called_once()
    manager.start_model.assert_called_once()
    called_profile = manager.start_model.call_args[0][0]
    assert called_profile.name == "gemma-4-e4b"


def test_ensure_local_model_ready_restarts_if_endpoint_unhealthy() -> None:
    """Valida reinicialização se o status do manager for READY mas o endpoint HTTP não responder 200."""
    manager = MagicMock(spec=LocalModelManager)
    manager.status = ModelStatus.READY
    active_profile = MagicMock(spec=ModelProfile)
    active_profile.name = "gemma-4-e4b"
    active_profile.port = 18094
    active_profile.host = "127.0.0.1"
    manager.active_profile = active_profile

    http_get_fn = MagicMock(return_value=503)

    router = HybridRouter(local_manager=manager, http_get_fn=http_get_fn)
    router.ensure_local_model_ready("gemma-4b", port=18094)

    manager.stop_model.assert_called_once()
    manager.start_model.assert_called_once()
