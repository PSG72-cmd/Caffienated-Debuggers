"""Test that API credentials work independently of the WebSocket server."""

import os
import sys

def test_api_credentials():
    """Test if API_KEY and API_BASE_URL are properly configured."""
    api_key = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    api_base_url = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
    
    print(f"[TEST] API_KEY present: {bool(api_key)}", file=sys.stderr)
    print(f"[TEST] API_BASE_URL: {api_base_url}", file=sys.stderr)
    
    if not api_key:
        print("[TEST] No API key found - would run in heuristic mode")
        return False
    
    print("[TEST] API credentials found - attempting to create OpenAI client...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=api_base_url)
        print("[TEST] OpenAI client created successfully")
        print("[TEST] Client is ready to make API calls")
        return True
    except Exception as e:
        print(f"[TEST] Failed to create OpenAI client: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = test_api_credentials()
    sys.exit(0 if success else 1)
