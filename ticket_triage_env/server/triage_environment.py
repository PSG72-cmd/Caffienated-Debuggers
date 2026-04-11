"""Ticket triage environment: reset, step, state, rewards, and task episodes."""

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
    return sorted({t.lower().strip() for t in tags if t.strip()})


class TicketTriageEnvironment(Environment[TriageAction, TriageObservation, State]):
    """Simulates helpdesk triage with partial per-step rewards and terminal grading."""

    SUPPORTS_CONCURRENT_SESSIONS = True

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="ticket_triage_env",
            description=(
                "IT ticket triage: assign category, priority, team, and tags; "
                "three graded tasks (easy/medium/hard)."
            ),
            version="0.1.0",
            author="OpenEnv Hackathon",
        )

    def __init__(self) -> None:
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
        task = kwargs.get("task")
        if task not in ("easy", "medium", "hard", None):
            task = "easy"
        task_key: TaskKey = task if task is not None else "easy"

        self._state = State(episode_id=episode_id or str(uuid4()), step_count=0)
        self._task_key = task_key
        self._cfg = copy.deepcopy(EPISODES[task_key])
        self._gold = copy.deepcopy(self._cfg["gold"])
        self._tickets_view = [TicketView(**t) for t in self._cfg["tickets_public"]]
        self._agent = {}
        self._credited = {g["id"]: set() for g in self._gold}
        self._submitted = False
        _ = seed

        return self._build_observation(
            done=False,
            reward=0.0,
            feedback="Episode started. Use set_labels per ticket, then submit.",
        )

    def _validate_enums(self, action: TriageAction) -> Optional[str]:
        if action.category and action.category.lower().strip() not in ALLOWED_CATEGORIES:
            return f"Invalid category {action.category!r}."
        if action.priority and action.priority.strip() not in ALLOWED_PRIORITIES:
            return f"Invalid priority {action.priority!r}."
        if action.assign_team and action.assign_team.lower().strip() not in ALLOWED_TEAMS:
            return f"Invalid assign_team {action.assign_team!r}."
        return None

    def _gold_for(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        for g in self._gold:
            if g["id"] == ticket_id:
                return g
        return None

    def _partial_for_ticket(
        self, ticket_id: str, slot: Dict[str, Any], gold: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        credited = self._credited.setdefault(ticket_id, set())
        add = 0.0
        msgs: List[str] = []

        def try_field(key: str, ok: bool, weight: float, label: str) -> None:
            nonlocal add
            if ok and key not in credited:
                credited.add(key)
                add += weight
                msgs.append(f"+{weight:.2f} {label} correct")

        cat = (slot.get("category") or "").lower().strip()
        pri = (slot.get("priority") or "").strip()
        team = (slot.get("assign_team") or "").lower().strip()
        tags = set(_norm_tag_list(list(slot.get("tags") or [])))

        try_field("category", bool(cat) and cat == gold["category"], 0.18, "category")
        try_field("priority", bool(pri) and pri == gold["priority"], 0.18, "priority")
        try_field(
            "assign_team",
            bool(team) and team == gold["assign_team"],
            0.14,
            "team",
        )
        gold_tags = {t.lower() for t in (gold.get("tags") or [])}
        if gold_tags and gold_tags.issubset(tags):
            if "tags" not in credited:
                credited.add("tags")
                add += 0.2
                msgs.append("+0.20 required tags satisfied")

        return add, msgs

    def _merge_slot(self, ticket_id: str, action: TriageAction) -> Dict[str, Any]:
        cur = dict(self._agent.get(ticket_id, {}))
        if action.category:
            cur["category"] = action.category.lower().strip()
        if action.priority:
            cur["priority"] = action.priority.strip()
        if action.assign_team:
            cur["assign_team"] = action.assign_team.lower().strip()
        if action.tags:
            merged = set(_norm_tag_list(list(cur.get("tags") or [])))
            merged.update(_norm_tag_list(action.tags))
            cur["tags"] = sorted(merged)
        self._agent[ticket_id] = cur
        return cur

    def step(
        self,
        action: TriageAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> TriageObservation:
        self._state.step_count += 1
        _ = timeout_s

        if self._submitted:
            r = Reward(
                step_total=-0.02,
                partial_credit=0.0,
                penalty=-0.02,
                terminal_grader_component=0.0,
            )
            obs = self._build_observation(
                done=True,
                reward=r.step_total,
                feedback="Episode already finished.",
                extra_meta={"reward_breakdown": r.model_dump(), "grader_score": None},
            )
            obs.metadata["reward_breakdown"] = r.model_dump()
            return obs

        err = self._validate_enums(action)
        if err:
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
