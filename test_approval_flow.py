import requests
import time
import json
import os

BASE_URL = "http://127.0.0.1:5000"

def run_test():
    print("1. Uploading test file...")
    csv_path = "C:/Users/admin/.gemini/antigravity/scratch/XAutomation/test_data.csv"
    with open(csv_path, 'rb') as f:
        files = {'file': f}
        upload_res = requests.post(f"{BASE_URL}/upload", files=files)
        print("Upload:", upload_res.json())

    print("\n2. Generating AI drafts...")
    generate_payload = {
        "message_template": "Hey {post_content}, let's connect!",
        "use_ai": True,
        "openrouter_api_key": "dummy_key", # Will use fallback template due to dummy key
        "openrouter_model": "openai/gpt-4o-mini"
    }
    gen_res = requests.post(f"{BASE_URL}/generate", json=generate_payload)
    print("Generate:", gen_res.json())

    print("\n3. Waiting for worker to generate pending_approval messages (5s)...")
    time.sleep(5)

    print("\n4. Checking approvals API...")
    app_res = requests.get(f"{BASE_URL}/api/approvals")
    approvals = app_res.json().get("approvals", [])
    print(f"Found {len(approvals)} approvals.")
    
    if not approvals:
        print("No approvals found. Test failed. Did the generation worker finish?")
        return

    first_approval = approvals[0]
    idx = first_approval["index"]
    original_msg = first_approval["data"]["generated_message"]
    print(f"Original message: {original_msg}")

    print("\n5. Disapproving and regenerating...")
    disapprove_payload = {
        "index": idx,
        "feedback": "Make it much shorter",
        "api_key": "dummy_key",
        "model": "openai/gpt-4o-mini",
        "fallback_template": "Shorter: Hey {post_content}!"
    }
    dis_res = requests.post(f"{BASE_URL}/api/disapprove", json=disapprove_payload)
    dis_data = dis_res.json()
    print("Disapprove:", dis_data)
    new_msg = dis_data.get("new_message", "")

    print("\n6. Approving the new message...")
    approve_payload = {
        "index": idx,
        "message": new_msg
    }
    app_res2 = requests.post(f"{BASE_URL}/api/approve", json=approve_payload)
    print("Approve:", app_res2.json())

    print("\n7. Starting automation to send approved messages...")
    start_res = requests.post(f"{BASE_URL}/start", json=generate_payload) # Reusing the payload structure
    print("Start sending:", start_res.json())

    print("\n8. Waiting for worker to send the approved message (15s)...")
    time.sleep(15)

    print("\n9. Stopping automation...")
    stop_res = requests.post(f"{BASE_URL}/stop")
    try:
        print("Stop:", stop_res.json())
    except:
        print("Worker probably already exited on its own.")

    print("\nTest completed.")

if __name__ == "__main__":
    run_test()
