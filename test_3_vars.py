import requests
import json
import os
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_3_variations():
    # 1. Create a dummy CSV
    csv_content = "username,post_content\ntest_user_1,Exploring AI agents today!\n"
    csv_path = "test_3_vars.csv"
    with open(csv_path, "w") as f:
        f.write(csv_content)
    
    # 2. Upload
    print("Uploading file...")
    with open(csv_path, "rb") as f:
        r = requests.post(f"{BASE_URL}/upload", files={"file": f})
    
    if r.status_code != 200:
        print(f"Upload failed: {r.text}")
        return

    # 3. Generate (using AI OFF to see if we get 3 manual templates)
    print("Triggering generation (AI OFF fallback)...")
    payload = {
        "message_template": "Hi {post_content}! Check out my tool.",
        "use_ai": False # Should still generate 3 identical manual templates now
    }
    # Wait, the current logic only generates 3 if use_ai is ON?
    # No, I updated worker.py to do: message = json.dumps([message_text] * 3)
    
    # Actually, /start and /generate need use_ai to be somewhat involved for the worker to do its thing in AI-like way?
    # Let's check worker.py's prompt-based gen.
    
    # /generate requires use_ai: True
    payload["use_ai"] = True
    payload["openrouter_api_key"] = " " # Space to bypass empty check but fail real call
    
    r = requests.post(f"{BASE_URL}/generate", json=payload)
    print(f"Generate response: {r.text}")
    
    import time
    print("Waiting 10s for generation...")
    time.sleep(10)
    
    # 4. Check approvals
    print("Checking approvals...")
    r = requests.get(f"{BASE_URL}/api/approvals")
    approvals = r.json().get("approvals", [])
    
    if not approvals:
        print("No approvals found!")
    else:
        for app in approvals:
            msg = app["data"].get("generated_message", "")
            try:
                variations = json.loads(msg)
                print(f"Found {len(variations)} variations for @{app['data']['username']}")
                if len(variations) == 3:
                    print("SUCCESS: 3 variations generated.")
                else:
                    print(f"FAILURE: Expected 3, got {len(variations)}")
            except:
                print(f"FAILURE: Message is not JSON: {msg}")

if __name__ == "__main__":
    test_3_variations()
