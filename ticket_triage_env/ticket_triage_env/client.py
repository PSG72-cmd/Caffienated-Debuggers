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

    def __init__(self, ws_url: str, max_retries: int = 5) -> None:
        import time
        import websocket  # type: ignore

        self._ws = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self._ws = websocket.create_connection(ws_url, timeout=10)
                print(f"WebSocket connected successfully on attempt {attempt + 1}", file=__import__('sys').stderr, flush=True)
                return
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # exponential backoff: 1s, 2s, 4s, 8s, 16s (31s total)
                    print(f"WebSocket connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait_time}s...", file=__import__('sys').stderr, flush=True)
                    time.sleep(wait_time)
        
        # If we get here, all retries failed
        raise RuntimeError(f"Failed to connect to WebSocket at {ws_url} after {max_retries} attempts. Last error: {last_error}") from last_error

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
