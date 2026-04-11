# API Reference - Cognition Env

Complete API documentation for the Cognition Env ticket triage environment.

## Base URL

```
http://localhost:8000
```

For interactive testing, visit: **http://localhost:8000/docs** (Swagger UI)

---

## Endpoints

### 1. Health Check

**GET** `/`

Returns API information and links.

**Response (200 OK):**
```json
{
  "message": "🧠 Cognition Env - Intelligent Ticket Triage with RL",
  "docs": "/docs",
  "api": {
    "reset": "POST /reset",
    "step": "POST /step",
    "state": "GET /state",
    "websocket": "WS /ws"
  },
  "learn_more": "https://github.com/PSG72-cmd/Cognition-Env"
}
```

---

### 2. Initialize Episode

**POST** `/reset`

Start a new environment episode.

**Request Body:**
```json
{
  "task": "easy"  // Optional: "easy", "medium", or "hard" (default: "easy")
}
```

**Response (200 OK):**
```json
{
  "task_key": "easy",
  "task_name": "Easy Triage",
  "instruction": "Triage one support ticket by assigning the correct category and priority.",
  "tickets": [
    {
      "id": "TICK-001",
      "title": "Login not working",
      "body": "Cannot access my account. Tried resetting password but didn't work."
    }
  ],
  "feedback": "Episode started. Use set_labels per ticket, then submit.",
  "reward": 0.0,
  "done": false,
  "metadata": {
    "allowed_categories": ["billing", "technical", "account_access", "general"],
    "allowed_priorities": ["P1", "P2", "P3", "P4"],
    "allowed_teams": ["tier1", "tier2", "oncall", "billing_ops"],
    "step_limit": 12,
    "grader_score": null,
    "reward_breakdown": null
  }
}
```

---

### 3. Execute Action

**POST** `/step`

Send an action to update ticket triage or submit for grading.

**Request Body:**

**Option A: Set Labels**
```json
{
  "command": "set_labels",
  "ticket_id": "TICK-001",
  "category": "technical",
  "priority": "P3",
  "assign_team": "tier1",
  "tags": ["urgent", "billing"]
}
```

All fields except `command` and `ticket_id` are optional. Omitted fields are not modified.

**Option B: Submit Episode**
```json
{
  "command": "submit"
}
```

**Response (200 OK):**
```json
{
  "task_key": "easy",
  "tickets": [...],
  "feedback": "✓ Category set correctly",
  "reward": 0.25,
  "done": false,
  "metadata": {
    "allowed_categories": [...],
    "allowed_priorities": [...],
    "allowed_teams": [...],
    "grader_score": null,  // null until submit; then score (0.0-1.0)
    "reward_breakdown": {
      "step_total": 0.25,
      "partial_credit": 0.25,
      "penalty": 0.0,
      "terminal_grader_component": 0.0
    }
  }
}
```

After `submit`:
```json
{
  "done": true,
  "reward": 0.72,  // Terminal reward
  "metadata": {
    "grader_score": 0.72,  // Now populated
    "reward_breakdown": {
      "step_total": 0.72,
      "partial_credit": 0.0,
      "penalty": 0.0,
      "terminal_grader_component": 0.72
    }
  }
}
```

---

### 4. Query State

**GET** `/state`

Get the current episode state without taking an action.

**Response (200 OK):**
Same structure as `/step` response, with no reward change.

---

### 5. WebSocket Persistent Sessions

**WS** `/ws`

Maintain episode state across multiple actions. Recommended for agents that maintain conversation context.

**Protocol:**
1. Connect: `ws://localhost:8000/ws`
2. Send action as JSON: `{"command": "set_labels", "ticket_id": "TICK-001", "category": "technical"}`
3. Receive observation JSON
4. Repeat or close

**Example (Python):**
```python
import asyncio
import websockets
import json

async def run():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        # Send action
        action = {
            "command": "set_labels",
            "ticket_id": "TICK-001",
            "category": "technical"
        }
        await ws.send(json.dumps(action))
        
        # Receive observation
        obs_json = await ws.recv()
        obs = json.loads(obs_json)
        print(obs)

asyncio.run(run())
```

---

## Data Models

### TriageAction

Agent's action in the environment.

```json
{
  "command": "set_labels" | "submit",
  "ticket_id": "string (optional for submit)",
  "category": "billing | technical | account_access | general (optional)",
  "priority": "P1 | P2 | P3 | P4 (optional)",
  "assign_team": "tier1 | tier2 | oncall | billing_ops (optional)",
  "tags": ["string"] (optional list)
}
```

### TriageObservation

Environment's response to agent.

```json
{
  "task_key": "easy | medium | hard",
  "task_name": "string (human-readable)",
  "instruction": "string (what to do)",
  "tickets": [
    {
      "id": "string",
      "title": "string",
      "body": "string"
    }
  ],
  "feedback": "string (result of last action)",
  "reward": "number (scalar reward)",
  "done": "boolean (episode finished?)",
  "metadata": {
    "allowed_categories": ["string"],
    "allowed_priorities": ["string"],
    "allowed_teams": ["string"],
    "step_limit": "number",
    "grader_score": "number | null (only set after submit)",
    "reward_breakdown": {
      "step_total": "number",
      "partial_credit": "number",
      "penalty": "number",
      "terminal_grader_component": "number"
    }
  }
}
```

---

## Error Responses

### 400 Bad Request
Malformed JSON or invalid action format.

```json
{
  "detail": "Validation error: Invalid category 'xyz'"
}
```

### 404 Not Found
Resource not found (e.g., unknown ticket ID).

### 500 Internal Server Error
Unexpected server error. Check server logs.

---

## Reward Structure

Agents earn rewards through:

1. **Partial Credit** (set_labels, first-time-only)
   - Category correct: +0.18
   - Priority correct: +0.18
   - Team correct: +0.14
   - Tags correct: +0.20

2. **Terminal Reward** (submit)
   - Base: 0.5 + (0.5 × grader_score)
   - Range: [0.5, 1.0]
   - grader_score is deterministic based on task

3. **Penalties**
   - Invalid enum: -0.05
   - Unknown ticket: -0.05
   - Post-submit step: -0.02

---

## Rate Limiting

No built-in rate limiting. For public deployments, add FastAPI middleware or reverse proxy rules.

---

## CORS

By default, CORS is not enabled. For frontend integrations, enable:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Example Workflows

### Single HTTP Episode

```bash
# Reset
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{}'

# Step 1
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"command":"set_labels","ticket_id":"TICK-001","category":"technical","priority":"P3"}'

# Step 2
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"command":"submit"}'
```

### Stateful WebSocket Episode

Use `examples.py` or your own client (see examples in [GETTING_STARTED.md](GETTING_STARTED.md)).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused" | Ensure server is running: `python -m uvicorn ticket_triage_env.server.app:app --port 8000` |
| "Validation error" | Check action JSON format matches TriageAction schema |
| "Unknown ticket ID" | Use ticket IDs from observation.tickets list |
| "Invalid category/priority" | Check metadata.allowed_* lists for valid values |

See [GETTING_STARTED.md](GETTING_STARTED.md#troubleshooting) for more help.
