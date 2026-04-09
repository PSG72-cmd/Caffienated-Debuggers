---
title: Cognition Env
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
python_version: "3.10"
app_port: 7860
suggested_hardware: "cpu-basic"
short_description: Intelligent ticket triage with reinforcement learning
tags:
  - reinforcement-learning
  - openenv
  - ai-agents
  - simulation
  - llm
pinned: true
---

# 🧠 Cognition Env

**Cognition Env** is a real-world OpenEnv environment where AI agents learn intelligent IT ticket triage using reinforcement learning ⚙️

---

## 🚀 What This Does

- Simulates real-world **helpdesk ticket triage**
- Agents learn to:
  - Assign **category**
  - Set **priority**
  - Choose **team**
  - Add **relevant tags**
- Uses **reward-driven learning with partial feedback**

---

## 🎯 Tasks

- 🟢 Easy → Basic ticket classification  
- 🟡 Medium → Multi-ticket structured triage  
- 🔴 Hard → Complex decision-making with constraints  

✔ Deterministic graders → scores from **0.0 to 1.0**

---

## ⚙️ OpenEnv Compliance

- `reset()` → start episode  
- `step(action)` → interaction loop  
- `state()` → current environment state  

✔ Typed models (Pydantic)  
✔ Reward shaping (not sparse)  
✔ Clean RL loop  

---

## 🧪 API

```bash
POST /reset
POST /step
GET  /state
```

---

## 📋 Action / observation / reward models

| Model | Role |
|-------|------|
| `TriageAction` | `command`: `set_labels` \| `submit`; optional `ticket_id`, `category`, `priority`, `assign_team`, `tags`. |
| `TriageObservation` | Task text, ticket list, allowed enums, feedback, `done`, `reward`, `metadata` (includes `grader_score` after submit). |
| `Reward` | Documented breakdown: `partial_credit`, `penalty`, `terminal_grader_component`, `step_total`. |

## Action / observation / reward models

| Model | Role |
|-------|------|
| `TriageAction` | `command`: `set_labels` \| `submit`; optional `ticket_id`, `category`, `priority`, `assign_team`, `tags`. |
| `TriageObservation` | Task text, ticket list, allowed enums, feedback, `done`, `reward`, `metadata` (includes `grader_score` after submit). |
| `Reward` | Documented breakdown: `partial_credit`, `penalty`, `terminal_grader_component`, `step_total`. |

## Tasks (easy → hard)

| Task | Goal | Grader (0–1) |
|------|------|----------------|
| **easy** | One ticket: correct **category** + **priority**. | `0.5` cat + `0.5` pri (`grader_easy.py`). |
| **medium** | Three tickets: **category**, **priority**, **team**. | Per-ticket `0.4` cat + `0.35` pri + `0.25` team, averaged (`grader_medium.py`). |
| **hard** | Five tickets + **global constraints** (P1→oncall, billing→`billing_ops`+`finance_review`, VIP body→`vip` tag). | `0.65` field accuracy + `0.35` constraint satisfaction (`grader_hard.py`). |

## Reward shaping (partial credit)

- **set_labels**: small positive reward the **first time** each field becomes correct for that ticket (category, priority, team, required tags); penalties for invalid enums, unknown `ticket_id`, or missing `ticket_id`.
- **submit**: terminal reward scaled by task difficulty × grader score.
- **After submit**: stepping again yields a small negative penalty (episode finished).

## Setup

```bash
cd ticket_triage_env
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
```

## Build Docker

```bash
docker build -t ticket-triage-env:latest .
docker run --rm -p 8000:8000 ticket-triage-env:latest
```

`POST /reset` with `{}` must return HTTP 200 (HF Space health check).

## Run the server locally

```bash
python -m uvicorn ticket_triage_env.server.app:app --host 0.0.0.0 --port 8000
# or
server   # if the console_scripts entry is on PATH
```

## Baseline inference (`inference.py`)

Uses the **OpenAI** Python client (`API_BASE_URL`, `MODEL_NAME`, `OPENAI_API_KEY`) and a **WebSocket** session at `/ws` (HTTP `/step` is stateless in OpenEnv; WS keeps episode state).

**Environment variables**

| Variable | Purpose |
|----------|---------|
| `ENV_BASE_URL` | HTTP base of the running env, e.g. `http://127.0.0.1:8000` or your Space URL |
| `API_BASE_URL` | LLM API base, e.g. `https://api.openai.com/v1` |
| `MODEL_NAME` | Model id, e.g. `CognitionEnv` |
| `OPENAI_API_KEY` | API key (if unset, a deterministic keyword baseline runs for smoke tests) |
| `HF_TOKEN` | Hugging Face token (Spaces / Hub; read in script per hackathon spec) |

```bash
set ENV_BASE_URL=http://127.0.0.1:8000
set OPENAI_API_KEY=sk-...
python inference.py
```

Logs use exactly: `[START]`, `[STEP] step=... action="..." reward=... done=... error=...`, `[END] task=... score=... success=...`.

Final score = `sum(step rewards) / MAX_TOTAL_REWARD` clamped to `[0,1]` (MAX is task-specific inside `inference.py`).

## OpenEnv validate

Install the OpenEnv CLI (see [OpenEnv docs](https://meta-pytorch.org/OpenEnv/cli.html)), then:

```bash
openenv validate --verbose
```

## Hugging Face Space

1. Create a **Docker** Space.
2. Push this repository; tag the Space with **openenv** in the topic/tags UI.
3. Set secrets if needed; default port **8000** matches `openenv.yaml`.

## Deliverables checklist (hackathon)

| File | Purpose |
|------|---------|
| `openenv.yaml` | Env metadata for OpenEnv |
| `ticket_triage_env/models.py` | `TriageAction`, `TriageObservation`, `Reward`, `TicketView` |
| `ticket_triage_env/server/app.py` | FastAPI app (`create_app`) |
| `app.py` | Root re-export required by prompt |
| `Dockerfile` | Container for Space / local |
| `inference.py` | Baseline LLM + logging |
| `README.md` | This file |
| `ticket_triage_env/grader_*.py` | Deterministic graders |

## Baseline results (sample)

Local run with **keyword heuristic** (no `OPENAI_API_KEY`), server at `http://127.0.0.1:8000`:

| Task | Final score | success |
|------|-------------|---------|
| easy | 0.9500 | True |
| medium | 0.9737 | True |
| hard | 0.9833 | True |

With a real LLM, scores depend on `MODEL_NAME` and prompts; re-run `python inference.py` and paste your table here for submission.

## Limitations

- Ticket text and gold labels are **fixed fixtures** (deterministic, reproducible).
- Session state for multi-step episodes requires **WebSocket** (`/ws`), not stateless HTTP `POST /step`.

## License

BSD-3-Clause-style (match Meta OpenEnv ecosystem) unless you replace with your own.
