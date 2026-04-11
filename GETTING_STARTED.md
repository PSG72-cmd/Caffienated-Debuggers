# 🚀 Getting Started with Cognition Env

A step-by-step guide to set up, run, and train agents on the IT ticket triage environment.

---

## Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/))
- **OpenAI API key** (optional; for LLM baseline)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/PSG72-cmd/Cognition-Env.git
cd Cognition-Env
```

### 2. Create a Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Windows (cmd):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -e .
```

This installs:
- `openenv-core` (RL environment interface)
- `fastapi` (web server)
- `pydantic` (data validation)
- `uvicorn` (ASGI server)
- `openai` (LLM client)
- All other required packages from `pyproject.toml`

✅ **Verify installation:**
```bash
python -c "import ticket_triage_env; print('✓ Installation successful')"
```

---

## Running the Environment Server

### Option 1: Using Uvicorn (Recommended)

```bash
python -m uvicorn ticket_triage_env.server.app:app --host 0.0.0.0 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

The server is now ready at `http://localhost:8000`

### Option 2: Using the Console Script

If installed via `pip install -e .`, the entry point may work:
```bash
server
```

### Option 3: Programmatically (Python)

```python
from ticket_triage_env.server.app import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Testing the Server

### Health Check

```bash
curl http://localhost:8000/docs
```

This opens the **interactive API documentation** (Swagger UI). You can test endpoints directly!

### Manual API Test

**Reset an episode:**
```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected response:**
```json
{
  "task_key": "easy",
  "task_name": "Easy Triage",
  "instruction": "Triage the following ticket...",
  "tickets": [
    {
      "id": "TICK-001",
      "title": "Login not working",
      "body": "Cannot access my account..."
    }
  ],
  "reward": 0.0,
  "done": false,
  "metadata": {...}
}
```

---

## Running Your First Agent

### Quick Start: Keyword Baseline (No API Key)

The environment includes a heuristic baseline that works without OpenAI:

```bash
# Terminal 1: Start the server
python -m uvicorn ticket_triage_env.server.app:app --port 8000

# Terminal 2: Run the baseline agent
python inference.py
```

**Expected output:**
```
[START] task=easy
[STEP] step=1 action="set_labels ticket_id=TICK-001 category=technical priority=P3" reward=0.25 done=False
[STEP] step=2 action="submit" reward=0.47 done=True
[END] task=easy score=0.72 success=true
```

### Advanced: Using OpenAI API

