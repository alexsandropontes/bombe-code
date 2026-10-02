"""Testes para o catálogo e modelos oficiais de Agentes (bombe_code.agents).
TDD Estrito: RED -> GREEN -> REFACTOR.
"""

from bombe_code.agents.models import AgentDefinition, AgentOrigin
from bombe_code.agents.registry import AgentRegistry
from bombe_code.turing.state_machine import TuringStage


def test_agent_definition_validation():
    agent = AgentDefinition(
        handle="@valim",
        name="José Valim",
        role="Backend Lead Engineer",
        origin=AgentOrigin.BRAZIL,
        historical_homage="Criador do Elixir e membro pioneiro do core team do Rails.",
        primary_stage=TuringStage.EXECUTE,
        phase="DOWNSTREAM",
        required_inputs=["ST-XXX.md"],
        expected_outputs=["tests/", "src/"],
        skills_allowed=["tdd-governance", "python-elite", "fastapi"],
        system_prompt="Você é José Valim, autoridade em backend e TDD estrito.",
    )
    assert agent.handle == "@valim"
    assert agent.is_brazilian is True
    assert agent.is_universal is False


def test_agent_registry_official_roster_count_and_parity():
    registry = AgentRegistry.default()
    agents = registry.list_all()

    # Total: 1 Turing + 22 Especialistas = 23 Agentes
    assert len(agents) == 23

    # Turing é o maestro universal
    turing = registry.get("@turing")
    assert turing is not None
    assert turing.is_universal is True

    # Maioria de pioneiros brasileiros de TI: 12 Brasileiros e 10 Mundiais
    specialists = [a for a in agents if not a.is_universal]
    assert len(specialists) == 22

    brazilians = [a for a in specialists if a.origin == AgentOrigin.BRAZIL]
    world = [a for a in specialists if a.origin == AgentOrigin.WORLD]

    assert len(brazilians) == 12
    assert len(world) == 10

    br_handles = {a.handle for a in brazilians}
    assert "@valim" in br_handles
    assert "@diego" in br_handles
    assert "@barreto" in br_handles

    world_handles = {a.handle for a in world}
    assert "@grace" in world_handles
    assert "@alan" in world_handles
    assert "@barbara" in world_handles


def test_agent_registry_lookup_by_handle():
    registry = AgentRegistry.default()

    # Busca com ou sem @
    assert registry.get("@grace") is not None
    assert registry.get("grace") is not None
    assert registry.get("grace").name == "Grace Hopper"

    assert registry.get("@desconhecido") is None


def test_agent_registry_filter_by_stage_and_phase():
    registry = AgentRegistry.default()

    discuss_agents = registry.list_by_stage(TuringStage.DISCUSS)
    handles = {a.handle for a in discuss_agents}
    assert "@meira" in handles
    assert "@grace" in handles

    execute_agents = registry.list_by_stage(TuringStage.EXECUTE)
    exec_handles = {a.handle for a in execute_agents}
    assert "@valim" in exec_handles
    assert "@ada" in exec_handles
    assert "@unclebob" in exec_handles

    upstream_agents = registry.list_by_phase("UPSTREAM")
    up_handles = {a.handle for a in upstream_agents}
    assert "@meira" in up_handles
    assert "@grace" in up_handles
    assert "@ieru" in up_handles
    assert "@caroli" in up_handles


def test_agent_contracts_integrity():
    registry = AgentRegistry.default()
    for agent in registry.list_all():
        assert agent.handle.startswith("@")
        assert len(agent.name) > 0
        assert len(agent.historical_homage) > 10
        assert len(agent.system_prompt) > 20
        if not agent.is_universal:
            assert len(agent.required_inputs) > 0
            assert len(agent.expected_outputs) > 0
