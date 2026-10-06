"""Testes unitários para o WaveSequencer (Regras da Lean Inception e Sequenciamento de Ondas)."""

from bombe_code.domain.wave.sequencer import (
    RiskLevel,
    WavePlan,
    WaveSequencer,
)


def test_wave_plan_creation():
    plan = WavePlan(
        wave_id="ONDA-001",
        name="Core Value Loop",
        business_hypothesis="Usuário consegue logar e visualizar sua dose diária",
        features=["Auth JWT", "Catálogo Básico", "Leitor de Cards"],
        risk_level=RiskLevel.RED,
        is_final=False,
    )
    assert plan.wave_id == "ONDA-001"
    assert len(plan.features) == 3
    assert plan.risk_level == RiskLevel.RED
    assert not plan.is_final


def test_sequencer_detection_of_future_and_final_waves():
    p1 = WavePlan(
        wave_id="ONDA-001",
        name="Core Value",
        business_hypothesis="Hipótese 1",
        features=["F1", "F2"],
        risk_level=RiskLevel.RED,
        is_final=False,
    )
    p2 = WavePlan(
        wave_id="ONDA-002",
        name="Retention",
        business_hypothesis="Hipótese 2",
        features=["F3", "F4"],
        risk_level=RiskLevel.YELLOW,
        is_final=False,
    )
    p3 = WavePlan(
        wave_id="ONDA-003",
        name="Operational Pipeline",
        business_hypothesis="Hipótese 3",
        features=["F5"],
        risk_level=RiskLevel.GREEN,
        is_final=True,
    )
    seq = WaveSequencer(plans=[p1, p2, p3])

    assert seq.total_waves == 3
    assert seq.has_future_waves("ONDA-001") is True
    assert seq.is_final_wave("ONDA-001") is False

    assert seq.has_future_waves("ONDA-002") is True
    assert seq.is_final_wave("ONDA-002") is False

    assert seq.has_future_waves("ONDA-003") is False
    assert seq.is_final_wave("ONDA-003") is True


def test_sequencer_validation_capacity_and_risk_rules():
    # Violação de capacidade: mais de 4 features em uma onda
    too_many_features = WavePlan(
        wave_id="ONDA-001",
        name="Overloaded Wave",
        business_hypothesis="Overload",
        features=["F1", "F2", "F3", "F4", "F5"],
        risk_level=RiskLevel.GREEN,
    )
    seq = WaveSequencer(plans=[too_many_features])
    errors = seq.validate()
    assert any("capacidade" in e.lower() for e in errors)


def test_sequencer_markdown_roundtrip():
    md = """
## Sequenciador de Ondas do MVP

| Onda | Nome da Onda | Hipótese de Negócio | Fatias Verticais / Features | Risco | Final |
|---|---|---|---|:---:|:---:|
| ONDA-001 | Core Loop | Usuário lê o card | Auth JWT, Leitor de Cards | VERMELHO | Não |
| ONDA-002 | Retenção | Usuário salva | Favoritos, Feedback | AMARELO | Não |
| ONDA-003 | Operacional | Pipeline diário | Web Push, Job Cron | VERDE | Sim |
"""
    seq = WaveSequencer.from_markdown(md)
    assert seq.total_waves == 3
    p1 = seq.get_plan("ONDA-001")
    assert p1 is not None
    assert p1.name == "Core Loop"
    assert p1.risk_level == RiskLevel.RED
    assert seq.is_final_wave("ONDA-003") is True
    assert seq.has_future_waves("ONDA-001") is True