#### Step 1: Get an API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to **API keys** → **Create new secret key**
4. Copy your key (you'll only see it once!)

#### Step 2: Set Environment Variables

**On macOS/Linux:**
```bash
export OPENAI_API_KEY=sk-your-key-here
export ENV_BASE_URL=http://127.0.0.1:8000
export MODEL_NAME=gpt-4  # or gpt-3.5-turbo
```

**On Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-your-key-here"
$env:ENV_BASE_URL="http://127.0.0.1:8000"
$env:MODEL_NAME="gpt-4"
```

#### Step 3: Run the Agent

```bash
# Terminal 1: Start the server
python -m uvicorn ticket_triage_env.server.app:app --port 8000

# Terminal 2: Run the LLM agent
python inference.py
```

Watch the LLM generate decisions in real-time!

---

## Understanding the Output

### Log Format

Each run produces logs like:
```
[START] task=easy
[STEP] step=1 action="set_labels ticket_id=TICK-001 category=technical priority=P3" reward=0.25 done=False
[STEP] step=2 action="set_labels ticket_id=TICK-001 category=technical priority=P3 assign_team=tier1" reward=0.5 done=False
[STEP] step=3 action="submit" reward=0.47 done=True
[END] task=easy score=0.72 success=true
```

**Fields:**
- `[START]` — Episode initialized
- `[STEP]` — Action taken
  - `step=N` — Step number
  - `action="..."` — Agent's command
  - `reward=X` — Reward for this step
  - `done=True/False` — Episode finished?
- `[END]` — Episode complete
  - `score=X` — Final grader score (0.0–1.0)
  - `success=true/false` — Agent triaged correctly?

### Interpreting Rewards

| Reward | Meaning |
|--------|---------|
| 0.0 | No progress this step |
| 0.25–0.5 | Partial correct (one field correct) |
| 0.5–0.75 | Multiple correct fields |
| 0.7–1.0 | Nearing perfect (terminal reward) |

---

## Choosing Your Task Difficulty

The environment has three tasks. Run them with environment variable:

```bash
# Easy task (1 ticket, 2 fields to triage)
export ENV_TASK=easy
python inference.py

# Medium task (3 tickets, 3 fields each)
export ENV_TASK=medium
python inference.py

# Hard task (5 tickets, + business logic constraints)
export ENV_TASK=hard
python inference.py
```

Or, modify `inference.py` to specify:
```python
response = client.post(f"{env_base_url}/reset", json={"task_key": "hard"})
```

---

## Docker Setup (Alternative)

If you prefer containerization:

### Build the Image

```bash
docker build -t cognition-env:latest .
```

### Run the Container

```bash
docker run --rm -p 8000:8000 cognition-env:latest
```

Server will be accessible at `http://localhost:8000`

### Run with Environment Variables

```bash
docker run --rm \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key \
  cognition-env:latest
```

---

## Creating Your Own Agent

You don't have to use the provided `inference.py`. Write your own!

### Minimal Agent Example

```python
import requests
import json

# Configuration
ENV_BASE_URL = "http://127.0.0.1:8000"

# 1. Reset environment
response = requests.post(f"{ENV_BASE_URL}/reset", json={})
obs = response.json()

print(f"Task: {obs['task_key']}")
print(f"Instruction: {obs['instruction']}")
print(f"Tickets: {obs['tickets']}")

# 2. Take an action
action = {
    "command": "set_labels",
    "ticket_id": obs['tickets'][0]['id'],
    "category": "technical",
    "priority": "P3"
}

response = requests.post(f"{ENV_BASE_URL}/step", json=action)
obs = response.json()

print(f"Feedback: {obs['feedback']}")
print(f"Reward: {obs['reward']}")

# 3. Submit when done
action = {"command": "submit"}
response = requests.post(f"{ENV_BASE_URL}/step", json=action)
obs = response.json()

print(f"Final Score: {obs['metadata']['grader_score']}")
```

### Using WebSocket for Persistent Sessions

WebSocket keeps episode state server-side (better for stateful agents):

```python
import asyncio
import websockets
import json

async def run_ws_agent():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as websocket:
        # Reset (implicit in WS connection)
        await websocket.send(json.dumps({"command": "system", "action": "reset"}))
        obs = json.loads(await websocket.recv())
        
        # Take action
        action = {
            "command": "set_labels",
            "ticket_id": obs['tickets'][0]['id'],
            "category": "technical",
            "priority": "P3"
        }
        await websocket.send(json.dumps(action))
        obs = json.loads(await websocket.recv())
        
        print(f"Reward: {obs['reward']}")

asyncio.run(run_ws_agent())
```

---

## Troubleshooting

### Issue: "Connection refused" when running agent

**Cause:** Server not running

**Solution:**
```bash
# Terminal 1: Ensure server is running
python -m uvicorn ticket_triage_env.server.app:app --port 8000

# Terminal 2: Confirm connection
curl http://localhost:8000/docs
```

### Issue: "ModuleNotFoundError: No module named 'openenv'"

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install -e .
```

### Issue: "OpenAI API key not valid"

**Cause:** Invalid or missing API key

**Solution:**
```bash
echo $OPENAI_API_KEY  # Verify key is set
# Generate new key at https://platform.openai.com/account/api-keys
```

### Issue: "Port 8000 already in use"

**Cause:** Another process using port 8000

**Solution:**
```bash
# Use a different port
python -m uvicorn ticket_triage_env.server.app:app --port 8001

# Or find and kill the process
lsof -ti:8000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :8000   # Windows
```

### Issue: "ValidationError: 3 validation errors"

**Cause:** Malformed action JSON

**Solution:** Verify your action format matches Pydantic models:
```python
# ✓ Correct
{"command": "set_labels", "ticket_id": "TICK-001", "category": "technical", "priority": "P3"}

# ✗ Wrong
{"command": "set_labels"}  # Missing required fields
```

---

## Next Steps

- **Read the API Reference:** See [main README](README.md)  
- **Understand Architecture:** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Train an RL Agent:** Use OpenAI Gym or Ray RLlib integrations
- **Contribute:** Send a pull request with improvements!

---

## Getting Help

- **Documentation:** [README.md](README.md) | [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Docs:** `http://localhost:8000/docs` (Swagger UI)
- **Issues:** [GitHub Issues](https://github.com/PSG72-cmd/Cognition-Env/issues)
- **Discussions:** [GitHub Discussions](https://github.com/PSG72-cmd/Cognition-Env/discussions)

Happy training! 🎓
