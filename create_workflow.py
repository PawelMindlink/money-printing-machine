import requests
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIG ---
N8N_URL = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")

if not API_KEY:
    print("ERROR: N8N_API_KEY not found in environment variables!")
    sys.exit(1)

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def create_new_workflow(name):
    """Creates a new empty workflow in n8n and returns its ID."""
    payload = {
        "name": name,
        "nodes": [],
        "connections": {},
        "settings": {"executionOrder": "v1"}
    }

    print(f"Creating workflow '{name}' at {N8N_URL}...")
    
    response = requests.post(
        f"{N8N_URL}/api/v1/workflows",
        headers=HEADERS,
        json=payload
    )

    if response.status_code == 200:
        data = response.json()
        workflow_id = data.get("id")
        print(f"SUCCESS! New Workflow ID: {workflow_id}")
        print(f"URL: {N8N_URL}/workflow/{workflow_id}")
        return workflow_id
    else:
        print(f"ERROR {response.status_code}: {response.text}")
        return None

if __name__ == "__main__":
    wf_name = sys.argv[1] if len(sys.argv) > 1 else "New Antigravity Workflow"
    create_new_workflow(wf_name)
