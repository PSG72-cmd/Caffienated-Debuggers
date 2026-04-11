"""
Example usage demonstrations for Cognition Env.

This script shows various ways to interact with the Cognition Env
ticket triage environment, perfect for testing and understanding the API.

Run this script after starting the server:
    python -m uvicorn ticket_triage_env.server.app:app --port 8000

Then in another terminal:
    python examples.py
"""

import json
import requests
from typing import Dict, Any

# Configuration
ENV_BASE_URL = "http://127.0.0.1:8000"


def separator(title: str) -> None:
    """Print a separator with title for readability."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def example_1_basic_easy_task() -> None:
    """
    Example 1: Complete an easy task with minimal actions.
    
    Easy task: Triage 1 ticket by setting category + priority.
    """
    separator("EXAMPLE 1: Basic Easy Task (1 ticket, 2 fields)")
    
    print("✓ Resetting environment for 'easy' task...\n")
    response = requests.post(f"{ENV_BASE_URL}/reset", json={})
    obs = response.json()
    
    print(f"Task: {obs['task_key']}")
    print(f"Task Name: {obs['task_name']}")
    print(f"Instruction: {obs['instruction']}\n")
    
    print("📋 Tickets to triage:")
    for ticket in obs['tickets']:
        print(f"  ID: {ticket['id']}")
        print(f"  Title: {ticket['title']}")
        print(f"  Body: {ticket['body'][:60]}...\n")
    
    print("Allowed values:")
    print(f"  Categories: {', '.join(obs['metadata']['allowed_categories'])}")
    print(f"  Priorities: {', '.join(obs['metadata']['allowed_priorities'])}")
    print(f"  Teams: {', '.join(obs['metadata']['allowed_teams'])}\n")
    
    # Take action 1: Set category
    ticket_id = obs['tickets'][0]['id']
    print(f"► Action 1: Setting category to 'technical' for {ticket_id}...")
    action = {
        "command": "set_labels",
        "ticket_id": ticket_id,
        "category": "technical"
    }
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Feedback: {obs['feedback']}")
    print(f"  Reward: {obs['reward']}\n")
    
    # Take action 2: Set priority
    print(f"► Action 2: Setting priority to 'P3' for {ticket_id}...")
    action = {
        "command": "set_labels",
        "ticket_id": ticket_id,
        "priority": "P3"
    }
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Feedback: {obs['feedback']}")
    print(f"  Reward: {obs['reward']}\n")
    
    # Submit
    print("► Action 3: Submitting triage...")
    action = {"command": "submit"}
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Done: {obs['done']}")
    print(f"  Grader Score: {obs['metadata']['grader_score']}")
    print(f"  Terminal Reward: {obs['reward']}")
    print(f"  Total Episode Reward: ~{obs['reward'] + 0.5}\n")  # 0.5 from partial credits


def example_2_medium_task_multi_ticket() -> None:
    """
    Example 2: Complete a medium task with multiple tickets.
    
    Medium task: Triage 3 tickets by setting category + priority + team.
    """
    separator("EXAMPLE 2: Medium Task (3 tickets, 3 fields each)")
    
    print("✓ Resetting environment for 'medium' task...\n")
    response = requests.post(f"{ENV_BASE_URL}/reset", json={"task": "medium"})
    obs = response.json()
    
    print(f"Task: {obs['task_key']}")
    print(f"Number of tickets: {len(obs['tickets'])}\n")
    
    # Show all tickets
    for i, ticket in enumerate(obs['tickets'], 1):
        print(f"Ticket {i}: {ticket['id']} - {ticket['title']}")
    
    print("\n✓ Triaging tickets...\n")
    
    # Simple heuristic: assign common values
    assignments = [
        {"ticket_id": obs['tickets'][0]['id'], "category": "technical", "priority": "P2", "assign_team": "tier2"},
        {"ticket_id": obs['tickets'][1]['id'], "category": "billing", "priority": "P3", "assign_team": "billing_ops"},
        {"ticket_id": obs['tickets'][2]['id'], "category": "account_access", "priority": "P1", "assign_team": "oncall"},
    ]
    
    cumulative_reward = 0.0
    
    for assignment in assignments:
        ticket_id = assignment['ticket_id']
        print(f"Triaging {ticket_id}...")
        
        # Set all fields in one action
        action = {
            "command": "set_labels",
            **assignment
        }
        response = requests.post(f"{ENV_BASE_URL}/step", json=action)
        obs = response.json()
        
        print(f"  Feedback: {obs['feedback']}")
        print(f"  Step Reward: {obs['reward']}\n")
        cumulative_reward += obs['reward']
    
    # Submit
    print("► Submitting triage...")
    action = {"command": "submit"}
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    
    cumulative_reward += obs['reward']
    
    print(f"  Done: {obs['done']}")
    print(f"  Grader Score: {obs['metadata']['grader_score']}")
    print(f"  Terminal Reward: {obs['reward']}")
    print(f"  Total Cumulative Reward: {cumulative_reward:.3f}\n")


def example_3_error_handling() -> None:
    """
    Example 3: Demonstrate error handling with invalid actions.
    """
    separator("EXAMPLE 3: Error Handling")
    
    print("✓ Resetting environment...\n")
    response = requests.post(f"{ENV_BASE_URL}/reset", json={})
    obs = response.json()
    ticket_id = obs['tickets'][0]['id']
    
    # Error 1: Invalid category
    print("► Attempt 1: Invalid category...")
    action = {
        "command": "set_labels",
        "ticket_id": ticket_id,
        "category": "invalid_category"
    }
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Feedback: {obs['feedback']}")
    print(f"  Reward: {obs['reward']} (negative = penalty)\n")
    
    # Error 2: Invalid priority
    print("► Attempt 2: Invalid priority...")
    action = {
        "command": "set_labels",
        "ticket_id": ticket_id,
        "priority": "P99"
    }
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Feedback: {obs['feedback']}")
    print(f"  Reward: {obs['reward']} (negative = penalty)\n")
    
    # Error 3: Unknown ticket ID
    print("► Attempt 3: Unknown ticket ID...")
    action = {
        "command": "set_labels",
        "ticket_id": "UNKNOWN-999",
        "category": "technical"
    }
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Feedback: {obs['feedback']}")
    print(f"  Reward: {obs['reward']} (negative = penalty)\n")
    
    # Success: Valid action
    print("► Attempt 4: Correct action...")
    action = {
        "command": "set_labels",
        "ticket_id": ticket_id,
        "category": "technical",
        "priority": "P3"
    }
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    print(f"  Feedback: {obs['feedback']}")
    print(f"  Reward: {obs['reward']} (positive = correct)\n")


def example_4_api_health_check() -> None:
    """
    Example 4: Check API and environment health.
    """
    separator("EXAMPLE 4: API Health Check")
    
    # Check root endpoint
    print("► GET /")
    response = requests.get(f"{ENV_BASE_URL}/")
    data = response.json()
    print(f"  Status: {response.status_code}")
    print(f"  Message: {data['message']}\n")
    
    # Check docs endpoint
    print("► GET /docs (Swagger UI)")
    response = requests.get(f"{ENV_BASE_URL}/docs")
    if response.status_code == 200:
        print(f"  Status: {response.status_code} ✓")
        print(f"  Visit http://localhost:8000/docs for interactive testing\n")
    else:
        print(f"  Status: {response.status_code} ✗\n")
    
    # Test reset endpoint
    print("► POST /reset")
    response = requests.post(f"{ENV_BASE_URL}/reset", json={})
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        obs = response.json()
        print(f"  Task: {obs['task_key']}")
        print(f"  Tickets available: {len(obs['tickets'])}")
        print(f"  ✓ Server is healthy\n")
    else:
        print(f"  ✗ Server error\n")


def example_5_reward_accumulation() -> None:
    """
    Example 5: Track reward accumulation throughout an episode.
    
    Demonstrates how partial rewards add up to a final score.
    """
    separator("EXAMPLE 5: Reward Accumulation Throughout Episode")
    
    print("✓ Starting easy task and tracking rewards...\n")
    
    response = requests.post(f"{ENV_BASE_URL}/reset", json={})
    obs = response.json()
    ticket_id = obs['tickets'][0]['id']
    
    total_reward = 0.0
    step_number = 1
    
    print("Step | Action                              | Reward | Cumulative")
    print("-" * 70)
    
    # Step 1: Category correct
    action = {"command": "set_labels", "ticket_id": ticket_id, "category": "technical"}
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    total_reward += obs['reward']
    print(f"  {step_number}  | Set category=technical              | +{obs['reward']:>5.2f} | {total_reward:>10.3f}")
    step_number += 1
    
    # Step 2: Priority correct
    action = {"command": "set_labels", "ticket_id": ticket_id, "priority": "P3"}
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    total_reward += obs['reward']
    print(f"  {step_number}  | Set priority=P3                     | +{obs['reward']:>5.2f} | {total_reward:>10.3f}")
    step_number += 1
    
    # Step 3: Submit for grading
    action = {"command": "submit"}
    response = requests.post(f"{ENV_BASE_URL}/step", json=action)
    obs = response.json()
    total_reward += obs['reward']
    grader_score = obs['metadata']['grader_score']
    
    print(f"  {step_number}  | Submit (grader score={grader_score:.2f})      | +{obs['reward']:>5.2f} | {total_reward:>10.3f}")
    print("-" * 70)
    print(f"\nFinal Grader Score: {grader_score:.3f}")
    print(f"Total Episode Reward: {total_reward:.3f}")
    print(f"Episode Done: {obs['done']}\n")


def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  Cognition Env - Example Usage Demonstrations")
    print("=" * 60)
    print("\nMake sure the server is running:")
    print("  python -m uvicorn ticket_triage_env.server.app:app --port 8000\n")
    
    try:
        # Check server is accessible
        response = requests.get(f"{ENV_BASE_URL}/", timeout=2)
        if response.status_code != 200:
            print("✗ Server not responding. Start it with:")
            print("  python -m uvicorn ticket_triage_env.server.app:app --port 8000\n")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server at {ENV_BASE_URL}. Start it with:")
        print("  python -m uvicorn ticket_triage_env.server.app:app --port 8000\n")
        return
    
    print("✓ Server is running!\n")
    
    try:
        example_1_basic_easy_task()
        example_2_medium_task_multi_ticket()
        example_3_error_handling()
        example_4_api_health_check()
        example_5_reward_accumulation()
        
        separator("All Examples Complete!")
        print("Next steps:")
        print("  - Explore the interactive API: http://localhost:8000/docs")
        print("  - Run the LLM baseline: python inference.py")
        print("  - Read the docs: README.md, ARCHITECTURE.md, GETTING_STARTED.md\n")
        
    except Exception as e:
        print(f"\n✗ Error during examples: {e}\n")
        raise


if __name__ == "__main__":
    main()
