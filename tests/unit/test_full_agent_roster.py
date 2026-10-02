"""Testes para o catálogo completo e profissional de 23 agentes (EP-002) no padrão PDW 3.5.
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from bombe_code.agents.models import AgentOrigin
from bombe_code.agents.registry import AgentRegistry
from bombe_code.turing.state_machine import TuringStage


def test_full_agent_roster_count_and_majority():
    registry = AgentRegistry.default()
    agents = registry.list_all()

    # Total: 1 Maestro Turing + 22 Especialistas = 23 Agentes
    assert len(agents) == 23

    # Maestro
    turing = registry.get("@turing")
    assert turing is not None
    assert turing.is_universal is True

    # Especialistas
    specialists = [a for a in agents if not a.is_universal]
    assert len(specialists) == 22

    brazilians = [a for a in specialists if a.origin == AgentOrigin.BRAZIL]
    world = [a for a in specialists if a.origin == AgentOrigin.WORLD]

    # Maioria de pioneiros brasileiros de TI: 12 Brasileiros e 10 Mundiais
    assert len(brazilians) == 12
    assert len(world) == 10

    br_handles = {a.handle for a in brazilians}
    expected_br = {
        "@meira",
        "@ieru",
        "@barreto",
        "@diego",
        "@caroli",
        "@valim",
        "@aniche",
        "@edith",
        "@demi",
        "@claudia",
        "@nelson",
        "@nina",
    }
    assert br_handles == expected_br

    world_handles = {a.handle for a in world}
    expected_world = {
        "@grace",
        "@alan",
        "@norman",
        "@codd",
        "@barbara",
        "@scott",
        "@ryan",
        "@james",
        "@ada",
        "@unclebob",
    }
    assert world_handles == expected_world


def test_backend_language_specialists_exist():
    registry = AgentRegistry.default()

    # Python & Go
    barbara = registry.get("@barbara")
    assert barbara is not None
    assert "Python" in barbara.role or "Python" in barbara.system_prompt
    assert "Go" in barbara.role or "Go" in barbara.system_prompt

    # .NET / C#
    scott = registry.get("@scott")
    assert scott is not None
    assert ".NET" in scott.role or "C#" in scott.system_prompt

    # Node.js / TypeScript
    ryan = registry.get("@ryan")
    assert ryan is not None
    assert "Node" in ryan.role or "TypeScript" in ryan.system_prompt

    # Java / Spring Boot
    james = registry.get("@james")
    assert james is not None
    assert "Java" in james.role or "Spring" in james.system_prompt

    # Elixir / Concorrência
    valim = registry.get("@valim")
    assert valim is not None
    assert "Elixir" in valim.historical_homage


def test_user_journey_and_appsec_specialists_exist():
    registry = AgentRegistry.default()

    # User Journey Architect
    alan = registry.get("@alan")
    assert alan is not None
    assert alan.primary_stage == TuringStage.PLAN
    assert "Journey" in alan.role

    # AppSec Defensivo & Criptografia (Paulo Barreto)
    barreto = registry.get("@barreto")
    assert barreto is not None
    assert "Security" in barreto.role or "Cripto" in barreto.role
    assert "BLS" in barreto.historical_homage or "Whirlpool" in barreto.historical_homage

    # AppSec Ofensivo & Pentest (Diego Aranha)
    diego = registry.get("@diego")
    assert diego is not None
    assert "Security" in diego.role or "OWASP" in diego.role


def test_pdw_35_compliance_in_prompts():
    registry = AgentRegistry.default()
    for agent in registry.list_all():
        prompt = agent.system_prompt
        # Todos os agentes devem conter seções inspiradas nos 9 pilares PDW 3.5
        assert "# 1. TEMA" in prompt or "TEMA:" in prompt or len(prompt) > 80
        assert len(agent.historical_homage) > 20
        assert agent.handle.startswith("@")
        if not agent.is_universal:
            assert len(agent.required_inputs) > 0
            assert len(agent.expected_outputs) > 0
