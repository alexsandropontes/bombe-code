import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bombe_code.local.contracts import (
    ModelConcurrencyError,
    ModelProfile,
    ModelStartupTimeoutError,
    ModelStatus,
    NvidiaSmiNotFoundError,
    VRAMThresholdExceededError,
)
from bombe_code.local.local_manager import LocalModelManager
from bombe_code.local.vram_gate import VRAMGate


class FakeProcess:
    """Processo simulado para testes determinísticos de subprocess."""

    def __init__(self, exit_after_polls: int = 1, pid: int = 4242) -> None:
        self.pid = pid
        self._polls_left = exit_after_polls
        self.terminated = False
        self.killed = False
        self.waited = False

    def poll(self) -> int | None:
        if self._polls_left <= 0:
            return 0
        self._polls_left -= 1
        return None

    def terminate(self) -> None:
        self.terminated = True
        self._polls_left = 0

    def kill(self) -> None:
        self.killed = True
        self._polls_left = 0

    def wait(self, timeout: float | None = None) -> int:
        self.waited = True
        return 0


# =========================================================================
# TESTES DO VRAMGate
# =========================================================================


def test_vram_gate_query_parses_used_vram() -> None:
    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="245\n", stderr="")

    gate = VRAMGate(runner=fake_runner)
    assert gate.query_used_vram_mb() == 245


def test_vram_gate_query_multi_gpu() -> None:
    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="180 MiB\n120\n", stderr=""
        )

    gate = VRAMGate(runner=fake_runner)
    assert gate.query_used_vram_mb() == 300


def test_vram_gate_nvidia_smi_not_found_returns_zero_when_not_strict() -> None:
    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("nvidia-smi not found")

    gate = VRAMGate(runner=fake_runner, strict=False)
    assert gate.query_used_vram_mb() == 0


def test_vram_gate_nvidia_smi_not_found_raises_when_strict() -> None:
    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("nvidia-smi not found")

    gate = VRAMGate(runner=fake_runner, strict=True)
    with pytest.raises(NvidiaSmiNotFoundError):
        gate.query_used_vram_mb()


def test_vram_gate_assert_clean_success() -> None:
    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="250\n", stderr="")

    gate = VRAMGate(runner=fake_runner)
    gate.assert_clean(max_used_mb=300)


def test_vram_gate_assert_clean_exceeded() -> None:
    def fake_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="350\n", stderr="")

    gate = VRAMGate(runner=fake_runner)
    with pytest.raises(VRAMThresholdExceededError) as exc_info:
        gate.assert_clean(max_used_mb=300)
    assert "350 MiB" in str(exc_info.value)
    assert "300 MiB" in str(exc_info.value)


# =========================================================================
# TESTES DO LocalModelManager
# =========================================================================


def test_local_manager_cli_command_building() -> None:
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="50"))
    manager = LocalModelManager(
        binary_path=Path("/custom/bin/llama-server"),
        vram_gate=gate,
    )

    profile = ModelProfile(
        name="qwen-test",
        model_path=Path("/models/qwen.gguf"),
        context_size=65536,
        port=19001,
        host="0.0.0.0",
        n_gpu_layers=99,
        flash_attention=True,
        kv_cache_type="q8_0",
        extra_args=("--draft-max", "16"),
    )

    cmd = manager.build_cli_command(profile)
    assert cmd == [
        "/custom/bin/llama-server",
        "-m",
        "/models/qwen.gguf",
        "-c",
        "65536",
        "--port",
        "19001",
        "--host",
        "0.0.0.0",
        "-ngl",
        "99",
        "-fa",
        "on",
        "-ctk",
        "q8_0",
        "-ctv",
        "q8_0",
        "--draft-max",
        "16",
    ]


def test_local_manager_cli_command_no_flash_attention() -> None:
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="50"))
    manager = LocalModelManager(
        binary_path=Path("/bin/llama-server"),
        vram_gate=gate,
    )

    profile = ModelProfile(
        name="gemma-test",
        model_path=Path("/models/gemma.gguf"),
        flash_attention=False,
        kv_cache_type="",
    )

    cmd = manager.build_cli_command(profile)
    assert "-fa" in cmd
    assert cmd[cmd.index("-fa") + 1] == "off"
    assert "-ctk" not in cmd


def test_local_manager_build_environment() -> None:
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="50"))
    manager = LocalModelManager(
        extra_ld_library_path="/opt/cuda/lib",
        vram_gate=gate,
    )

    profile = ModelProfile(
        name="env-test",
        model_path=Path("/models/model.gguf"),
        env_vars=(("CUSTOM_KEY", "custom_val"), ("FOO", "BAR")),
    )

    env = manager.build_environment(profile)
    assert "/opt/cuda/lib" in env["LD_LIBRARY_PATH"]
    assert env["CUSTOM_KEY"] == "custom_val"
    assert env["FOO"] == "BAR"


def test_local_manager_start_concurrency_error() -> None:
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="50"))
    manager = LocalModelManager(vram_gate=gate)
    manager._status = ModelStatus.READY
    manager._active_process = FakeProcess()

    profile = ModelProfile(name="model-2", model_path=Path("/models/m2.gguf"))
    with pytest.raises(ModelConcurrencyError):
        manager.start_model(profile)


