"""Deterministic grader for Task 3 (hard): five tickets + global constraints."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Set


def _field_accuracy(
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
    gold_tags: Set[str] = set(ticket_gold.get("tags") or [])
    guess_tags: Set[str] = {t.lower().strip() for t in (g.get("tags") or [])}
    if not gold_tags:
        tag_ok = True
    else:
        tag_ok = gold_tags.issubset(guess_tags)
    tag_part = 1.0 if tag_ok else 0.0
    raw = (0.3 * float(cat_ok) + 0.3 * float(pri_ok) + 0.25 * float(team_ok) + 0.15 * tag_part)
    # Clamp to ensure we never return exactly 0.0 or 1.0
    epsilon = 0.0001
    return max(epsilon, min(1.0 - epsilon, raw))


def _constraints(
    agent_labels: Mapping[str, Dict[str, Any]], tickets_gold: List[Mapping[str, Any]]
) -> float:
    """Fraction of constraint checks passed (each ticket may contribute rules)."""
    checks: List[bool] = []
    for tg in tickets_gold:
        tid = tg["id"]
        g = agent_labels.get(tid, {})
        pri = (g.get("priority") or "").strip()
        team = (g.get("assign_team") or "").lower().strip()
        cat = (g.get("category") or "").lower().strip()
        tags = {t.lower().strip() for t in (g.get("tags") or [])}

        if pri == "P1":
            checks.append(team == "oncall")
        if cat == "billing":
            checks.append(team == "billing_ops")
            checks.append("finance_review" in tags)
        if tg.get("requires_vip_tag"):
            checks.append("vip" in tags)
    if not checks:
        return 0.5  # Return 0.5 instead of 1.0 to stay strictly within (0, 1)
    return sum(1.0 for c in checks if c) / len(checks)


def grade(
    agent_labels: Mapping[str, Dict[str, Any]], tickets_gold: List[Mapping[str, Any]]
) -> float:
    if not tickets_gold:
        return 0.5  # Return middle value instead of 0.0
    acc = sum(_field_accuracy(agent_labels, tg) for tg in tickets_gold) / len(tickets_gold)
    cons = _constraints(agent_labels, tickets_gold)
    score = max(0.0, min(1.0, 0.65 * acc + 0.35 * cons))
    # Clamp to (0, 1) - strictly between, not including endpoints
    # Use a small epsilon to ensure we never hit 0.0 or 1.0
    epsilon = 0.0001
    clamped = max(epsilon, min(1.0 - epsilon, score))
    return clamped
