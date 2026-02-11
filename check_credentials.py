import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = "https://mindlink-n8n.ironcode.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTZkM2RkMi05OGY5LTRmMTYtOGIzYi1kN2I0ZjkzOTMxY2EiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTE4Y2Y3YWUtZGJiNy00NWVkLTkwNjAtZDBlNDVkMjNmNGNmIiwiaWF0IjoxNzcwODE4Njk1fQ.URFaTCPUZ2JnUwifCefk8wQmkXkWj--EfXK9oMpuhmU"
WORKFLOW_ID = "ApRz23ENs3s5HMOl"

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# 1. Get all credentials
print("=== CREDENTIALS ===")
r = requests.get(f"{N8N_URL}/api/v1/credentials", headers=HEADERS)
if r.status_code == 200:
    for c in r.json().get("data", []):
        print(f"  ID: {c['id']} | Name: {c['name']} | Type: {c['type']}")
else:
    print(f"  Error: {r.status_code} {r.text[:200]}")

# 2. Get current workflow to see what credential IDs are set on server
print("\n=== WORKFLOW CREDENTIAL MAPPINGS ===")
r2 = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=HEADERS)
if r2.status_code == 200:
    wf = r2.json()
    for node in wf.get("nodes", []):
        creds = node.get("credentials", {})
        if creds:
            print(f"  Node: {node['name']}")
            for ctype, cval in creds.items():
                print(f"    {ctype}: id={cval.get('id')} name={cval.get('name')}")
else:
    print(f"  Error: {r2.status_code}")
