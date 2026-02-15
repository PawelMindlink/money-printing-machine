"""Check Parse Form node for default dates."""
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
    if node["name"] == "Parse Form":
        print("=== PARSE FORM CODE ===")
        print(node["parameters"]["jsCode"])
        break

for node in wf["nodes"]:
    if node["name"] == "Pipeline Form":
        print("\n=== PIPELINE FORM DEFAULTS ===")
        props = node["parameters"].get("formProperties", {}).get("formProperties", [])
        for prop in props:
            print(f"  {prop['fieldLabel']} ({prop['fieldName']}): {prop.get('defaultValue', 'NO DEFAULT')}")
        break
