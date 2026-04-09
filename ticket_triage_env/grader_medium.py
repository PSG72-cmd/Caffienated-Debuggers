"""Deterministic grader for Task 2 (medium): three tickets, category + priority + team."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def _one_ticket(
    agent_labels: Mapping[str, Dict[str, Any]], ticket_gold: Mapping[str, Any]
) -> float:
    tid = ticket_gold["id"]
    g = agent_labels.get(tid, {})
    cat_ok = (g.get("category") or "").lower().strip() == (
        ticket_gold.get("category") or ""
    ).lower().strip()
    pri_ok = (g.get("priority") or "").strip() == (ticket_gold.get("priority") or "").strip()
    team_ok = (g.get("assign_team") or "").lower().strip() == (
        ticket_gold.get("assign_team") or ""
    ).lower().strip()
    return 0.4 * float(cat_ok) + 0.35 * float(pri_ok) + 0.25 * float(team_ok)


def grade(
    agent_labels: Mapping[str, Dict[str, Any]], tickets_gold: List[Mapping[str, Any]]
) -> float:
    if not tickets_gold:
        return 0.5  # Return middle value instead of 0.0
    parts = [_one_ticket(agent_labels, tg) for tg in tickets_gold]
    score = sum(parts) / len(parts)
    # Clamp to (0, 1) - strictly between, not including endpoints
    return max(0.001, min(0.999, score))
