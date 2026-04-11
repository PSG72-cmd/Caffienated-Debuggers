---
title: Cognition Env
emoji: 🧠
colorFrom: indigo
colorTo: purple
sdk: docker
python_version: "3.10"
app_port: 7860
suggested_hardware: "cpu-basic"
short_description: AI learns IT ticket triage with RL
tags:
  - reinforcement-learning
  - openenv
  - ai-agents
  - simulation
  - llm
pinned: true
---

# 🧠 Cognition Env

**Cognition Env** is a production-grade OpenEnv environment for training AI agents using reinforcement learning to perform intelligent IT helpdesk ticket triage.

> **The Problem:** IT support teams waste hours manually triaging support tickets—categorizing issues, setting priorities, assigning teams, and applying labels. This is repetitive, error-prone, and doesn't scale.  
> 
> **Our Solution:** Cognition Env provides a realistic simulation where AI agents learn through reinforcement learning to triage tickets like expert representatives. Agents receive:
> - **Partial rewards** as they make correct decisions
> - **Terminal rewards** after submission based on a deterministic grader
> - **Multi-step feedback** on their actions
>
> **Why This Matters:** This environment enables research into:
> - Reward shaping for complex real-world decision-making
> - Multi-constraint optimization in agent training  
> - Transfer learning from easy → medium → hard tasks
> - Production-ready AI agents for support automation

---

## 🎯 Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd ticket_triage_env
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .

# 2. Run the environment server
python -m uvicorn ticket_triage_env.server.app:app --host 0.0.0.0 --port 8000

# 3. In another terminal, run an example agent
python inference.py
```

**Expected Output:**
```
[START] task=easy
[STEP] step=1 action="set_labels ticket_id=TICK-001 category=technical priority=P3" reward=0.25 done=False
[STEP] step=2 action="submit" reward=0.72 done=True
[END] task=easy score=0.72 success=true
```

---

## 🏗️ Architecture Overview

```
Agent → (REST + WebSocket) → Environment Server → Grader → Score
              ↓                      ↓               ↓
         Request/Step         Episode State      Task-Specific
         (Action)             Management        Evaluation
```

**Core Components:**
- **TriageEnvironment**: Manages episode state, ticket simulation, and reward calculation
- **Graders** (Easy/Medium/Hard): Deterministic scoring based on task difficulty
- **Server** (FastAPI): REST endpoints for reset/step + WebSocket for persistent sessions
- **Client**: Example agent using LLM + reward feedback for decision-making

[See ARCHITECTURE.md for detailed system design →](ARCHITECTURE.md)

---

## 📋 What This Environment Teaches

| Task | Difficulty | Goal | Agent Learns |
|------|----------|------|---------------|
| **Easy** | 🟢 | 1 ticket: correct **category** + **priority** | Basic classification + priority assignment |
| **Medium** | 🟡 | 3 tickets: **category** + **priority** + **team assignment** | Multi-ticket coordination + routing |
| **Hard** | 🔴 | 5 tickets: **category** + **priority** + **team** + **global constraints** | Complex reasoning with business rules (P1→oncall, billing→finance_review+billing_ops, VIP→vip tag) |

✔ **Deterministic Graders**: Scores from 0.0–1.0 enable reproducible evaluation  
✔ **Reward Shaping**: Agents receive partial credit as fields become correct (not sparse rewards)  
✔ **Constraints**: Hard task includes real-world business logic constraints

---

## 🔌 API Reference

### Reset Episode
```bash
POST /reset
Content-Type: application/json

{}

Response:
{
  "task_name": "Easy Triage",
  "task_key": "easy",
  "instruction": "Triage one support ticket correctly...",
  "tickets": [{"id": "TICK-001", "title": "...", "body": "..."}],
  "reward": 0.0,
  "done": false
}
```

### Take Action
```bash
POST /step
Content-Type: application/json

{
  "command": "set_labels",
  "ticket_id": "TICK-001",
  "category": "technical",
  "priority": "P3"
}

