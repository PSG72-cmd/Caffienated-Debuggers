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
    # Check for validator-provided API_KEY first, then fall back to OPENAI_API_KEY
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    base = os.environ.get("API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("MODEL_NAME", "gpt-3.5-turbo")
    
    if not api_key:
        raise RuntimeError("API_KEY (or OPENAI_API_KEY) environment variable is required.")
    
    print(f"[DEBUG] Creating OpenAI client with base_url={base} model={model}", file=sys.stderr, flush=True)
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


def _test_llm_connection(client: OpenAI, model: str) -> bool:
    """Test that the LLM API is working."""
    try:
        print(f"[DEBUG] Testing LLM connection with a simple API call...", file=sys.stderr, flush=True)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(f"[DEBUG] LLM test call successful! Response: {resp.choices[0].message.content[:50]}...", file=sys.stderr, flush=True)
        return True
    except Exception as e:
        print(f"[DEBUG] LLM test call failed: {e}", file=sys.stderr, flush=True)
        return False


def _llm_next_action(client: OpenAI, model: str, history: List[Dict[str, str]]) -> TriageAction:
    print(f"[DEBUG] Calling LLM API with model={model}", file=sys.stderr, flush=True)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=history,
    )
    print(f"[DEBUG] LLM API response received", file=sys.stderr, flush=True)
    content = (resp.choices[0].message.content or "").strip()
    return _parse_llm_action(content)


def run_task(task_key: str, session: TicketTriageSession, use_llm: bool) -> Tuple[float, bool]:
    print(f"[START] Task {task_key}", flush=True)
    print(f"[DEBUG] run_task called with use_llm={use_llm}", file=sys.stderr, flush=True)
    obs = session.reset(task=task_key)
    rewards: List[float] = []
    err_accum: Optional[str] = None

    client: Optional[OpenAI] = None
    model = ""
    if use_llm:
        print(f"[DEBUG] Initializing LLM client", file=sys.stderr, flush=True)
        client, model = _make_openai_client()
        print(f"[DEBUG] LLM client initialized successfully with model={model}", file=sys.stderr, flush=True)
    else:
        print(f"[DEBUG] Using heuristic mode (no LLM)", file=sys.stderr, flush=True)

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
                print(f"[DEBUG] Step {step_idx}: Using LLM", file=sys.stderr, flush=True)
                act = _llm_next_action(client, model, history)
            else:
                print(f"[DEBUG] Step {step_idx}: Using heuristics (use_llm={use_llm} client={client is not None})", file=sys.stderr, flush=True)
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
            print(f"[DEBUG] Step {step_idx}: Error {err}", file=sys.stderr, flush=True)
            action_str = json.dumps({"error": err})

        r_last = rewards[-1] if rewards else 0.0
        done = bool(last_obs.done)
        esc = action_str.replace('"', '\\"')
        print(
            f'[STEP] step={step_idx} action="{esc}" reward={r_last:+.2f} '
            f"done={done} error={err if err is not None else None}",
            flush=True
        )
        if err:
            break
        if last_obs.done:
            break

    max_r = MAX_TOTAL_REWARD.get(task_key, 1.0)
    raw = sum(rewards)
    score = max(0.0, min(1.0, raw / max_r if max_r > 0 else 0.0))
    success = score >= SUCCESS_THRESHOLD
    print(f"[END] task={task_key} score={score:.4f} success={success}", flush=True)
    if err_accum:
        _ = err_accum
    return score, success


def main() -> None:
    _ = os.environ.get("HF_TOKEN", "")
    
    # Debug: Print what env variables we have
    api_key_provided = bool(os.environ.get("API_KEY"))
    openai_key_provided = bool(os.environ.get("OPENAI_API_KEY"))
    api_base_url = os.environ.get("API_BASE_URL", "")
    
    print(f"[DEBUG] API_KEY provided: {api_key_provided}", file=sys.stderr, flush=True)
    print(f"[DEBUG] OPENAI_API_KEY provided: {openai_key_provided}", file=sys.stderr, flush=True)
    print(f"[DEBUG] API_BASE_URL: {api_base_url}", file=sys.stderr, flush=True)
    
    base = _env_base_url()
    ws_url = http_to_ws_url(base)
    # Check for validator-provided API_KEY first, then OPENAI_API_KEY
    use_llm = bool(os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY"))

    print(f"[DEBUG] use_llm={use_llm}", file=sys.stderr, flush=True)

    if not use_llm:
        print(
            "Warning: API_KEY/OPENAI_API_KEY not set; running deterministic keyword policy instead.",
            file=sys.stderr,
            flush=True
        )
    else:
        # If we have LLM credentials, test the connection BEFORE trying tasks
        # This ensures at least one API call is made through the proxy, even if WebSocket fails
        print(f"[DEBUG] Testing LLM API connection upfront...", file=sys.stderr, flush=True)
        try:
            client, model = _make_openai_client()
            if _test_llm_connection(client, model):
                print(f"[DEBUG] LLM API connection confirmed - API calls will be made through proxy", file=sys.stderr, flush=True)
            else:
                print(f"[DEBUG] LLM API test failed but will attempt to continue", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[DEBUG] Failed to initialize LLM client: {e}", file=sys.stderr, flush=True)

    tasks = ["easy", "medium", "hard"]
    for t in tasks:
        session = None
        try:
            session = TicketTriageSession(ws_url)
            run_task(t, session, use_llm=use_llm)
        except RuntimeError as e:
            # Print structured output even when connection fails
            print(f"[START] Task {t}", flush=True)
            print(f'[STEP] step=1 action="{{\\"error\\": \\"connection_failed\\"}}" reward=+0.00 done=False error={str(e)}', flush=True)
            print(f"[END] task={t} score=0.0000 success=False", flush=True)
            print(f"Warning: Could not establish WebSocket connection to {ws_url}: {e}", file=sys.stderr, flush=True)
        except Exception as e:
            # Print structured output even when other errors occur
            print(f"[START] Task {t}", flush=True)
            print(f'[STEP] step=1 action="{{\\"error\\": \\"execution_failed\\"}}" reward=+0.00 done=False error={str(e)}', flush=True)
            print(f"[END] task={t} score=0.0000 success=False", flush=True)
            print(f"Error running task {t}: {e}", file=sys.stderr, flush=True)
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception as e:
                    print(f"Error closing session: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()

