"""Test script to run server and inference locally."""

import subprocess
import sys
import time
import requests
from threading import Thread

def check_server_health(url="http://127.0.0.1:8000/health", max_retries=30):
    """Check if server is healthy."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"[OK] Server is healthy (attempt {attempt + 1})")
                return True
        except requests.exceptions.RequestException:
            print(f"Waiting for server... (attempt {attempt + 1}/{max_retries})")
            time.sleep(1)
    return False

def start_server():
    """Start the server in a subprocess."""
    print("Starting server...")
    cmd = [sys.executable, "-m", "uvicorn", "ticket_triage_env.server.app:app", "--host", "127.0.0.1", "--port", "8000"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process

def test_inference():
    """Test inference.py."""
    print("\n" + "="*60)
    print("Running inference.py test...")
    print("="*60)
    
    cmd = [sys.executable, "inference.py"]
    result = subprocess.run(cmd, cwd="d:\\ticket_triage_env", capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("\nSTDERR:")
        print(result.stderr)
    
    print(f"\nExit code: {result.returncode}")
    return result.returncode == 0

if __name__ == "__main__":
    # Start server
    server_process = start_server()
    time.sleep(2)  # Give server time to start
    
    try:
        # Check server health
        if not check_server_health():
            print("[FAIL] Server failed to start/become healthy")
            sys.exit(1)
        
        # Run inference test
        success = test_inference()
        
        if success:
            print("\n[PASS] Test passed!")
        else:
            print("\n[FAIL] Test failed - see errors above")
            sys.exit(1)
            
    finally:
        # Cleanup
        print("\nShutting down server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
