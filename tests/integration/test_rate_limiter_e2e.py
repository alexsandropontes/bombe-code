from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bombe_code.features.rate_limiter import TokenBucketRateLimiter
from bombe_code.local.contracts import ModelStatus
from bombe_code.local.local_manager import LocalModelManager
from bombe_code.local.vram_gate import VRAMGate
from bombe_code.routing.classifier import ComplexityAnalysis
from bombe_code.routing.router import HybridRouter


class DummyProcess:
    """Subprocesso mock para o llama-server durante o fluxo E2E."""

    def __init__(self, cmd: list[str]) -> None:
        self.cmd = cmd
        self.pid = 4242

    def poll(self) -> int | None:
        return None

    def terminate(self) -> None:
        pass


def test_rate_limiter_e2e_full_flow(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Valida o fluxo E2E: Roteamento -> Ativação MTP Local -> Limitação via Token Bucket."""
    caplog.set_level(logging.INFO)

    # 1. Configura modelo dummy para testes
    model_file = tmp_path / "qwen-3.8-9b.gguf"
    model_file.touch()

    executed_commands: list[list[str]] = []

    def mock_popen(cmd: list[str], env: dict[str, str] | None = None) -> DummyProcess:
        executed_commands.append(cmd)
        return DummyProcess(cmd)

    def mock_http_get(url: str) -> int:
        if "/health" in url:
            return 200
        return 404

    import subprocess

    gate = VRAMGate(
        runner=lambda _cmd: subprocess.CompletedProcess(args=[], returncode=0, stdout="120\n")
    )
    manager = LocalModelManager(
        binary_path=Path("/bin/llama-server"),
        vram_gate=gate,
        popen_fn=mock_popen,
        http_get_fn=mock_http_get,
    )

    router = HybridRouter(local_manager=manager, http_get_fn=mock_http_get)

    # 2. Roteamento via HybridRouter para slice Pleno
    analysis = ComplexityAnalysis(
        score=2,
        recommended_tier="pleno",
        reasons=["Slice com complexidade moderada requerendo Qwen 9B local"],
    )
    decision = router.route(analysis)
    assert decision.provider_name == "vllm-local"
    assert decision.model_name == "qwen-9b"
    assert decision.tier == "pleno"

    # 3. Ativação do modelo local com MTP verificado no comando
    router.ensure_local_model_ready(decision.model_name, port=18094)
    assert manager.status == ModelStatus.READY
    assert len(executed_commands) == 1

    cmd = executed_commands[0]
    assert "--spec-type" in cmd
    spec_idx = cmd.index("--spec-type")
    assert cmd[spec_idx + 1] == "draft-mtp"
    assert "--spec-draft-n-max" in cmd

    # 4. Execução de chamadas protegidas pelo TokenBucketRateLimiter
    logger = logging.getLogger("bombe_code.benchmark")
    logger.info("Comando gerado com sucesso contendo flag MTP: %s", " ".join(cmd))

    # Capacidade: 3 tokens, taxa baixa para evitar recarga imediata
    rate_limiter = TokenBucketRateLimiter(refill_rate=0.01, capacity=3.0)

    successful_inferences = 0
    throttled_requests = 0

    for req_id in range(1, 6):
        if rate_limiter.consume(1):
            successful_inferences += 1
            logger.info("Requisição %d autorizada e processada pelo modelo local MTP.", req_id)
        else:
            throttled_requests += 1
            logger.warning("Requisição %d interceptada pelo TokenBucketRateLimiter (Rate Limit Exceeded).", req_id)

    assert successful_inferences == 3
    assert throttled_requests == 2

    # 5. Validação das evidências nos logs
    log_text = caplog.text
    assert "Inicializando modelo local" in log_text
    assert "--spec-type draft-mtp" in log_text
    assert "interceptada pelo TokenBucketRateLimiter" in log_text
    assert "Requisição 1 autorizada" in log_text
    assert "Requisição 4 interceptada" in log_text
