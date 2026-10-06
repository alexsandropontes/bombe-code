"""Modelo de Domínio para o Sequenciador de Ondas (Lean Inception & Wave Slicing)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    """Níveis de risco do Semáforo do Sequenciador da Lean Inception."""

    GREEN = "GREEN"  # Baixa incerteza / Baixo esforço
    YELLOW = "YELLOW"  # Média incerteza / Médio esforço
    RED = "RED"  # Alta incerteza técnica ou de negócio (The Riskiest Assumption)

    @classmethod
    def from_str(cls, val: str) -> RiskLevel:
        v = (val or "").strip().upper()
        if "VERM" in v or "RED" in v or "ALTO" in v:
            return cls.RED
        if "AMAR" in v or "YEL" in v or "MED" in v:
            return cls.YELLOW
        return cls.GREEN


class SequencerValidationError(Exception):
    """Exceção levantada quando um Sequenciador viola regras de mercado da Lean Inception."""


@dataclass
class WavePlan:
    """Representa o planejamento de uma Onda no Sequenciador."""

    wave_id: str
    name: str
    business_hypothesis: str
    features: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.GREEN
    is_final: bool = False


@dataclass
class WaveSequencer:
    """Agregado de Domínio que encapsula o Sequenciador de Ondas do MVP."""

    plans: list[WavePlan] = field(default_factory=list)

    @property
    def total_waves(self) -> int:
        return len(self.plans)

    def get_plan(self, wave_id: str) -> WavePlan | None:
        target = wave_id.strip().upper()
        for p in self.plans:
            if p.wave_id.strip().upper() == target:
                return p
        return None

    def get_plan_index(self, wave_id: str) -> int:
        target = wave_id.strip().upper()
        for i, p in enumerate(self.plans):
            if p.wave_id.strip().upper() == target:
                return i
        return -1

    def has_future_waves(self, current_wave_id: str) -> bool:
        """Verifica se existem ondas planejadas posteriores à onda informada."""
        idx = self.get_plan_index(current_wave_id)
        if idx == -1:
            return False
        return idx < (len(self.plans) - 1)

    def is_final_wave(self, current_wave_id: str) -> bool:
        """Verifica se a onda atual é a última onda planejada do produto."""
        if not self.plans:
            return True
        idx = self.get_plan_index(current_wave_id)
        if idx == -1:
            # Se não consta no sequenciador e tem planos, assume onda única ou final
            return False
        plan = self.plans[idx]
        if plan.is_final:
            return True
        return idx == (len(self.plans) - 1)

    def validate(self) -> list[str]:
        """Aplica as Regras de Ouro de Mercado da Lean Inception."""
        errors: list[str] = []
        for plan in self.plans:
            # Regra de Capacidade: máximo de 4 fatias verticais por onda
            if len(plan.features) > 4:
                errors.append(
                    f"Violação de capacidade na {plan.wave_id}: {len(plan.features)} features planejadas "
                    f"(o limite da Lean Inception é de no máximo 4 por onda)."
                )
        return errors

    @classmethod
    def from_markdown(cls, md_text: str) -> WaveSequencer:
        """Faz o parsing resiliente de tabelas de sequenciamento em Markdown no PRD."""
        plans: list[WavePlan] = []
        lines = md_text.splitlines()
        in_table = False

        for line in lines:
            trimmed = line.strip()
            if not trimmed.startswith("|"):
                continue

            # Detecta header
            if "Onda" in trimmed and (
                "Nome" in trimmed or "Hipótese" in trimmed or "Fatias" in trimmed
            ):
                in_table = True
                continue

            if in_table and re.match(r"^\|[\s\-:|]+\|$", trimmed):
                # Linha separadora |---|---|...
                continue

            if in_table and trimmed.startswith("|"):
                cols = [c.strip() for c in trimmed.split("|")[1:-1]]
                if len(cols) >= 4:
                    wave_id = cols[0]
                    if not wave_id or wave_id.startswith("-"):
                        continue
                    name = cols[1] if len(cols) > 1 else ""
                    hypothesis = cols[2] if len(cols) > 2 else ""
                    raw_features = cols[3] if len(cols) > 3 else ""
                    features = [f.strip() for f in raw_features.split(",") if f.strip()]

                    raw_risk = cols[4] if len(cols) > 4 else "VERDE"
                    risk = RiskLevel.from_str(raw_risk)

                    is_final = False
                    if len(cols) > 5:
                        final_str = cols[5].upper()
                        is_final = "SIM" in final_str or "TRUE" in final_str or "1" in final_str

                    plans.append(
                        WavePlan(
                            wave_id=wave_id,
                            name=name,
                            business_hypothesis=hypothesis,
                            features=features,
                            risk_level=risk,
                            is_final=is_final,
                        )
                    )

        # Se nenhuma onda foi marcada explicitamente como final, marca a última
        if plans and not any(p.is_final for p in plans):
            plans[-1].is_final = True

        return cls(plans=plans)

    def to_markdown(self) -> str:
        """Serializa o Sequenciador em tabela Markdown oficial para o PRD."""
        lines = [
            "## Sequenciador de Ondas do MVP",
            "",
            "| Onda | Nome da Onda | Hipótese de Negócio | Fatias Verticais / Features | Risco | Final |",
            "|---|---|---|---|:---:|:---:|",
        ]
        for p in self.plans:
            final_str = "Sim" if p.is_final else "Não"
            risk_str = (
                "VERMELHO"
                if p.risk_level == RiskLevel.RED
                else ("AMARELO" if p.risk_level == RiskLevel.YELLOW else "VERDE")
            )
            feats_str = ", ".join(p.features)
            lines.append(
                f"| {p.wave_id} | {p.name} | {p.business_hypothesis} | {feats_str} | {risk_str} | {final_str} |"
            )
        lines.append("")
        return "\n".join(lines)
