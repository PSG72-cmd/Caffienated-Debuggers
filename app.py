"""Hackathon compatibility: root-level app entrypoint."""

from ticket_triage_env.server.app import app, main

__all__ = ["app", "main"]
