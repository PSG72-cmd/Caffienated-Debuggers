# 🏗️ Cognition Env — Architecture & System Design

## High-Level Overview

```
┌─────────────────────────────────────────────────────┐
│                    Agent (AI/LLM)                   │
│              (e.g., inference.py)                   │
└────────────────────┬────────────────────────────────┘
                     │ HTTP POST /step
                     │ WebSocket /ws
                     ▼
        ┌────────────────────────────┐
        │  FastAPI Server            │
        │  (ticket_triage_env/       │
        │   server/app.py)           │
        │                            │
        │  ├─ POST /reset            │
        │  ├─ POST /step             │
        │  └─ WS /ws                 │
        └────────────┬───────────────┘
                     │
                     ▼
        ┌───────────────────────────┐
        │  TriageEnvironment         │
        │  (server/                  │
        │   triage_environment.py)   │
        │                            │
        │  ├─ Current episode state  │
        │  ├─ Ticket simulation      │
        │  ├─ Action validation      │
        │  └─ Reward calculation     │
        └────────────┬────────────────┘
                     │
        ┌────────────┴──────────────┐
        ▼                           ▼
    ┌─────────────┐        ┌──────────────┐
    │   Graders   │        │   Pydantic   │
    │             │        │   Models     │
    │ • Easy      │        │              │
    │ • Medium    │        │ • Action     │
    │ • Hard      │        │ • Observation│
    │             │        │ • Reward     │
    └─────────────┘        └──────────────┘
```

---

## Component Breakdown

### 1. **Server Layer** (`ticket_triage_env/server/app.py`)

**Responsibility:** Handle HTTP requests and WebSocket connections

**Endpoints:**
- `POST /reset` — Initialize new episode
- `POST /step` — Execute single action (stateless)
- `WS /ws` — WebSocket for persistent episode state
- `GET /state` — Query current environment state

**Key Functions:**
- Request validation (Pydantic)
- Episode routing (manages multiple concurrent episodes)
- Response serialization
- Error handling and logging

**Technology:** FastAPI, Pydantic v2

---

### 2. **Environment Core** (`ticket_triage_env/server/triage_environment.py`)

**Responsibility:** Implement OpenEnv interface and manage RL loop

**Main Class:** `TriageEnvironment`

**Key Methods:**
- `reset(seed: int | None) → TriageObservation`
  - Initialize episode with random tickets
  - Return initial observation
  
- `step(action: TriageAction) → tuple[TriageObservation, float, bool, dict]`
  - Apply action to current state
  - Calculate reward
  - Update episode status
  - Return (obs, reward, done, metadata)

- `_validate_action() → bool`
  - Check ticket_id exists
  - Verify enum values
  - Validate command semantics

- `_calculate_reward() → float`
  - Partial credit for correct fields
  - Penalties for invalid actions
  - Terminal grader score on submit

**State Management:**
- Current tickets and their assigned values
- Reward accumulation per ticket
- Episode completion status
- Grader scores (after submit)

---

### 3. **Graders** (`ticket_triage_env/grader_easy/medium/hard.py`)

**Responsibility:** Deterministic evaluation of agent performance

**Three Implementations:**

#### **Easy Grader** (`grader_easy.py`)
```
One ticket: Category (0.5) + Priority (0.5)
Score = (category_correct × 0.5) + (priority_correct × 0.5)
Range: [0.0, 1.0]
```

#### **Medium Grader** (`grader_medium.py`)
```
Three tickets: Category (0.4) + Priority (0.35) + Team (0.25) per ticket
Score = avg([ticket1_score, ticket2_score, ticket3_score])
Range: [0.0, 1.0]
```

#### **Hard Grader** (`grader_hard.py`)
```
Five tickets: Field accuracy (0.65) + Constraint satisfaction (0.35)

Field Accuracy (per ticket):
  - Category: 0.2
  - Priority: 0.2
  - Team: 0.25

Global Constraints:
  - Rule: P1 → assigned to 'oncall'
  - Rule: billing category → 'billing_ops' + 'finance_review' tags
  - Rule: VIP body → 'vip' tag

Final Score = (field_acc × 0.65) + (constraints_satisfied × 0.35)
Range: [0.0, 1.0]
```

