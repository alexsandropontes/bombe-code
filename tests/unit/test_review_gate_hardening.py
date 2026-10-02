"""Testes unitários para o Hardening do TuringReviewGate com scanner anti-fraude (ST-032).
TDD Estrito: RED -> GREEN.
"""

from bombe_code.turing.review_gate import TuringReviewGate


def test_turing_review_gate_detects_not_implemented_fraud():
    gate = TuringReviewGate()

    # Código com NotImplementedError
    fraudulent_code = """
def process_payment(amount: float) -> bool:
    raise NotImplementedError("TODO implementar")
"""
    aniche_verdict = {"approved": True, "notes": "Testes de mentira"}
    unclebob_verdict = {"approved": True, "notes": "Parece bom"}

    res = gate.evaluate(
        aniche_verdict=aniche_verdict,
        unclebob_verdict=unclebob_verdict,
        test_run_success=True,
        code_content=fraudulent_code,
    )

    assert res["approved"] is False
    assert any("fraude" in r.lower() or "notimplemented" in r.lower() for r in res["veto_reasons"])


def test_turing_review_gate_approves_genuine_code():
    gate = TuringReviewGate()

    clean_code = """
def process_payment(amount: float) -> bool:
    if amount <= 0:
        return False
    return True
"""
    aniche_verdict = {"approved": True, "notes": "100% cobertura real"}
    unclebob_verdict = {"approved": True, "notes": "Clean code e SOLID"}

    res = gate.evaluate(
        aniche_verdict=aniche_verdict,
        unclebob_verdict=unclebob_verdict,
        test_run_success=True,
        code_content=clean_code,
    )

    assert res["approved"] is True
    assert len(res["veto_reasons"]) == 0
