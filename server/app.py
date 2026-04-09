"""FastAPI app for the ticket triage OpenEnv server - root level entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the parent directory is in the path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from openenv.core.env_server.http_server import create_app
from ticket_triage_env.models import TriageAction, TriageObservation
from ticket_triage_env.server.triage_environment import TicketTriageEnvironment

# Create the FastAPI app
app = create_app(
    TicketTriageEnvironment,
    TriageAction,
    TriageObservation,
    env_name="ticket_triage_env",
)


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


def main() -> None:
    """Main entry point for the server."""
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()


