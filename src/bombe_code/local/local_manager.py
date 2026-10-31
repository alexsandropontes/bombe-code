import logging
import os
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from .contracts import (
    LocalModelError,
    ModelConcurrencyError,
    ModelProfile,
    ModelStartupTimeoutError,
    ModelStatus,
)
from .vram_gate import VRAMGate

logger = logging.getLogger(__name__)

DEFAULT_LLAMA_SERVER_BINARY = Path("/home/lexpontes/.unsloth/llama.cpp-b11985/llama-server")
DEFAULT_CUDA_LD_LIBRARY_PATH = (
    "/home/lexpontes/.unsloth/llama.cpp-b11985:"
    "/home/lexpontes/.unsloth/studio/unsloth_studio/lib/python3.13/site-packages/nvidia/cu13/lib"
)


class LocalModelManager:
    """Gerenciador de ciclo de vida e orquestração de processos do llama-server."""

    def __init__(
        self,
        binary_path: Path | None = None,
        extra_ld_library_path: str = DEFAULT_CUDA_LD_LIBRARY_PATH,
        vram_gate: VRAMGate | None = None,
        popen_fn: Callable[..., Any] | None = None,
        http_get_fn: Callable[[str], int] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.binary_path = binary_path or DEFAULT_LLAMA_SERVER_BINARY
        self.extra_ld_library_path = extra_ld_library_path
        self.vram_gate = vram_gate or VRAMGate()
        self.popen_fn = popen_fn or subprocess.Popen
        self.http_get_fn = http_get_fn or self._default_http_get
        self.sleep_fn = sleep_fn
        self.time_fn = time_fn

        self._active_profile: ModelProfile | None = None
        self._active_process: Any | None = None
        self._status: ModelStatus = ModelStatus.STOPPED

    @property
    def active_profile(self) -> ModelProfile | None:
        """Perfil do modelo atualmente carregado ou em inicialização."""
        return self._active_profile

    @property
    def active_process(self) -> Any | None:
        """Handle do subprocesso ativo."""
        return self._active_process

    @property
    def status(self) -> ModelStatus:
        """Status atual do servidor de modelo."""
        return self._status

    @staticmethod
    def _default_http_get(url: str) -> int:
        try:
            response = httpx.get(url, timeout=1.0)
            return response.status_code
        except (httpx.HTTPError, OSError) as err:
            logger.debug("Tentativa de health check falhou em %s: %s", url, err)
            return 0

    def build_cli_command(self, profile: ModelProfile) -> list[str]:
        """Monta a lista de argumentos de linha de comando para o llama-server."""
        cmd = [
            str(self.binary_path),
            "-m",
            str(profile.model_path),
            "-c",
            str(profile.context_size),
            "--port",
            str(profile.port),
            "--host",
            profile.host,
            "-ngl",
            str(profile.n_gpu_layers),
        ]

        if profile.flash_attention:
            cmd.extend(["-fa", "on"])
        else:
            cmd.extend(["-fa", "off"])

        if profile.kv_cache_type:
            cmd.extend(["-ctk", profile.kv_cache_type, "-ctv", profile.kv_cache_type])

        cmd.extend(list(profile.extra_args))
        return cmd

    def build_environment(self, profile: ModelProfile) -> dict[str, str]:
        """Configura o ambiente de execução injetando paths de CUDA e variáveis do perfil."""
        env = os.environ.copy()
        current_ld = env.get("LD_LIBRARY_PATH", "")

        if self.extra_ld_library_path:
            if current_ld:
                env["LD_LIBRARY_PATH"] = f"{self.extra_ld_library_path}:{current_ld}"
            else:
                env["LD_LIBRARY_PATH"] = self.extra_ld_library_path

        for key, val in profile.env_vars:
            env[key] = val

        return env

    def start_model(self, profile: ModelProfile, timeout_seconds: float = 120.0) -> None:
        """Inicializa uma instância de modelo no llama-server sob Fila Indiana estrita."""
        if self._active_process is not None or self._status in (
            ModelStatus.STARTING,
            ModelStatus.READY,
        ):
            active_name = self._active_profile.name if self._active_profile else "desconhecido"
            raise ModelConcurrencyError(
                f"Modelo '{active_name}' já está em execução ou inicializando. "
                "Finalize-o antes de iniciar um novo modelo."
            )

        self.vram_gate.assert_clean(300)

        cmd = self.build_cli_command(profile)
        env = self.build_environment(profile)

        self._status = ModelStatus.STARTING
        self._active_profile = profile

        try:
            self._active_process = self.popen_fn(cmd, env=env)
        except (OSError, subprocess.SubprocessError) as err:
            self._status = ModelStatus.ERROR
            self._active_process = None
            self._active_profile = None
            raise LocalModelError(
                f"Falha ao disparar subprocesso do llama-server: {err}"
            ) from err

        health_url = f"http://{profile.host}:{profile.port}/health"
        deadline = self.time_fn() + timeout_seconds
        poll_interval = 0.5
        is_ready = False

        while self.time_fn() < deadline:
            if hasattr(self._active_process, "poll") and self._active_process.poll() is not None:
                exit_code = self._active_process.poll()
                self.stop_model()
                self._status = ModelStatus.ERROR
                raise ModelStartupTimeoutError(
                    f"Processo do modelo encerrou prematuramente com exit code {exit_code}."
                )

            try:
                status_code = self.http_get_fn(health_url)
                if status_code == 200:
                    self._status = ModelStatus.READY
                    is_ready = True
                    break
            except (httpx.HTTPError, OSError, TimeoutError) as err:
                logger.debug("Falha durante polling de /health: %s", err)

            self.sleep_fn(poll_interval)

        if not is_ready:
            self.stop_model()
            self._status = ModelStatus.ERROR
            raise ModelStartupTimeoutError(
                f"Tempo limite ({timeout_seconds}s) atingido aguardando inicialização em {health_url}."
            )

    def stop_model(self, timeout_seconds: float = 15.0) -> None:
        """Encerra graciosamente o processo com SIGTERM, aplicando SIGKILL se necessário."""
        if self._active_process is None:
            self._status = ModelStatus.STOPPED
            return

        self._status = ModelStatus.STOPPING
        proc = self._active_process

        try:
            if hasattr(proc, "terminate"):
                proc.terminate()
            elif hasattr(proc, "pid") and isinstance(proc.pid, int):
                os.kill(proc.pid, signal.SIGTERM)

            deadline = self.time_fn() + timeout_seconds
            terminated = False

            while self.time_fn() < deadline:
                if hasattr(proc, "poll") and proc.poll() is not None:
                    terminated = True
                    break
                self.sleep_fn(0.2)

            if not terminated:
                if hasattr(proc, "kill"):
                    proc.kill()
                elif hasattr(proc, "pid") and isinstance(proc.pid, int):
                    os.kill(proc.pid, signal.SIGKILL)
                if hasattr(proc, "wait"):
                    try:
                        proc.wait(timeout=2.0)
                    except (subprocess.SubprocessError, OSError) as wait_err:
                        logger.warning("Erro ao aguardar processo pós-SIGKILL: %s", wait_err)
        except (subprocess.SubprocessError, OSError) as stop_err:
            logger.warning("Falha durante encerramento do processo: %s", stop_err)
        finally:
            self._active_process = None
            self._active_profile = None
            self._status = ModelStatus.STOPPED
            self.vram_gate.assert_clean(300)
