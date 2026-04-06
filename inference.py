"""Baseline inference: OpenAI LLM + WebSocket OpenEnv session (persistent state)."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from ticket_triage_env.client import TicketTriageSession, http_to_ws_url
from ticket_triage_env.models import TriageAction, TriageObservation

MAX_TOTAL_REWARD = {"easy": 2.0, "medium": 3.8, "hard": 6.0}
SUCCESS_THRESHOLD = 0.65
STEP_CAP = 48


def _env_base_url() -> str:
    return os.environ.get("ENV_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _make_openai_client() -> Tuple[OpenAI, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base = os.environ.get("API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("MODEL_NAME", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for baseline inference.")
    client = OpenAI(api_key=api_key, base_url=base)
    return client, model


def _obs_to_prompt(obs: TriageObservation) -> str:
    return json.dumps(obs.model_dump(), indent=2)


def _parse_llm_action(text: str) -> TriageAction:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if not m:
        raise ValueError("No JSON object found in model output")
    data = json.loads(m.group(0))
    return TriageAction.model_validate(data)


def _heuristic_for_ticket(t0) -> TriageAction:
    body = (t0.title + " " + t0.body).lower()
    cat = "general"
    if "invoice" in body or "billing" in body or "tax" in body or "card" in body:
        cat = "billing"
    if "password" in body or "login" in body or "portal" in body:
        cat = "account_access"
    if "api" in body or "500" in body or "database" in body or "vpn" in body or "latency" in body:
        cat = "technical"
    pri = "P3"
    if "p1" in body or "failover" in body:
        pri = "P1"
    elif "500" in body or "latency" in body or "vip" in body:
        pri = "P2"
    elif "password" in body or "export" in body or "how do i" in body:
        pri = "P4"
    team = "tier1"
    if pri == "P1":
        team = "oncall"
    elif cat == "billing":
        team = "billing_ops"
    elif cat == "technical" and pri == "P2":
        team = "tier2"
    tags: List[str] = []
    if cat == "billing":
        tags.append("finance_review")
    if "vip" in body:
        tags.append("vip")
    return TriageAction(
        command="set_labels",
        ticket_id=t0.id,
        category=cat,
        priority=pri,
        assign_team=team,
        tags=tags,
        metadata={},
    )


def _heuristic_action(obs: TriageObservation, step_idx: int) -> TriageAction:
    tickets = obs.tickets
    if not tickets:
        return TriageAction(command="submit", metadata={})
    if step_idx <= len(tickets):
        return _heuristic_for_ticket(tickets[step_idx - 1])
    return TriageAction(command="submit", metadata={})


def _llm_next_action(client: OpenAI, model: str, history: List[Dict[str, str]]) -> TriageAction:
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=history,
    )
    content = (resp.choices[0].message.content or "").strip()
    return _parse_llm_action(content)


def run_task(task_key: str, session: TicketTriageSession, use_llm: bool) -> Tuple[float, bool]:
    print(f"[START] Task {task_key}")
    obs = session.reset(task=task_key)
    rewards: List[float] = []
    err_accum: Optional[str] = None

    client: Optional[OpenAI] = None
    model = ""
    if use_llm:
        client, model = _make_openai_client()

    system = (
        "You control an IT ticket triage simulator. Reply with ONE JSON object only, "
        "no markdown, matching this schema:\n"
        '{"command":"set_labels"|"submit","ticket_id":string,"category":string,'
        '"priority":string,"assign_team":string,"tags":string[]}\n'
        "Allowed categories: billing, technical, account_access, general. "
        "Priorities: P4,P3,P2,P1. Teams: tier1,tier2,oncall,billing_ops. "
        "Use set_labels to update tickets; when finished call submit with empty strings."
    )
    last_obs = obs
    history: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": _obs_to_prompt(last_obs)},
    ]

    for step_idx in range(1, STEP_CAP + 1):
        err: Optional[str] = None
        action_str = ""
        try:
            if use_llm and client is not None:
                act = _llm_next_action(client, model, history)
            else:
                act = _heuristic_action(last_obs, step_idx)
            action_str = json.dumps(act.model_dump(exclude_none=True), ensure_ascii=False)
            last_obs = session.step(act)
            r = float(last_obs.reward or 0.0)
            rewards.append(r)
            history.append({"role": "assistant", "content": action_str})
            history.append({"role": "user", "content": _obs_to_prompt(last_obs)})
        except Exception as e:  # noqa: BLE001
            err = str(e)
            err_accum = err
            rewards.append(0.0)
            action_str = json.dumps({"error": err})

        r_last = rewards[-1] if rewards else 0.0
        done = bool(last_obs.done)
        esc = action_str.replace('"', '\\"')
        print(
            f'[STEP] step={step_idx} action="{esc}" reward={r_last:+.2f} '
            f"done={done} error={err if err is not None else None}"
        )
        if err:
            break
        if last_obs.done:
            break

    max_r = MAX_TOTAL_REWARD.get(task_key, 1.0)
    raw = sum(rewards)
    score = max(0.0, min(1.0, raw / max_r if max_r > 0 else 0.0))
    success = score >= SUCCESS_THRESHOLD
    print(f"[END] task={task_key} score={score:.4f} success={success}")
    if err_accum:
        _ = err_accum
    return score, success


def main() -> None:
    _ = os.environ.get("HF_TOKEN", "")
    base = _env_base_url()
    ws_url = http_to_ws_url(base)
    use_llm = bool(os.environ.get("OPENAI_API_KEY"))

    if not use_llm:
        print(
            "Warning: OPENAI_API_KEY not set; running deterministic keyword policy instead.",
            file=sys.stderr,
        )

    tasks = ["easy", "medium", "hard"]
    for t in tasks:
        session = TicketTriageSession(ws_url)
        try:
            run_task(t, session, use_llm=use_llm)
        finally:
            session.close()


if __name__ == "__main__":
    main()

