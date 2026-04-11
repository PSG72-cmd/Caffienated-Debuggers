"""
Pydantic v2 models for Cognition Env (ticket triage environment).

This module defines the contract between agents and the environment:
  - TriageAction: What agents can do
  - TriageObservation: What agents see
  - Reward: Structured reward breakdown
  - TicketView: Individual ticket representation

All models use Pydantic v2 for automatic validation, serialization (JSON),
and API documentation (OpenAPI/Swagger).

Example:
    # Create an action
    action = TriageAction(
        command="set_labels",
        ticket_id="TICK-001",
        category="technical",
        priority="P3",
        assign_team="tier1",
        tags=["urgent"]
    )
    
    # Create an observation (typically returned by environment)
    obs = TriageObservation(
        task_key="easy",
        tickets=[...],
        reward=0.25,
        done=False,
        feedback="Category set correctly",
        ...
    )
"""

from __future__ import annotations

from typing import List, Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field


class Reward(BaseModel):
    """Structured reward components for one environment step (documentation + logging)."""

    step_total: float = Field(
        ...,
        description="Total scalar reward returned for this step (matches observation.reward).",
    )
    partial_credit: float = Field(
        0.0,
        description="Credit from correct triage fields or satisfied constraints this step.",
    )
    penalty: float = Field(
        0.0,
        description="Penalty for invalid or harmful actions (negative or zero).",
    )
    terminal_grader_component: float = Field(
        0.0,
        description="On submit: portion tied to deterministic grader score [0,1].",
    )


class TicketView(BaseModel):
    """One ticket visible to the agent."""

    id: str
    title: str
    body: str


class TriageAction(Action):
    """Agent triage decision for one ticket, or episode submission."""

    command: Literal["set_labels", "submit"] = Field(
        ...,
        description='Use "set_labels" to update one ticket; "submit" to finish and grade.',
    )
    ticket_id: str = Field(
        default="",
        description="Ticket id from the observation (required for set_labels).",
    )
    category: str = Field(
        default="",
        description="One of: billing | technical | account_access | general",
    )
    priority: str = Field(
        default="",
        description="One of: P4 | P3 | P2 | P1",
    )
    assign_team: str = Field(
        default="",
        description="One of: tier1 | tier2 | oncall | billing_ops",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Lowercase tags to attach (e.g. finance_review, vip).",
    )


class TriageObservation(Observation):
    """What the agent sees after reset or each step."""

    task_name: str = Field(default="", description="Human-readable task title")
    task_key: Literal["easy", "medium", "hard"] = Field(
        default="easy",
        description="Which benchmark task is active",
    )
    instruction: str = Field(default="", description="What the agent should accomplish")
    tickets: List[TicketView] = Field(default_factory=list)
    feedback: str = Field(
        default="",
        description="Result of the last action (hints, validation errors, summary).",
    )
    constraints_summary: str = Field(
        default="",
        description="Extra global rules for the hard task (may be empty).",
    )
    allowed_categories: List[str] = Field(default_factory=list)
    allowed_priorities: List[str] = Field(default_factory=list)
    allowed_teams: List[str] = Field(default_factory=list)
    step_limit: int = Field(default=20, description="Recommended max steps before giving up")
