"""
Hackathon-compatible FastAPI entrypoint for Ticket Triage OpenEnv.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict

from ticket_triage_env.server.triage_environment import TicketTriageEnvironment
from ticket_triage_env.models import TriageAction

app = FastAPI()

# Initialize environment
env = TicketTriageEnvironment()


# ---------------------------
# ROOT ENDPOINT
# ---------------------------

@app.get("/")
async def root():
    return {
        "message": "🧠 Cognition Env - Intelligent Ticket Triage with RL",
        "docs": "/docs",
        "api": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state"
        }
    }


# ---------------------------
# Request Model
# ---------------------------

class ActionRequest(BaseModel):
    command: str
    ticket_id: str = ""
    category: str | None = None
    priority: str | None = None
    assign_team: str | None = None
    tags: list[str] | None = None


# ---------------------------
# ENDPOINTS
# ---------------------------

@app.post("/reset")
async def reset():
    obs = env.reset()

    return {
        "observation": obs.model_dump(),
        "reward": 0.0,
        "done": False,
        "info": {}
    }


@app.post("/step")
async def step(action: ActionRequest):

    # Convert request → TriageAction
    triage_action = TriageAction(**action.model_dump())

    obs = env.step(triage_action)

    return {
        "observation": obs.model_dump(),
        "reward": float(obs.reward),
        "done": bool(obs.done),
        "info": obs.metadata or {}
    }


@app.get("/state")
async def state():
    return env.state.model_dump()


# ---------------------------
# MAIN
# ---------------------------

def main():
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()