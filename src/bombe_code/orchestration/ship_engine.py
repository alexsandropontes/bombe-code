"""Ship engine responsible for gated git branch promotions."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from bombe_code.domain.contracts.ship import PromotionResult, ShipTarget
from bombe_code.turing.promocao import PromotorDeBranches


class ShipEngine:
    """Orchestrates git promotion workflows with pre-flight automated test gates."""

    def __init__(
        self,
        project_dir: Path | str = ".",
        test_runner: Callable[[], bool] | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.test_runner = test_runner
        self.promotor = PromotorDeBranches(self.project_dir)

    def _run_pre_flight_tests(self) -> bool:
        """Runs test suite before promotion; returns True if tests pass."""
        if self.test_runner is not None:
            return bool(self.test_runner())

        try:
            res = subprocess.run(
                ["pytest", "-q"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            return res.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False

    def promote_to_environment(self, target: ShipTarget | str) -> PromotionResult:
        """Promotes current approved state to target branch after validating tests."""
        target_env = ShipTarget(target)
        target_branch = "main" if target_env == ShipTarget.PRD else target_env.value

        if not self._run_pre_flight_tests():
            return PromotionResult(
                success=False,
                source_commit="",
                target_branch=target_branch,
                message="Testes pré-flight falharam. Promoção abortada.",
                tests_passed=False,
                details=["Pre-flight test gate rejected promotion."],
            )

        if target_env == ShipTarget.DEV:
            res = self.promotor.promover_para_dev("feat: promote to dev via ShipEngine")
        else:
            res = self.promotor.promover_fase(target_branch)

        current_commit = self.promotor.commit_atual()

        return PromotionResult(
            success=res.success,
            source_commit=current_commit,
            target_branch=target_branch,
            message=res.mensagem,
            tests_passed=True,
            details=res.detalhes,
        )
