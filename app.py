"""
Hackathon-compatible FastAPI entrypoint for Ticket Triage OpenEnv.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from ticket_triage_env.server.triage_environment import TicketTriageEnvironment
from ticket_triage_env.models import TriageAction

app = FastAPI()

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize environment
env = TicketTriageEnvironment()



# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ---------------------------
# ROOT ENDPOINT
# ---------------------------

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/info")
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

    # Convert request → TriageAction, excluding None so defaults apply
    triage_action = TriageAction(**action.model_dump(exclude_none=True))

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