"""Testes unitários para o TuringReviewGate do Downstream com @aniche e @unclebob (ST-028).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from bombe_code.turing.review_gate import TuringReviewGate


def test_review_gate_approves_when_both_reviewers_and_tests_pass():
    gate = TuringReviewGate()

    aniche_verdict = {
        "approved": True,
        "agent": "@aniche",
        "notes": "Suíte completa de testes com cobertura de caminhos críticos e zero flaky tests.",
    }
    unclebob_verdict = {
        "approved": True,
        "agent": "@unclebob",
        "notes": "Código limpo, funções pequenas, nomenclatura expressiva e conformidade com SOLID.",
    }

    result = gate.evaluate(
        aniche_verdict=aniche_verdict,
        unclebob_verdict=unclebob_verdict,
        test_run_success=True,
    )

    assert result["approved"] is True
    assert result["gate"] == "TuringReviewGate"
    assert len(result["veto_reasons"]) == 0


def test_review_gate_vetoes_when_aniche_rejects_tests():
    gate = TuringReviewGate()

    aniche_verdict = {
        "approved": False,
        "agent": "@aniche",
        "notes": "Faltam testes de integração para o caso de borda de timeout no banco.",
    }
    unclebob_verdict = {
        "approved": True,
        "agent": "@unclebob",
        "notes": "Clean code aprovado.",
    }

    result = gate.evaluate(
        aniche_verdict=aniche_verdict,
        unclebob_verdict=unclebob_verdict,
        test_run_success=True,
    )

    assert result["approved"] is False
    assert any("@aniche" in r for r in result["veto_reasons"])


def test_review_gate_vetoes_when_unclebob_rejects_code():
    gate = TuringReviewGate()

    aniche_verdict = {"approved": True, "agent": "@aniche", "notes": "Testes verdes."}
    unclebob_verdict = {
        "approved": False,
        "agent": "@unclebob",
        "notes": "Método com 120 linhas violando SRP e acoplamento direto de persistência.",
    }

    result = gate.evaluate(
        aniche_verdict=aniche_verdict,
        unclebob_verdict=unclebob_verdict,
        test_run_success=True,
    )

    assert result["approved"] is False
    assert any("@unclebob" in r for r in result["veto_reasons"])


def test_review_gate_vetoes_when_automated_tests_fail():
    gate = TuringReviewGate()

    aniche_verdict = {"approved": True, "agent": "@aniche", "notes": "Testes desenhados."}
    unclebob_verdict = {"approved": True, "agent": "@unclebob", "notes": "Clean code ok."}

    result = gate.evaluate(
        aniche_verdict=aniche_verdict,
        unclebob_verdict=unclebob_verdict,
        test_run_success=False,
    )

    assert result["approved"] is False
    assert any("Suíte de testes automatizados falhou" in r for r in result["veto_reasons"])
