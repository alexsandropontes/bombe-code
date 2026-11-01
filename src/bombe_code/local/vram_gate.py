import subprocess
from collections.abc import Callable

from .contracts import NvidiaSmiNotFoundError, VRAMThresholdExceededError


class VRAMGate:
    """Barreira sentinela para medição e controle de alocação de memória VRAM via nvidia-smi."""

    def __init__(
        self,
        runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
        strict: bool = False,
    ) -> None:
        self._runner = runner or self._default_runner
        self._strict = strict

    @staticmethod
    def _default_runner(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, capture_output=True, text=True, check=True)

    def query_used_vram_mb(self) -> int:
        """Consulta a VRAM em uso em MiB no host via nvidia-smi.

        Retorna o total agregado de VRAM em uso. Se nvidia-smi não existir ou falhar,
        retorna 0 (ou levanta NvidiaSmiNotFoundError se strict=True).
        """
        cmd = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]
        try:
            result = self._runner(cmd)
        except FileNotFoundError as err:
            if self._strict:
                raise NvidiaSmiNotFoundError("Comando 'nvidia-smi' não encontrado no PATH.") from err
            return 0
        except Exception as err:
            if self._strict:
                raise NvidiaSmiNotFoundError(
                    f"Falha ao executar consulta de VRAM via nvidia-smi: {err}"
                ) from err
            return 0

        stdout = result.stdout.strip()
        if not stdout:
            if self._strict:
                raise NvidiaSmiNotFoundError("Saída vazia retornada pelo comando nvidia-smi.")
            return 0

        total_vram = 0
        for line in stdout.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            token = line_str.split()[0]
            try:
                total_vram += int(float(token))
            except ValueError:
                continue

        return total_vram

    def wait_until_clean(self, max_used_mb: int = 300, timeout_seconds: float = 10.0) -> bool:
        """Aguarda a desalocação assíncrona da VRAM pelo driver NVIDIA até o teto."""
        import time
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            used = self.query_used_vram_mb()
            if used <= max_used_mb:
                return True
            time.sleep(0.5)
        return self.query_used_vram_mb() <= max_used_mb

    def assert_clean(self, max_used_mb: int = 300) -> None:
        """Verifica se a VRAM em uso está abaixo do limite aceitável de segurança."""
        self.wait_until_clean(max_used_mb=max_used_mb, timeout_seconds=8.0)
        used = self.query_used_vram_mb()
        if used > max_used_mb:
            raise VRAMThresholdExceededError(
                f"VRAM residual ({used} MiB) excede o teto máximo permitido de {max_used_mb} MiB."
            )
