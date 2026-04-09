"""Episode fixtures for ticket triage tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Literal

TaskKey = Literal["easy", "medium", "hard"]

EPISODES: Dict[TaskKey, Dict[str, Any]] = {
    "easy": {
        "task_name": "Task 1 (Easy) — Single ticket triage",
        "instruction": (
            "Assign the correct category and priority for the ticket. "
            "Use one set_labels action for the ticket, then submit."
        ),
        "constraints_summary": "",
        "tickets_public": [
            {
                "id": "T-E1",
                "title": "VPN disconnects every hour",
                "body": (
                    "Employees on Windows laptops lose VPN connectivity roughly every hour. "
                    "No billing or invoice question — this is infrastructure."
                ),
            }
        ],
        "gold": [
            {
                "id": "T-E1",
                "category": "technical",
                "priority": "P3",
                "assign_team": "tier1",
                "tags": [],
            }
        ],
    },
    "medium": {
        "task_name": "Task 2 (Medium) — Three related tickets",
        "instruction": (
            "Triage all tickets with category, priority, and assign_team. "
            "Then submit when finished."
        ),
        "constraints_summary": "",
        "tickets_public": [
            {
                "id": "T-M1",
                "title": "Invoice #4421 looks wrong",
                "body": "Customer says the March invoice double-charged storage fees.",
            },
            {
                "id": "T-M2",
                "title": "Reset my password",
                "body": "I cannot log in to the customer portal; need password reset link.",
            },
            {
                "id": "T-M3",
                "title": "API returns 500s",
                "body": "Production checkout API intermittently returns HTTP 500 since last deploy.",
            },
        ],
        "gold": [
            {
                "id": "T-M1",
                "category": "billing",
                "priority": "P3",
                "assign_team": "billing_ops",
                "tags": [],
            },
            {
                "id": "T-M2",
                "category": "account_access",
                "priority": "P4",
                "assign_team": "tier1",
                "tags": [],
            },
            {
                "id": "T-M3",
                "category": "technical",
                "priority": "P2",
                "assign_team": "tier2",
                "tags": [],
            },
        ],
    },
    "hard": {
        "task_name": "Task 3 (Hard) — Queue with SLA-style constraints",
        "instruction": (
            "Triage every ticket (category, priority, team, tags). "
            "Follow the global constraints exactly, then submit."
        ),
        "constraints_summary": (
            "Global rules: (1) Any ticket with priority P1 must have assign_team oncall. "
            "(2) Any billing category ticket must use billing_ops and include tag finance_review. "
            "(3) Any ticket whose body contains the word VIP must include tag vip."
        ),
        "tickets_public": [
            {
                "id": "T-H1",
                "title": "VIP customer — card declined",
                "body": "VIP account: card declined at checkout during flash sale.",
            },
            {
                "id": "T-H2",
                "title": "Tax document request",
                "body": "Need corrected tax invoice for Q4; billing question.",
            },
            {
                "id": "T-H3",
                "title": "Production database failover",
                "body": "Primary DB unhealthy; need immediate failover — P1 incident.",
            },
            {
                "id": "T-H4",
                "title": "Feature question",
                "body": "How do I export usage reports as CSV from the dashboard?",
            },
            {
                "id": "T-H5",
                "title": "Latency regression",
                "body": "Search endpoint p95 doubled after yesterday's release.",
            },
        ],
        "gold": [
            {
                "id": "T-H1",
                "category": "billing",
                "priority": "P2",
                "assign_team": "billing_ops",
                "tags": ["finance_review", "vip"],
                "requires_vip_tag": True,
            },
            {
                "id": "T-H2",
                "category": "billing",
                "priority": "P3",
                "assign_team": "billing_ops",
                "tags": ["finance_review"],
                "requires_vip_tag": False,
            },
            {
                "id": "T-H3",
                "category": "technical",
                "priority": "P1",
                "assign_team": "oncall",
                "tags": [],
                "requires_vip_tag": False,
            },
            {
                "id": "T-H4",
                "category": "general",
                "priority": "P4",
                "assign_team": "tier1",
                "tags": [],
                "requires_vip_tag": False,
            },
            {
                "id": "T-H5",
                "category": "technical",
                "priority": "P2",
                "assign_team": "tier2",
                "tags": [],
                "requires_vip_tag": False,
            },
        ],
    },
}

ALLOWED_CATEGORIES = ["billing", "technical", "account_access", "general"]
ALLOWED_PRIORITIES = ["P4", "P3", "P2", "P1"]
ALLOWED_TEAMS = ["tier1", "tier2", "oncall", "billing_ops"]
