"""
Core RL environment for IT support ticket triage with reward shaping.

This module implements `TicketTriageEnvironment`, which simulates a real-world
helpdesk ticket triage scenario. Agents learn to:
  - Classify tickets (category, priority)
  - Route to teams (tier1, tier2, oncall, billing_ops)
  - Apply relevant tags (e.g., vip, urgent, finance_review)

## Key Design Patterns

1. **Reward Shaping:** Agents receive partial credit (+0.1–0.5) when fields become
   correct, enabling faster training than sparse rewards. Terminal reward comes from
   deterministic graders (0.0–1.0 based on task correctness).

2. **Three Task Levels:**
   - Easy: 1 ticket, 2 fields (category + priority)
   - Medium: 3 tickets, 3 fields each (category + priority + team)
   - Hard: 5 tickets, 3 fields + global business logic constraints

3. **Deterministic Grading:** Same input always produces same score, ensuring
   reproducible evaluation across agents and seeds.

4. **Episode State Management:** Each episode tracks:
   - Agent assignments (what agent has set so far)
   - Credited fields (prevent double-rewarding)
   - Gold labels (hidden from agent, used for grading)
   - Cumulative rewards

## Reward Breakdown

- **set_labels action:** Per-field partial credit (first-time only)
- **submit action:** Terminal reward = base_score + (0.5 × grader_score)
- **After submit:** Small negative penalty (-0.02) to discourage post-submission steps

## Example Usage

    from ticket_triage_env.server.triage_environment import TicketTriageEnvironment
    from ticket_triage_env.models import TriageAction
    
    env = TicketTriageEnvironment()
    obs = env.reset(task="easy")  # Start easy task
    
    # Agent takes action
    action = TriageAction(
        command="set_labels",
        ticket_id=obs.tickets[0].id,
        category="technical",
        priority="P3"
    )
    obs = env.step(action)
    print(f"Reward: {obs.reward}, Feedback: {obs.feedback}")
    
    # Agent submits when confident
    submit_action = TriageAction(command="submit")
    obs = env.step(submit_action)
    print(f"Done: {obs.done}, Grader Score: {obs.metadata['grader_score']}")
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata, State

from ticket_triage_env import grader_easy, grader_hard, grader_medium
from ticket_triage_env.episode_data import (
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    ALLOWED_TEAMS,
    EPISODES,
    TaskKey,
)
from ticket_triage_env.models import Reward, TicketView, TriageAction, TriageObservation


def _norm_tag_list(tags: List[str]) -> List[str]:
    """
    Normalize and deduplicate a list of tags.
    
    Converts to lowercase, strips whitespace, deduplicates, and sorts.
    Empty strings are removed.
    
    Args:
        tags: List of tag strings (may have duplicates or whitespace)
    
    Returns:
        Sorted list of unique, normalized tags
    
    Example:
        >>> _norm_tag_list(["VIP", "  urgent  ", "vip"])
        ['urgent', 'vip']
    """
    return sorted({t.lower().strip() for t in tags if t.strip()})


class TicketTriageEnvironment(Environment[TriageAction, TriageObservation, State]):
    """
    OpenEnv environment for IT support ticket triage with reinforcement learning.
    
    This environment simulates a helpdesk where agents learn to triage support tickets
    by assigning categories, priorities, teams, and tags. It provides reward shaping
    to accelerate RL training and deterministic grading for reproducible evaluation.
    
    Attributes:
        SUPPORTS_CONCURRENT_SESSIONS (bool): Indicates this environment can handle
            multiple simultaneous episodes (true).
    
    Task Modes:
        - "easy": Single ticket, 2 fields (category + priority)
        - "medium": 3 tickets, 3 fields each (category + priority + team)
        - "hard": 5 tickets, 3 fields + business logic constraints
    
    Actions:
        - "set_labels": Update one ticket's assigned fields
        - "submit": End episode and trigger grading
    
    Rewards:
        - Partial credit: +0.1–0.5 per correct field (first time only)
        - Terminal reward: 0.5–1.0 based on grader score
        - Penalties: -0.05–-0.1 for invalid actions
    
    Interface Compliance:
        Fully implements OpenEnv Environment interface:
        - reset(seed, episode_id, **kwargs) -> Observation
        - step(action) -> Observation
        - get_metadata() -> EnvironmentMetadata
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def get_metadata(self) -> EnvironmentMetadata:
        """
        Return environment metadata for OpenEnv registration.
        
        Returns:
            EnvironmentMetadata with name, description, version, author
        """
        return EnvironmentMetadata(
            name="ticket_triage_env",
            description=(
                "IT ticket triage: assign category, priority, team, and tags; "
                "three graded tasks (easy/medium/hard) with reward shaping and "
                "deterministic terminal evaluation."
            ),
            version="0.1.0",
            author="OpenEnv Hackathon",
        )

    def __init__(self) -> None:
        """Initialize environment state (empty until reset is called)."""
        super().__init__(transform=None, rubric=None)
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task_key: TaskKey = "easy"
        self._cfg: Dict[str, Any] = {}
        self._gold: List[Dict[str, Any]] = []
        self._tickets_view: List[TicketView] = []
        self._agent: Dict[str, Dict[str, Any]] = {}
        self._credited: Dict[str, Set[str]] = {}
        self._submitted = False

    def _build_observation(
        self,
        *,
        done: bool,
        reward: float,
        feedback: str,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> TriageObservation:
        """
        Construct a TriageObservation with current episode state.
        
        Args:
            done: Whether episode is finished
            reward: Scalar reward for this step
            feedback: Human-readable feedback on agent's action
            extra_meta: Additional metadata (e.g., grader_score)
        
        Returns:
            TriageObservation with all required fields populated
        """
        meta: Dict[str, Any] = {"reward_breakdown": None, "grader_score": None}
        if extra_meta:
            meta.update(extra_meta)
        return TriageObservation(
            done=done,
            reward=reward,
            metadata=meta,
            task_name=self._cfg.get("task_name", ""),
            task_key=self._task_key,
            instruction=self._cfg.get("instruction", ""),
            tickets=list(self._tickets_view),
            feedback=feedback,
            constraints_summary=self._cfg.get("constraints_summary", ""),
            allowed_categories=ALLOWED_CATEGORIES,
            allowed_priorities=ALLOWED_PRIORITIES,
            allowed_teams=ALLOWED_TEAMS,
            step_limit={"easy": 12, "medium": 30, "hard": 45}[self._task_key],
        )

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> TriageObservation:
        """
        Initialize a new episode.
        
        Loads the task configuration, resets agent state, and returns initial
        observation with tickets and instructions.
        
        Args:
            seed: Random seed (currently unused; fixtures are deterministic)
            episode_id: Custom episode ID (default: UUID4)
            **kwargs: Extra options including 'task' to specify (easy|medium|hard)
        
        Returns:
            TriageObservation with initial state (done=False, reward=0.0)
            r = Reward(
                step_total=-0.08,
                partial_credit=0.0,
                penalty=-0.08,
                terminal_grader_component=0.0,
            )
            obs = self._build_observation(
                done=False,
                reward=r.step_total,
                feedback=err,
                extra_meta={"reward_breakdown": r.model_dump()},
            )
            obs.metadata["reward_breakdown"] = r.model_dump()
            return obs

        if action.command == "submit":
            if self._task_key == "easy":
                score = grader_easy.grade(self._agent, self._gold[0])
            elif self._task_key == "medium":
                score = grader_medium.grade(self._agent, self._gold)
            else:
                score = grader_hard.grade(self._agent, self._gold)

            terminal_scale = {"easy": 1.4, "medium": 2.2, "hard": 3.0}[self._task_key]
            terminal = terminal_scale * score
            r = Reward(
                step_total=terminal,
                partial_credit=0.0,
                penalty=0.0,
                terminal_grader_component=terminal,
            )
            self._submitted = True
            obs = self._build_observation(
                done=True,
                reward=terminal,
                feedback=(
                    f"Submitted. Deterministic grader score={score:.3f} "
                    f"(terminal reward scaled for task difficulty)."
                ),
                extra_meta={"reward_breakdown": r.model_dump(), "grader_score": score},
            )
            obs.metadata["reward_breakdown"] = r.model_dump()
            obs.metadata["grader_score"] = score
            return obs

        tid = action.ticket_id.strip()
        if not tid:
            r = Reward(
                step_total=-0.06,
                partial_credit=0.0,
                penalty=-0.06,
                terminal_grader_component=0.0,
            )
            obs = self._build_observation(
                done=False,
                reward=r.step_total,
                feedback="ticket_id is required for set_labels.",
                extra_meta={"reward_breakdown": r.model_dump()},
            )
            obs.metadata["reward_breakdown"] = r.model_dump()
            return obs

        gold = self._gold_for(tid)
        if gold is None:
            r = Reward(
                step_total=-0.06,
                partial_credit=0.0,
                penalty=-0.06,
                terminal_grader_component=0.0,
            )
            obs = self._build_observation(
                done=False,
                reward=r.step_total,
                feedback=f"Unknown ticket_id {tid!r}.",
                extra_meta={"reward_breakdown": r.model_dump()},
            )
            obs.metadata["reward_breakdown"] = r.model_dump()
            return obs

        slot = self._merge_slot(tid, action)
        partial, msgs = self._partial_for_ticket(tid, slot, gold)
        if not msgs:
            fb = f"Updated {tid}; no new partial credit (already credited or still incorrect)."
        else:
            fb = f"Updated {tid}: " + "; ".join(msgs)

        r = Reward(
            step_total=partial,
            partial_credit=partial,
            penalty=0.0,
            terminal_grader_component=0.0,
        )
        obs = self._build_observation(
            done=False,
            reward=partial,
            feedback=fb,
            extra_meta={"reward_breakdown": r.model_dump()},
        )
        obs.metadata["reward_breakdown"] = r.model_dump()
        return obs

    @property
    def state(self) -> State:
        return State(episode_id=self._state.episode_id, step_count=self._state.step_count)
