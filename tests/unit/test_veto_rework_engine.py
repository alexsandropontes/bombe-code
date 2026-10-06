"""Testes do VetoReworkEngine — classificação de vetos e ciclo de retrabalho."""

from types import SimpleNamespace

from bombe_code.turing.rework import VetoClass, VetoReworkEngine


def test_classifica_approval_missing_deterministicamente():
    engine = VetoReworkEngine()
    analysis = engine.classify(
        "Ausência de aprovação explícita no parecer (Default-Deny)",
        validator_output="O produto parece adequado.",
        target_agent="@edith",
    )
    assert analysis.veto_class == VetoClass.APPROVAL_MISSING
    assert analysis.source == "deterministic"
    assert analysis.target_agent == "@edith"
    assert analysis.rework_prompt and "RE-AUDITORIA" in analysis.rework_prompt


def test_classifica_product_gap_por_marcadores_de_bloqueio():
    engine = VetoReworkEngine()
    analysis = engine.classify(
        "@edith: veto",
        validator_output="Auditoria concluída.\nBLOQUEIO: módulo de pagamentos não implementado.",
        target_agent="@edith",
    )
    assert analysis.veto_class == VetoClass.PRODUCT_GAP


def test_classifica_test_failure():
    engine = VetoReworkEngine()
    analysis = engine.classify("Suíte de testes automatizados falhou.", validator_output="")
    assert analysis.veto_class == VetoClass.TEST_FAILURE


def test_classifica_agent_blocked():
    engine = VetoReworkEngine()
    analysis = engine.classify(
        "🛑 BLOCKED: evidências obrigatórias não recebidas", validator_output=""
    )
    assert analysis.veto_class == VetoClass.AGENT_BLOCKED


def test_llm_classifica_quando_ambiguo():
    class FakeLLMAgent:
        def run_sync(self, prompt: str, **kwargs):
            return SimpleNamespace(output='{"veto_class": "PRODUCT_GAP"}')

    class FakeFactory:
        def create_agent(self, **kwargs):
            return FakeLLMAgent()

    engine = VetoReworkEngine(llm_factory=FakeFactory(), permitir_llm=True)
    analysis = engine.classify(
        "Ausência de aprovação explícita no parecer (Default-Deny)",
        validator_output="parecer vago",
    )
    assert analysis.veto_class == VetoClass.PRODUCT_GAP
    assert analysis.source == "llm"


def test_llm_indisponivel_cai_no_deterministico():
    class BrokenFactory:
        def create_agent(self, **kwargs):
            raise RuntimeError("sem provedor")

    engine = VetoReworkEngine(llm_factory=BrokenFactory())
    analysis = engine.classify("Ausência de aprovação explícita no parecer (Default-Deny)")
    assert analysis.veto_class == VetoClass.APPROVAL_MISSING
    assert analysis.source == "deterministic"


def test_rework_prompt_exige_declaracao_explicita():
    engine = VetoReworkEngine()
    analysis = engine.classify("Ausência de aprovação explícita", target_agent="@edith")
    prompt = engine.build_rework_prompt(analysis, original_demand="SaaS de frotas")
    assert "Homologação: APROVADO" in prompt
    assert "SaaS de frotas" in prompt
    assert "BLOQUEIO:" in prompt


def test_escalation_estruturada_com_bloqueios_extraidos():
    engine = VetoReworkEngine()
    analysis = engine.classify("veto", validator_output="", target_agent="@edith")
    escalation = engine.build_escalation(
        analysis,
        attempts=2,
        validator_outputs={
            "@edith": "BLOQUEIO: autenticação ausente\nBLOQUEIO: sem testes e2e",
        },
    )
    assert escalation["type"] == "business_question"
    assert escalation["veto_class"] == "APPROVAL_MISSING"
    assert escalation["attempts"] == 2
    assert escalation["suggested_owner"] == "@edith"
    assert escalation["blockers"] == ["autenticação ausente", "sem testes e2e"]
    assert "DÚVIDA DE NEGÓCIO" in escalation["question"]
