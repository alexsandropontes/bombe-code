"""Testes do Guardiãoooo Determinístico de Ações — anti-alucinação por AÇÃO,
não por relógio (timeout de execução não protege contra alucinação)."""

from bombe_code.permissions.acao_guard import GuardaDeAcoes


def test_escrita_limpa_passa():
    guarda = GuardaDeAcoes(agente="@valim")
    veto = guarda.validar_escrita("src/app.py", "def app():\n    return 1\n")
    assert veto is None
    assert guarda.escritas == 1
    assert guarda.red_flag is None


def test_fraude_de_conteudo_veta_notimplementederror():
    guarda = GuardaDeAcoes(agente="@valim")
    veto = guarda.validar_escrita("src/app.py", "def pagar():\n    raise NotImplementedError\n")
    assert veto and "VETO" in veto and "NotImplementedError" in veto
    assert guarda.vetoes == 1


def test_mock_e_todo_vetam():
    guarda = GuardaDeAcoes(agente="@valim")
    assert "VETO" in guarda.validar_escrita("src/x.py", "from unittest.mock import MagicMock\n")
    assert "VETO" in guarda.validar_escrita("src/y.js", "// TODO: implementar depois\n")


def test_conteudo_vazio_veta():
    guarda = GuardaDeAcoes(agente="@valim")
    assert "VETO" in guarda.validar_escrita("src/vazia.py", "   \n")


def test_construcao_progressiva_e_legitima():
    """Arquivo grande construído em partes: cada escrita CONTÉM a anterior."""
    guarda = GuardaDeAcoes(agente="@valim")
    assert guarda.validar_escrita("src/big.md", "parte 1\n") is None
    assert guarda.validar_escrita("src/big.md", "parte 1\nparte 2\n") is None
    assert guarda.validar_escrita("src/big.md", "parte 1\nparte 2\nparte 3\n") is None
    assert guarda.vetoes == 0


def test_escrita_duplicada_exata_veta():
    guarda = GuardaDeAcoes(agente="@valim")
    assert guarda.validar_escrita("src/app.py", "conteúdo v1\n") is None
    veto = guarda.validar_escrita("src/app.py", "conteúdo v1\n")
    assert veto and "IDÊNTICO" in veto


def test_briga_de_conteudo_veta():
    """Escritas divergentes (nem duplicata, nem extensão) repetidas = briga."""
    guarda = GuardaDeAcoes(agente="@valim")
    assert guarda.validar_escrita("src/app.py", "versão A inicial\n") is None
    assert (
        guarda.validar_escrita("src/app.py", "versão B diferente\n") is None
    )  # 1ª divergência: ok
    veto = guarda.validar_escrita("src/app.py", "versão C outra coisa\n")
    assert veto and "divergente" in veto


def test_leitura_repetida_avisa_e_depois_ica_bandeira():
    guarda = GuardaDeAcoes(agente="@ieru")
    # Leituras 1..4: silenciosas (releitura legítima de arquivo grande)
    assert all(guarda.registrar_leitura("docs/big.md") == "" for _ in range(4))
    assert guarda.red_flag is None
    # 5ª: aviso ao agente, sem bandeira
    assert "5ª leitura" in guarda.registrar_leitura("docs/big.md")
    assert guarda.red_flag is None
    # 9ª: excesso claro → bandeira vermelha
    for _ in range(4):
        guarda.registrar_leitura("docs/big.md")
    assert guarda.red_flag and "leituras do mesmo alvo" in guarda.red_flag


def test_tres_vetores_icam_bandeira_vermelha():
    guarda = GuardaDeAcoes(agente="@valim")
    guarda.validar_escrita("a.py", "raise NotImplementedError")
    guarda.validar_escrita("b.py", "// TODO depois")
    guarda.validar_escrita("c.py", "")
    assert guarda.vetoes == 3
    assert guarda.red_flag and "vetos" in guarda.red_flag


def test_loop_de_acao_ica_bandeira_vermelha():
    guarda = GuardaDeAcoes(agente="@ieru")
    for _ in range(3):
        guarda.registrar_acao("read_project_file", "docs/arch.md")
    guarda.registrar_acao("read_project_file", "docs/arch.md")
    assert guarda.red_flag and "loop de ação" in guarda.red_flag


def test_bandeira_vermelha_bloqueia_escritas_subsequentes():
    guarda = GuardaDeAcoes(agente="@valim")
    guarda.validar_escrita("a.py", "raise NotImplementedError")
    guarda.validar_escrita("b.py", "// TODO")
    guarda.validar_escrita("c.py", "")
    veto = guarda.validar_escrita("d.py", "conteúdo perfeitamente válido\n")
    assert veto and "bandeira vermelha" in veto


def test_redflag_via_stream_evento_unico():
    """O _drive checa a bandeira no primeiro evento e aborta antes do fim."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from bombe_code.agents.models import AgentDefinition
    from bombe_code.agents.runner import AgentRunner

    definition = AgentDefinition(
        handle="@ieru",
        name="I",
        role="r",
        country="BR",
        origin="BRAZIL",
        historical_homage="h",
        primary_stage="PLAN",
        phase="UPSTREAM",
        required_inputs=[],
        expected_outputs=[],
        skills_allowed=[],
        system_prompt="s",
    )

    class FakeStreamAgent:
        def run_stream_events(self, prompt, usage_limits=None):
            class CM:
                async def __aenter__(self_inner):
                    return self_inner

                async def __aexit__(self_inner, *a):
                    return False

                async def __aiter__(self_inner):
                    yield SimpleNamespace(kind="x")

            return CM()

    factory = MagicMock()
    factory.create_agent.return_value = FakeStreamAgent()
    guarda = GuardaDeAcoes(agente="@ieru")
    guarda.red_flag = "vetos acumulados"
    runner = AgentRunner(definition, factory, guarda=guarda)

    import pytest as _pytest

    with _pytest.MonkeyPatch.context() as mp:
        mp.delenv("BOMBE_TUI_RUNNING", raising=False)
        res = runner.run("missão")

    assert res.status == "RED_FLAG"
    assert "BANDEIRA VERMELHA" in res.block_reason


def test_painel_de_erro_sobrevive_a_excecao_com_markup():
    """Regressão: exceção contendo '[/magenta]' não pode derrubar o próprio
    painel de erro (o app precisava disso até pra relançar)."""
    from rich.console import Console

    from bombe_code.errors import format_error_panel

    exc = RuntimeError("closing tag '[/magenta]' at position 82 doesn't match")
    painel = format_error_panel(exc, log_file=__import__("pathlib").Path("/tmp/x.log"))
    console = Console()
    console.render(painel)  # não pode levantar MarkupError
