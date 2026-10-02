from __future__ import annotations

BASE_PROMPT = (
    "You are Bombe Code, an interactive coding agent. "
    "You execute tasks end-to-end in the user's project."
)

_AGENT_PREAMBLES = {
    "build": "Focus on implementing the requested change completely.",
    "plan": "Focus on analyzing and planning before any change.",
}


def build_system_prompt(agent: str, project_instructions: str | None = None) -> str:
    preamble = _AGENT_PREAMBLES.get(agent, f"You are operating as the '{agent}' agent.")
    parts = [BASE_PROMPT, f"Active agent: {agent}.", preamble]
    if project_instructions:
        parts.append(project_instructions)
    return "\n\n".join(parts)
