"""Deterministic grader for Task 1 (easy): single ticket category + priority."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def grade(agent_labels: Mapping[str, Dict[str, Any]], gold: Mapping[str, Any]) -> float:
    """Return score strictly in (0.0, 1.0) for the easy task."""
    tid = gold["id"]
    guess = agent_labels.get(tid, {})
    cat_ok = (guess.get("category") or "").lower().strip() == (
        gold.get("category") or ""
    ).lower().strip()
    pri_ok = (guess.get("priority") or "").strip() == (gold.get("priority") or "").strip()
    score = 0.5 * float(cat_ok) + 0.5 * float(pri_ok)
    # Clamp to (0, 1) - strictly between, not including endpoints
    return max(0.001, min(0.999, score))
