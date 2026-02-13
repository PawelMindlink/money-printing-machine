"""Update V5 workflow on n8n with the correct Render API URL."""
import requests, json, os, sys
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "WADs1VFZV4wjeaQR"
RENDER_URL = "https://money-printing-machine.onrender.com"

headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

# 1. GET current workflow
print(f"Fetching workflow {WORKFLOW_ID}...")
r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers)
if r.status_code != 200:
    print(f"ERROR fetching: {r.status_code} {r.text[:200]}")
    sys.exit(1)

wf = r.json()

# 2. Find and update HTTP Request node
updated = False
for node in wf["nodes"]:
    if node["name"] == "Python Brain (API)":
        # Replace dynamic expression with hardcoded URL
        node["parameters"]["url"] = f"{RENDER_URL}/process"
        print(f"Updated {node['name']} URL to: {RENDER_URL}/process")
        updated = True
        break

if not updated:
    print("ERROR: Could not find 'Python Brain (API)' node!")
    sys.exit(1)

# 3. PUT updated workflow
payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": wf.get("settings", {})
}
r = requests.put(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers, json=payload)
if r.status_code == 200:
    print(f"SUCCESS! V5 workflow updated with Render URL")
else:
    print(f"ERROR {r.status_code}: {r.text[:300]}")