def test_local_manager_start_model_success() -> None:
    current_time = 1000.0

    def fake_time() -> float:
        nonlocal current_time
        return current_time

    def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds

    http_calls = 0

    def fake_http_get(url: str) -> int:
        nonlocal http_calls
        http_calls += 1
        return 200 if http_calls >= 2 else 503

    proc = FakeProcess(exit_after_polls=99)
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="100"))

    manager = LocalModelManager(
        vram_gate=gate,
        popen_fn=lambda cmd, env: proc,
        http_get_fn=fake_http_get,
        sleep_fn=fake_sleep,
        time_fn=fake_time,
    )

    profile = ModelProfile(name="test-ready", model_path=Path("/models/m.gguf"))
    manager.start_model(profile, timeout_seconds=10.0)

    assert manager.status == ModelStatus.READY
    assert manager.active_profile == profile
    assert manager.active_process is proc
    assert http_calls >= 2


def test_local_manager_start_model_timeout_cleans_up() -> None:
    current_time = 1000.0

    def fake_time() -> float:
        nonlocal current_time
        return current_time

    def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds

    proc = FakeProcess(exit_after_polls=99)
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="100"))

    manager = LocalModelManager(
        vram_gate=gate,
        popen_fn=lambda cmd, env: proc,
        http_get_fn=lambda url: 503,
        sleep_fn=fake_sleep,
        time_fn=fake_time,
    )

    profile = ModelProfile(name="timeout-test", model_path=Path("/models/m.gguf"))
    with pytest.raises(ModelStartupTimeoutError) as exc_info:
        manager.start_model(profile, timeout_seconds=5.0)

    assert "Tempo limite" in str(exc_info.value)
    assert manager.status == ModelStatus.ERROR
    assert manager.active_process is None
    assert proc.terminated is True


def test_local_manager_start_model_premature_exit() -> None:
    current_time = 1000.0

    def fake_time() -> float:
        nonlocal current_time
        return current_time

    def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds

    # Processo retorna exit code 1 no primeiro poll
    crashed_proc = MagicMock()
    crashed_proc.poll.return_value = 1

    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="100"))
    manager = LocalModelManager(
        vram_gate=gate,
        popen_fn=lambda cmd, env: crashed_proc,
        http_get_fn=lambda url: 0,
        sleep_fn=fake_sleep,
        time_fn=fake_time,
    )

    profile = ModelProfile(name="crash-test", model_path=Path("/models/m.gguf"))
    with pytest.raises(ModelStartupTimeoutError) as exc_info:
        manager.start_model(profile, timeout_seconds=10.0)

    assert "exit code 1" in str(exc_info.value)
    assert manager.status == ModelStatus.ERROR


def test_local_manager_stop_model_graceful_sigterm() -> None:
    current_time = 1000.0

    def fake_time() -> float:
        nonlocal current_time
        return current_time

    def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds

    proc = FakeProcess(exit_after_polls=1)
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="50"))

    manager = LocalModelManager(
        vram_gate=gate,
        sleep_fn=fake_sleep,
        time_fn=fake_time,
    )
    manager._active_process = proc
    manager._active_profile = ModelProfile(name="active", model_path=Path("/m.gguf"))
    manager._status = ModelStatus.READY

    manager.stop_model(timeout_seconds=5.0)

    assert proc.terminated is True
    assert proc.killed is False
    assert manager.status == ModelStatus.STOPPED
    assert manager.active_process is None
    assert manager.active_profile is None


def test_local_manager_stop_model_forced_sigkill() -> None:
    current_time = 1000.0

    def fake_time() -> float:
        nonlocal current_time
        return current_time

    def fake_sleep(seconds: float) -> None:
        nonlocal current_time
        current_time += seconds

    class StubbornProcess:
        def __init__(self) -> None:
            self.pid = 999
            self.terminated = False
            self.killed = False

        def poll(self) -> int | None:
            if self.killed:
                return 0
            return None

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

        def wait(self, timeout: float | None = None) -> int:
            return 0

    proc = StubbornProcess()
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="50"))

    manager = LocalModelManager(
        vram_gate=gate,
        sleep_fn=fake_sleep,
        time_fn=fake_time,
    )
    manager._active_process = proc
    manager._active_profile = ModelProfile(name="stubborn", model_path=Path("/m.gguf"))
    manager._status = ModelStatus.READY

    manager.stop_model(timeout_seconds=2.0)

    assert proc.terminated is True
    assert proc.killed is True
    assert manager.status == ModelStatus.STOPPED
    assert manager.active_process is None


def test_local_manager_vram_barrier_blocks_startup() -> None:
    gate = VRAMGate(runner=lambda _: subprocess.CompletedProcess(args=[], returncode=0, stdout="350"))
    manager = LocalModelManager(vram_gate=gate)

    profile = ModelProfile(name="oom-test", model_path=Path("/models/m.gguf"))
    with pytest.raises(VRAMThresholdExceededError):
        manager.start_model(profile)

    assert manager.status == ModelStatus.STOPPED
    assert manager.active_process is None
