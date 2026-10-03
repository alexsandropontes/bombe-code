"""
Backend API for Chatbot
Simple HTTP API for chat operations
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os

from llm_client import LLMClient
from orchestrator import AgentOrchestrator

app = FastAPI(title="Chatbot API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    team: str
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    response: str
    team: str
    agents_used: List[str]


class TeamInfo(BaseModel):
    name: str
    agents: List[Dict[str, str]]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/teams")
def list_teams():
    """List available teams"""
    teams_dir = os.path.join(os.path.dirname(__file__), "..", "agents", "teams")
    
    if not os.path.exists(teams_dir):
        return []
    
    teams = []
    for team_folder in os.listdir(teams_dir):
        team_path = os.path.join(teams_dir, team_folder)
        if os.path.isdir(team_path):
            # Check if team has agent files
            md_files = list(os.path.join(team_path, f) for f in os.listdir(team_path) if f.endswith('.md'))
            if md_files:
                teams.append(team_folder)
    
    return teams


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Send message to agent team"""
    try:
        orchestrator = AgentOrchestrator(request.team)
        response = orchestrator.execute(request.message, request.history)
        
        return ChatResponse(
            response=response,
            team=request.team,
            agents_used=[a["name"] for a in orchestrator.agents]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
