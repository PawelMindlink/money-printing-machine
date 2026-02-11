import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = "https://mindlink-n8n.ironcode.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTZkM2RkMi05OGY5LTRmMTYtOGIzYi1kN2I0ZjkzOTMxY2EiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTE4Y2Y3YWUtZGJiNy00NWVkLTkwNjAtZDBlNDVkMjNmNGNmIiwiaWF0IjoxNzcwODE4Njk1fQ.URFaTCPUZ2JnUwifCefk8wQmkXkWj--EfXK9oMpuhmU"
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