**Contract:**
```python
def grade(predicted: dict, gold: dict) -> float:
    """
    Args:
        predicted: Agent's submitted triage (category, priority, team, tags, etc.)
        gold: Correct answer (from environment fixture)
    
    Returns:
        score: float in [0.0, 1.0]
    """
```

All graders are **deterministic** (same input → same output) and **comparable** (scores across tasks use the same 0–1 scale).

---

### 4. **Data Models** (`ticket_triage_env/models.py`)

Pydantic models ensure type safety and API documentation.

**Key Models:**

1. **TriageAction** — Agent input
   - `command`: "set_labels" | "submit"
   - `ticket_id`, `category`, `priority`, `assign_team`, `tags`

2. **TriageObservation** — Agent output
   - Task metadata (name, key, instruction)
   - Current tickets
   - Reward and done status
   - Allowed enums (what values agent can use)

3. **Reward** — Structured breakdown
   - `step_total`: Scalar reward for step
   - `partial_credit`: Correct field bonuses
   - `penalty`: Invalid action penalties
   - `terminal_grader_component`: Grader score contribution

4. **TicketView** — Ticket representation
   - `id`: Unique identifier
   - `title`: Short summary
   - `body`: Full description

---

## Data Flow

### Episode Initialization (`reset`)

```
Agent calls: POST /reset

1. Server receives reset request
2. TriageEnvironment.reset() called
3. Load task (easy/medium/hard)
4. Sample random tickets from fixture
5. Initialize empty assignments
6. Return TriageObservation (tickets, instruction, etc.)

Agent receives: {
  task_key: "easy",
  tickets: [{id: "TICK-001", title: "...", body: "..."}],
  instruction: "Triage this ticket...",
  reward: 0.0,
  done: false
}
```

### Action Execution (`step`)

```
Agent calls: POST /step with TriageAction

1. Server receives action
2. TriageEnvironment.step(action) called
   a. Validate action
      - Ticket ID exists?
      - Enum values valid?
      - Command semantics OK?
   
   b. Apply action
      - Update internal ticket state
      - Mark fields as set by agent
   
   c. Calculate reward
      - Partial credit: +0.X if field becomes correct
      - Penalty: -0.Y if action invalid
      - (No terminal reward yet)
   
   d. Check episode status
      - If command == "submit":
        * Get gold labels
        * Call appropriate grader
        * Compute terminal reward
        * Set done=True
      - Else done=False

3. Return TriageObservation with updated state
   - Feedback: "✓ Category set correctly" or "✗ Invalid enum"
   - Reward: step reward
   - Done: True if submitted, False otherwise
   - Metadata: grader_score (if done), allowed_values, etc.

Agent receives: {
  feedback: "✓ Category set correctly",
  reward: 0.25,
  done: false,
  metadata: {...}
}
```

### WebSocket Persistent Sessions

```
Agent initiates: WS /ws

1. Server creates new WebSocket connection
2. Episode state persists across /ws messages
3. Each message = one action
4. State maintained server-side (not in GET parameters)
5. Connection closes = episode discarded
```

---

## Reward Shaping Strategy

### Motivation
Sparse rewards (only at episode end) make RL training slow. We use **shaped rewards** to provide guidance during learning.

### Design

**Partial Credit Phase** (`set_labels` command)
- Agent gets +0.1 to +0.5 reward **per field** when correct
- Only on first correct assignment of that field (no double-dipping)
- Penalties for invalid actions: -0.1 to -0.5

Example:
```
Step 1: set_labels ticket_id=TICK-001 category=technical priority=P3
  → category is correct: +0.25
  → priority is correct: +0.25
  → total step reward: +0.5

Step 2: set_labels ticket_id=TICK-001 category=billing priority=P3
  → category changes to correct: 0 (already had credit)
  → priority already correct: 0
  → total step reward: 0.0
```

