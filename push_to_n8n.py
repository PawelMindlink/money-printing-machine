import requests
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "ApRz23ENs3s5HMOl"  # MSC_ALGO_v4_Pipeline

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

with open("Workflows/MSC_ALGO_v4_Pipeline.json", "r", encoding="utf-8") as f:
    local_data = json.load(f)

payload = {
    "name": local_data["name"],
    "nodes": local_data["nodes"],
    "connections": local_data["connections"],
    "settings": local_data.get("settings", {"executionOrder": "v1"})
}

print(f"Pushing {len(payload['nodes'])} nodes to n8n ({WORKFLOW_ID})...")
print(f"Nodes: {[n['name'] for n in payload['nodes']]}")

resp = requests.put(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=HEADERS, json=payload)

if resp.status_code == 200:
    result = resp.json()
    print(f"SUCCESS! Updated at {result.get('updatedAt')}")
    print(f"Nodes on server: {[n['name'] for n in result.get('nodes', [])]}")
else:
    print(f"ERROR {resp.status_code}: {resp.text[:500]}")
