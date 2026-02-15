"""Check Fetch GA4 Landing Page for continueOnFail or alwaysOutputData."""
import json, requests, os
from dotenv import load_dotenv
load_dotenv()

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "WADs1VFZV4wjeaQR"
headers = {"X-N8N-API-KEY": API_KEY}

r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers)
wf = r.json()

for node in wf["nodes"]:
    if node["name"] == "Fetch GA4 Landing Page":
        print(f"Node: {node['name']}")
        print(f"continueOnFail: {node.get('continueOnFail', False)}")
        print(f"alwaysOutputData: {node.get('alwaysOutputData', False)}")
        print(f"onError: {node.get('onError', 'stopWorkflow')}")
        break