**Terminal Reward** (`submit` command)
- Grader determines final score (0.0–1.0)
- Terminal reward = 0.5 + (0.5 × grader_score)
  - Minimum: 0.5 (for trying)
  - Maximum: 1.0 (perfect grader score)
- Scaled by task difficulty (internally)

**Post-Submission Penalty**
- Any `step()` after episode is done: -0.05 per step
- Prevents infinite episodes

---

## State Management

### Episode State Variables
```python
class EpisodeState:
    task_key: "easy" | "medium" | "hard"
    tickets: List[Ticket]  # Visible to agent
    gold_labels: dict      # Hidden from agent (used for grading)
    agent_assignments: dict  # What agent has set so far
    cumulative_reward: float
    done: bool
    grader_score: float | None
    metadata: dict
```

### Ticket State Transitions
```
┌──────────────┐
│  Unassigned  │  (gold_labels exist, agent hasn't set)
└──────┬───────┘
       │ agent sets field correctly
       ▼
┌──────────────────────────────┐
│  Partially Assigned (Correct) │  (agent got some fields right)
└──────┬───────────────────────┘
       │ agent sets remaining fields correctly
       ▼
┌──────────────┐
│   Assigned   │  (all required fields correct, ready for submit)
└──────────────┘
```

---

## Modular Architecture Benefits

1. **Separation of Concerns**
   - Server handles I/O
   - Environment handles RL logic
   - Graders handle evaluation
   - Models handle contracts

2. **Extensibility**
   - New tasks: add `grader_advanced.py` + `task_data.json`
   - New agents: implement any client that calls REST API
   - Custom reward shaping: modify `_calculate_reward()` logic
   - Alternative transport: wrap TriageEnvironment in different server

3. **Testability**
   - Graders: pure functions (input → output)
   - Environment: no dependencies on HTTP (mockable)
   - Server: separates I/O from logic

4. **Reproducibility**
   - Deterministic graders and fixed ticket fixtures
   - WebSocket state + HTTP stateless options
   - Same seed → same episode

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Server | FastAPI | Modern, type-hinted, async-ready |
| Models | Pydantic v2 | Validation, serialization, documentation |
| RL Interface | OpenEnv Core | Standard environment protocol |
| Async | asyncio | Handle concurrent WebSocket connections |
| Deployment | Docker | Reproducibility, Spaces compatibility |
| LLM Baseline | OpenAI | Example inference client |

---

## Deployment Architecture

### Local Development
```
Your Machine
├─ terminal 1: python -m uvicorn ticket_triage_env.server.app:app --port 8000
└─ terminal 2: python inference.py
```

### Docker (Local or Cloud)
```
Docker Container
├─ Python 3.11
├─ FastAPI server (port 8000)
└─ Pre-installed dependencies (requirements from pyproject.toml)
```

### Hugging Face Spaces
```
Spaces Instance
├─ Dockerfile pulled & built
├─ Server runs automatically
├─ Persistent storage (if configured)
└─ Public URL for accessibility
```

---

## Performance Considerations

- **Concurrency:** WebSocket + FastAPI handle multiple simultaneous episodes
- **Memory:** Episode state grows with ticket count; garbage-collected after done
- **Latency:** LLM inference (not environment) is bottleneck in training loops
- **Scalability:** No database required; stateless HTTP or per-connection state via WS

---

## Security Notes

- **Input Validation:** All Pydantic models validate input types/ranges
- **No Auth:** Current version assumes trusted agents (add if deploying publicly)
- **CORS:** Configure if frontend needs to call from different domain
- **Rate Limiting:** Add if needed (FastAPI middleware available)

---

## Future Extensions

1. **Multi-Agent Support:** Queuing for concurrent agent training
2. **Curriculum Learning:** Progressive task difficulty
3. **Custom Reward Functions:** User-provided reward modules
4. **Observability:** Metrics, logging, tracing integration
5. **Persistence:** SQL database for collecting training data
6. **Benchmarking:** Performance tracking across agent versions

---

## References

- [OpenEnv Documentation](https://meta-pytorch.org/OpenEnv/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Reward Shaping in RL](https://www.baeldung.com/cs/reward-shaping)
