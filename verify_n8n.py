"""
Verify and activate both workflows on n8n server.
"""
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
key = os.getenv("N8N_API_KEY")
headers = {"X-N8N-API-KEY": key, "Content-Type": "application/json"}

ENRICHMENT_ID = "cVucKbJhrTRXVpzI"
MSC_ALGO_ID = "WADs1VFZV4wjeaQR"

# Verify Enrichment Pipeline
print("=== Enrichment Pipeline ===")
r = requests.get(f"{url}/api/v1/workflows/{ENRICHMENT_ID}", headers=headers)
wf = r.json()
nodes = [n["name"] for n in wf["nodes"]]
print(f"Nodes ({len(nodes)}): {nodes}")
print(f"Active: {wf.get('active')}")

# Check critical nodes
expected = ["Manual Trigger", "MSC-ALGO Trigger", "Discover Brands", "Load Config", 
            "Read Growth CSV", "Filter Actionable", "Claude: Analyze", "Write Enriched CSV"]
missing = [n for n in expected if n not in nodes]
if missing:
    print(f"MISSING NODES: {missing}")
else:
    print("All critical nodes present ✓")

# Verify MSC-ALGO
print("\n=== MSC-ALGO ===")
r2 = requests.get(f"{url}/api/v1/workflows/{MSC_ALGO_ID}", headers=headers)
wf2 = r2.json()
nodes2 = [n["name"] for n in wf2["nodes"]]
print(f"Nodes ({len(nodes2)}): {nodes2}")
has_trigger = "Trigger Enrichment" in nodes2
print(f"Trigger Enrichment present: {has_trigger}")

# Activate Enrichment Pipeline (required for webhook)
print("\n=== Activating Enrichment Pipeline ===")
activate = requests.patch(
    f"{url}/api/v1/workflows/{ENRICHMENT_ID}",
    headers=headers,
    json={"active": True}
)
if activate.status_code == 200:
    result = activate.json()
    print(f"Activated: {result.get('active')}")
    print(f"Webhook URL: {url}/webhook/enrichment-trigger")
else:
    print(f"Activation failed: {activate.status_code} - {activate.text[:300]}")

print("\n=== DONE ===")
