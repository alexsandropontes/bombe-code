"""Unit: system prompt por agent (F3 RN3)."""

from bombe_code.session.system import build_system_prompt


def test_prompt_inclui_base_e_nome_do_agente():
    prompt = build_system_prompt(agent="build")
    assert "Bombe Code" in prompt
    assert "build" in prompt


def test_prompt_inclui_instrucoes_do_projeto_quando_presentes():
    prompt = build_system_prompt(agent="plan", project_instructions="Sem emojis no codigo.")
    assert "Sem emojis no codigo." in prompt


def test_prompt_sem_instrucoes_do_projeto_nao_adiciona_bloco():
    prompt = build_system_prompt(agent="build")
    assert "project_instructions" not in prompt
