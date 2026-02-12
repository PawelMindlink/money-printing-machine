import requests
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Configure for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "ApRz23ENs3s5HMOl"  # MSC_ALGO_v4_Pipeline
FILE_PATH = os.path.join("Workflows", "MSC_ALGO_v4_Pipeline.json")

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def force_sync():
    """Forces an immediate sync of the workflow to n8n."""
    print(f"--- FORCE SYNC STARTED ---")
    
    if not os.path.exists(FILE_PATH):
        print(f"Error: File {FILE_PATH} not found!")
        return

    try:
        print(f"Reading file: {FILE_PATH}")
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            local_data = json.load(f)

        payload = {
            "name": local_data.get("name", "MSC_ALGO_v4_Pipeline"),
            "nodes": local_data["nodes"],
            "connections": local_data["connections"],
            "settings": local_data.get("settings", {"executionOrder": "v1"})
        }

        print(f"Uploading to: {N8N_URL}/api/v1/workflows/{WORKFLOW_ID}")
        response = requests.put(
            f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
            headers=HEADERS,
            json=payload,
            timeout=30  # Add timeout
        )

        if response.status_code == 200:
            result = response.json()
            nodes = [n['name'] for n in result.get('nodes', [])]
            # Verify Classifier Node
            has_classifier = "MSC-ALGO Classifier" in nodes
            print(f"SUCCESS: Workflow updated.")
            print(f"Active Nodes: {len(nodes)}")
            print(f"Classifier Node Present: {has_classifier}")
        else:
            print(f"ERROR {response.status_code}: {response.text[:500]}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    force_sync()
