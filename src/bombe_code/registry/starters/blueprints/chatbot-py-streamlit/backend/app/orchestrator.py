"""
Agent Orchestrator - Sequential Execution (A → B → C)
Uses Pydantic AI for agent orchestration
"""
import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Agent:
    """Agent definition"""
    name: str
    role: str
    order: int
    system_prompt: str


class AgentOrchestrator:
    """Orchestrates sequential agent execution"""
    
    def __init__(self, team_name: str):
        self.team_name = team_name
        self.teams_dir = Path(__file__).parent.parent / "agents" / "teams"
        self.team_dir = self.teams_dir / team_name
        self.agents: List[Agent] = []
        self._load_agents()
    
    def _load_agents(self):
        """Load agents from team directory"""
        if not self.team_dir.exists():
            raise ValueError(f"Team '{self.team_name}' not found")
        
        # Load all .md files (agent prompts)
        for md_file in sorted(self.team_dir.glob("*.md")):
            # Skip orchestrator and other non-agent files
            if md_file.stem in ["orchestrator", "README"]:
                continue
            
            # Read agent prompt
            system_prompt = md_file.read_text(encoding="utf-8")
            
            # Extract agent info from prompt (first lines)
            name = md_file.stem
            role = self._extract_role(system_prompt)
            order = self._extract_order(system_prompt)
            
            self.agents.append(Agent(
                name=name,
                role=role,
                order=order,
                system_prompt=system_prompt
            ))
        
        # Sort by order
        self.agents.sort(key=lambda a: a.order)
    
    def _extract_role(self, prompt: str) -> str:
        """Extract role from prompt"""
        # Simple extraction - looks for "role:" or "Papel:"
        for line in prompt.split("\n"):
            if "role:" in line.lower():
                return line.split(":")[1].strip()
        return "Assistant"
    
    def _extract_order(self, prompt: str) -> int:
        """Extract order from prompt"""
        # Simple extraction - looks for "order:" or "ordem:"
        for line in prompt.split("\n"):
            if "order:" in line.lower() or "ordem:" in line.lower():
                try:
                    return int(line.split(":")[1].strip())
                except ValueError as exc:
                    print(f"[orchestrator] ordem inválida em '{line.strip()}': {exc}")
        return 999  # Default order
    
    async def execute(self, message: str, history: List[Dict[str, str]] = None) -> str:
        """
        Execute agents sequentially
        Output of A becomes input of B, etc.
        """
        if not self.agents:
            return "No agents configured for this team"
        
        if history is None:
            history = []
        
        current_input = message
        results = []
        
        # Import here to avoid circular imports
        from llm_client import LLMClient
        llm = LLMClient()
        
        for agent in self.agents:
            # Build messages with history
            messages = []
            
            # Add system prompt
            messages.append({"role": "system", "content": agent.system_prompt})
            
            # Add history
            messages.extend(history)
            
            # Add current input
            messages.append({"role": "user", "content": current_input})
            
            # Get agent response
            response = llm.chat(current_input, agent.system_prompt)
            
            results.append({
                "agent": agent.name,
                "role": agent.role,
                "response": response
            })
            
            # Output becomes input for next agent
            current_input = f"[Previous agent: {agent.role}]\n{response}"
        
        # Return final response (from last agent)
        return results[-1]["response"] if results else "No response"
    
    def get_team_info(self) -> Dict[str, Any]:
        """Get team information"""
        return {
            "name": self.team_name,
            "agent_count": len(self.agents),
            "agents": [
                {"name": a.name, "role": a.role, "order": a.order}
                for a in self.agents
            ]
        }
