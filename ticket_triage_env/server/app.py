"""FastAPI app for the ticket triage OpenEnv server."""

from __future__ import annotations

from openenv.core.env_server.http_server import create_app

from ticket_triage_env.models import TriageAction, TriageObservation
from ticket_triage_env.server.triage_environment import TicketTriageEnvironment

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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
