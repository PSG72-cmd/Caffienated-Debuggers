"""
FastAPI application server for Cognition Env (OpenEnv ticket triage environment).

This module creates the HTTP REST API and WebSocket interface for the IT support
ticket triage reinforcement learning environment. It exposes three main endpoints:
  - POST /reset: Initialize a new episode
  - POST /step: Execute an action in the current episode
  - GET /state: Query current environment state

The server uses FastAPI + Uvicorn for production-grade ASGI deployment.

Example:
    Start the server locally:
        $ python -m uvicorn ticket_triage_env.server.app:app --host 0.0.0.0 --port 8000
    
    Or use the console script entry point:
        $ server

    Then access the interactive API docs at http://localhost:8000/docs
"""

from __future__ import annotations

from openenv.core.env_server.http_server import create_app
from fastapi.middleware.cors import CORSMiddleware

from ticket_triage_env.models import TriageAction, TriageObservation
from ticket_triage_env.server.triage_environment import TicketTriageEnvironment

# Create FastAPI application with OpenEnv HTTP server wrapper
# This automatically adds /reset, /step, /state endpoints and WebSocket support
app = create_app(
    TicketTriageEnvironment,
    TriageAction,
    TriageObservation,
    env_name="ticket_triage_env",
)

# Enable CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    """
    Root endpoint providing API overview and navigation.
    
    This is a convenience endpoint for developers. For interactive API documentation,
    visit /docs (Swagger UI) or /redoc (ReDoc).
    
    Returns:
        dict: API information including endpoint URLs and documentation links.
    """
    return {
        "message": "🧠 Cognition Env - Intelligent Ticket Triage with RL",
        "docs": "/docs",
        "api": {
            "reset": "POST /reset",
            "step": "POST /step",
            "state": "GET /state",
            "websocket": "WS /ws"
        },
        "learn_more": "https://github.com/your-org/cognition-env"
    }


def main() -> None:
    """
    Entry point for running the server as a console script.
    
    Starts a production-grade Uvicorn ASGI server on 0.0.0.0:8000.
    Use this function via the pip console_scripts entry point:
        $ server
    
    Or call directly:
        $ python -m ticket_triage_env.server.app
    """
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