Response:
{
  "feedback": "✓ Category set correctly",
  "reward": 0.25,
  "done": false,
  "metadata": {"grader_score": null, ...}
}
```

### WebSocket for Persistent Sessions
```
ws://localhost:8000/ws
```
Maintains episode state across multiple `/step` calls without re-initializing.

---

## 🧪 Features

### ✅ OpenEnv Compliance
- Standard interface: `reset()`, `step(action)`, `state()`
- Typed models (Pydantic v2)
- Clean RL loop with proper done/reset semantics

### ✅ Structured Rewards
Each step returns detailed reward breakdown:
```python
{
  "step_total": 0.72,           # Total reward this step
  "partial_credit": 0.25,        # Correct field credit
  "penalty": 0.0,                # Invalid action penalty
  "terminal_grader_component": 0.47  # Grader score component
}
```

### ✅ Realism
- Real ticket formats (id, title, body)
- Business logic constraints (oncall for P1, routing rules)
- Partial feedback (agents see which fields they got right)

---

## 🚀 Running This Environment  



### Local Server
```bash
python -m uvicorn ticket_triage_env.server.app:app --host 0.0.0.0 --port 8000
# Alternative (if installed via pip install -e .):
server  # Uses console_scripts entry point
```

### Docker Deployment
```bash
docker build -t cognition-env:latest .
docker run --rm -p 8000:8000 cognition-env:latest
```
> Note: `POST /reset` with `{}` must return HTTP 200 for HF Spaces health checks

---

## 📚 Detailed Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design, component descriptions, data flow
- **[GETTING_STARTED.md](GETTING_STARTED.md)** — Detailed setup, troubleshooting, examples
- **[API.md](API.md)** — Complete API reference with curl examples

---

## 🤖 Training an Agent

### Using the LLM Baseline (`inference.py`)

The repository includes an example AI agent powered by OpenAI:

```bash
export ENV_BASE_URL=http://127.0.0.1:8000
export OPENAI_API_KEY=sk-your-key-here
python inference.py
```

**What happens:**
1. Agent resets the environment (`POST /reset`)
2. Reads observation (tickets, constraints, etc.)
3. Uses LLM to decide actions (via WebSocket)
4. Receives reward feedback
5. Re-prompts LLM with feedback for next action
6. Submits when confident all fields are correct
7. Logs final score

**Output Example:**
```
[START] task=easy
[STEP] step=1 action="set_labels ticket_id=TICK-001 category=technical priority=P3" reward=0.25 done=False
[STEP] step=2 action="set_labels ticket_id=TICK-001 category=technical priority=P3 assign_team=tier1" reward=0.5 done=False
[STEP] step=3 action="submit" reward=0.47 done=True
[END] task=easy score=0.72 success=true
```

### Environment Variables for Agents

| Variable | Purpose | Example |
|----------|---------|---------|
| `ENV_BASE_URL` | Location of running environment server | `http://127.0.0.1:8000` |
| `OPENAI_API_KEY` | OpenAI API key (optional; fallback to keyword baseline) | `sk-...` |
| `MODEL_NAME` | Model to use for inference | `gpt-4` |
| `API_BASE_URL` | Custom LLM API endpoint | `https://api.openai.com/v1` |

---

## 🎓 Reward Shaping Details

Understanding how agents earn rewards is critical for training:

### Partial Credit (`set_labels` command)
- **First-time correct field:** Small positive reward (0.1–0.5 per field)
- **Each ticket:** Category, priority, team, and tags award independently
- **Invalid action:** Penalty (negative reward)
  - Unknown ticket ID  
  - Invalid enum value  
  - Missing required field

### Terminal Reward (`submit` command)
- Scaled by **task difficulty** and **grader score**  
- Grader computes 0.0–1.0 based on task requirements (see task tables above)
- Final reward = base + (difficulty_multiplier × grader_score)

### Episode Termination
- Agent must call `submit` to end episode
- Stepping after `submit` yields small negative penalty
- Episode cannot be extended indefinitely

---

## 🔍 Model Reference

### Pydantic Models (Input/Output)

**TriageAction** (Agent → Environment)
```python
{
  "command": "set_labels" | "submit",    # Action type
  "ticket_id": "TICK-001",                # Target ticket
  "category": "technical",                # One of: billing, technical, account_access, general
  "priority": "P3",                       # One of: P1, P2, P3, P4
  "assign_team": "tier1",                 # One of: tier1, tier2, oncall, billing_ops
  "tags": ["urgent", "vip"]               # Custom tags
}
```

**TriageObservation** (Environment → Agent)
```python
{
  "task_name": "Easy Triage",
  "task_key": "easy",
  "instruction": "Triage the following ticket...",
  "tickets": [                            # Current visible tickets
    {
      "id": "TICK-001",
      "title": "Login not working",
      "body": "Cannot access my account"
    }
  ],
  "reward": 0.25,                         # Reward from last action
  "done": false,                          # Episode finished?
  "metadata": {                           # Additional info
    "grader_score": 0.72,                 # Only after submit
    "allowed_categories": [...],
    "allowed_priorities": [...]
  }
}
```

---

## 🏪 Production Deployment

### Hugging Face Spaces
This environment is compatible with [Hugging Face Spaces](https://huggingface.co/spaces):
- Dockerfile provided
- Automatically allocates compute
- Easy sharing and collaboration

### Requirements
- Python ≥ 3.11
- FastAPI, Pydantic, OpenEnv core library
- (Optional) OpenAI API key for LLM baseline

---

## 🧪 Testing & Validation

Run OpenEnv validation (requires OpenEnv CLI):

```bash
# Install OpenEnv tools
pip install openenv

# Validate environment compliance
openenv validate --verbose

# Run baseline inference and check logs
python inference.py
```

### Health Checks
- `/reset` with `{}` returns 200 OK ✓
- Episode state tracked correctly via WebSocket ✓
- Reward shaping follows documented formula ✓
- Graders produce deterministic scores ✓

---

## 🤝 Contributing

Improvements welcome! Potential areas:
- Additional task difficulty levels
- Alternative agent baselines (RL, supervised learning)
- Extended constraint vocabularies  
- Performance optimizations

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📖 Citation

If you use this environment in research, please cite:

```bibtex
@software{cognition_env,
  title={Cognition Env: OpenEnv Environment for IT Support Ticket Triage},
  author={OpenEnv Contributors},
  year={2024},
  url={https://github.com/PSG72-cmd/Cognition-Env}
}
```

---

## 🙋 Support

- **Questions?** Check [GETTING_STARTED.md](GETTING_STARTED.md) or [Discussions](https://github.com/PSG72-cmd/Cognition-Env/discussions)
- **Bug Reports?** [Open an Issue](https://github.com/PSG72-cmd/Cognition-Env/issues)
- **Documentation:** [Full API Reference](API.md) | [Architecture](ARCHITECTURE.md)

---

## 📝 License

BSD 3-Clause License — see [LICENSE](LICENSE) file for details.
