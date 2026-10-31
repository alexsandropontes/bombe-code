"""Static complexity classifier for vertical slices."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CRITICAL_TERMS = {
    "protocol",
    "engine",
    "router",
    "quota",
    "auth",
    "security",
    "concurrency",
    "lock",
    "vllm",
    "circuit_breaker",
}


class ComplexityAnalysis(BaseModel):
    """Immutable complexity analysis report for a slice."""

    model_config = ConfigDict(frozen=True)

    score: int = Field(ge=1, le=3, description="Complexity score between 1 and 3")
    reasons: list[str] = Field(min_length=1, description="Audit trail of classification reasons")
    recommended_tier: str = Field(pattern="^(junior|pleno|senior)$")


class ComplexityClassifier:
    """Evaluates slices statically based on lines, affected paths, and architectural keywords."""

    def evaluate_slice(self, slice_spec: dict[str, Any]) -> ComplexityAnalysis:
        """Evaluate slice and return deterministic ComplexityAnalysis."""
        affected_files: list[str] = slice_spec.get("affected_files", [])
        estimated_lines: int = int(slice_spec.get("estimated_lines", 0))
        scope: str = str(slice_spec.get("scope", "")).lower()

        # Check Senior Rules
        senior_reasons = self._check_senior_rules(affected_files, scope, estimated_lines)
        if senior_reasons:
            return ComplexityAnalysis(
                score=3,
                reasons=senior_reasons,
                recommended_tier="senior",
            )

        # Check Pleno Rules
        pleno_reasons = self._check_pleno_rules(affected_files, scope, estimated_lines)
        if pleno_reasons:
            return ComplexityAnalysis(
                score=2,
                reasons=pleno_reasons,
                recommended_tier="pleno",
            )

        # Default: Junior Rules
        junior_reasons = self._check_junior_rules(affected_files, scope, estimated_lines)
        return ComplexityAnalysis(
            score=1,
            reasons=junior_reasons,
            recommended_tier="junior",
        )

    def _check_senior_rules(
        self, affected_files: list[str], scope: str, estimated_lines: int
    ) -> list[str]:
        reasons: list[str] = []
        if estimated_lines > 200:
            reasons.append(f"Estimated lines exceed threshold ({estimated_lines} lines > 200)")

        matched_terms = [
            term
            for term in CRITICAL_TERMS
            if any(term in path.lower() for path in affected_files) or term in scope
        ]
        if matched_terms:
            reasons.append(
                f"Critical architectural scope identified (matched terms: {', '.join(sorted(matched_terms))})"
            )
        return reasons

    def _check_pleno_rules(
        self, affected_files: list[str], scope: str, estimated_lines: int
    ) -> list[str]:
        reasons: list[str] = []
        if len(affected_files) > 1:
            reasons.append(f"Multiple files affected ({len(affected_files)} files)")
        if 50 <= estimated_lines <= 200:
            reasons.append(f"Moderate code volume ({estimated_lines} lines in range 50-200)")
        return reasons

    def _check_junior_rules(
        self, affected_files: list[str], scope: str, estimated_lines: int
    ) -> list[str]:
        return [
            f"Isolated single file task (< 50 lines: {estimated_lines}) with low architectural complexity"
        ]
