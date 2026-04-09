"""WebSocket client for persistent sessions (HTTP /step is stateless)."""

from __future__ import annotations

import json
from typing import Any, Dict
from urllib.parse import urlparse, urlunparse

from ticket_triage_env.models import TriageAction, TriageObservation


def http_to_ws_url(base_http_url: str) -> str:
    p = urlparse(base_http_url)
    scheme = "wss" if p.scheme == "https" else "ws"
    path = (p.path or "").rstrip("/") + "/ws"
    return urlunparse((scheme, p.netloc, path, "", "", ""))


class TicketTriageSession:
    """Minimal sync WebSocket session (uses `websocket-client`)."""

    def __init__(self, ws_url: str) -> None:
        import websocket  # type: ignore

        self._ws = websocket.create_connection(ws_url)

    def close(self) -> None:
        try:
            self._ws.send(json.dumps({"type": "close"}))
        except Exception:
            pass
        self._ws.close()

    def reset(self, task: str = "easy") -> TriageObservation:
        self._ws.send(json.dumps({"type": "reset", "data": {"task": task}}))
        raw = self._ws.recv()
        return self._parse_obs_msg(raw)

    def step(self, action: TriageAction) -> TriageObservation:
        payload = action.model_dump(exclude_none=True)
        self._ws.send(json.dumps({"type": "step", "data": payload}))
        raw = self._ws.recv()
        return self._parse_obs_msg(raw)

    def _parse_obs_msg(self, raw: str) -> TriageObservation:
        msg = json.loads(raw)
        if msg.get("type") == "error":
            raise RuntimeError(str(msg.get("data", {})))
        data = msg.get("data") or {}
        inner = dict(data.get("observation") or {})
        inner["reward"] = data.get("reward")
        inner["done"] = bool(data.get("done", False))
        return TriageObservation.model_validate(inner)
