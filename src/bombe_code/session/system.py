from __future__ import annotations

BASE_PROMPT = (
    "You are Bombe Code, an interactive coding agent. "
    "You execute tasks end-to-end in the user's project."
)

_STAGE_INSTRUCTIONS = {
    "DISCUSS": (
        "## ETAPA ATIVA: DISCUSS\n"
        "Você está na etapa DISCUSS da ONDA. Seu foco é alinhamento de escopo, ideação e documentação de PRD/briefing em docs/briefings/.\n"
        "É PROIBIDO alterar ou criar arquivos de código em src/ ou testes nesta etapa."
    ),
    "PLAN": (
        "## ETAPA ATIVA: PLAN\n"
        "Você está na etapa PLAN da ONDA. Seu foco é arquitetura de software, jornadas de usuário e especificação de ai-stories em docs/stories/.\n"
        "É PROIBIDO criar código de produção em src/ nesta etapa."
    ),
    "EXECUTE": (
        "## ETAPA ATIVA: EXECUTE\n"
        "Você está na etapa EXECUTE da ONDA. Seu foco é implementação e desenvolvimento guiado por testes (TDD).\n"
        "A escrita e edição de código em src/ e testes em tests/ está totalmente liberada."
    ),
    "VALIDATE": (
        "## ETAPA ATIVA: VALIDATE\n"
        "Você está na etapa VALIDATE da ONDA. Seu foco é execução de testes de integração/E2E e relatórios em docs/reports/.\n"
        "A adição de novos módulos arbitrários em src/ é restrita."
    ),
    "COMPLETED": (
        "## ETAPA ATIVA: COMPLETED\n"
        "A ONDA foi concluída com sucesso. Pronta para iniciar um novo ciclo em DISCUSS."
    ),
    "VIBE": (
        "## MODO ATIVO: VIBE (LIVRE)\n"
        "Você está operando no Modo VIBE. Você é um assistente de engenharia ágil, flexível e direto.\n"
        "Não há restrições formais de etapa: atenda prontamente às solicitações do desenvolvedor, "
        "escrevendo código, refatorando, criando arquivos e planejando com agilidade total conforme solicitado."
    ),
}

_AGENT_PREAMBLES = {
    "build": "Focus on implementing the requested change completely.",
    "plan": "Focus on analyzing and planning before any change.",
}



def build_system_prompt(

    agent: str,
    project_instructions: str | None = None,
    stage: str = "DISCUSS",
) -> str:
    preamble = _AGENT_PREAMBLES.get(agent, f"You are operating as the '{agent}' agent.")
    stage_guide = _STAGE_INSTRUCTIONS.get(stage.upper(), _STAGE_INSTRUCTIONS["DISCUSS"])
    parts = [BASE_PROMPT, f"Active agent: {agent}.", preamble, stage_guide]
    if project_instructions:
        parts.append(project_instructions)
    return "\n\n".join(parts)

