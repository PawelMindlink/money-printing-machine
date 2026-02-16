"""
Fix MSC-ALGO Trigger Enrichment expression and push to n8n.
Issue: $node["Parse Form"].json.brand fails on item index > 0
Fix: Use $('Parse Form').first().json.brand for single-item reference
"""
import json
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}

# --- Fix MSC-ALGO ---
print("=== Fixing MSC-ALGO Trigger Enrichment ===")
wf_path = "Workflows/MSC_ALGO_v5_Hybrid.json"
with open(wf_path, "r", encoding="utf-8") as f:
    wf = json.load(f)

for node in wf["nodes"]:
    if node["name"] == "Trigger Enrichment":
        old_body = node["parameters"].get("jsonBody", "")
        # Fix: use $('Parse Form').first() instead of $node["Parse Form"]
        node["parameters"]["jsonBody"] = '={{ JSON.stringify({ brand: $(\'Parse Form\').first().json.brand }) }}'
        print(f"  OLD: {old_body}")
        print(f"  NEW: {node['parameters']['jsonBody']}")
        break
else:
    print("  WARNING: Trigger Enrichment node not found!")

with open(wf_path, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=4, ensure_ascii=False)
print("  Saved MSC-ALGO")

# --- Push MSC-ALGO ---
MSC_ALGO_ID = "WADs1VFZV4wjeaQR"
payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": wf.get("settings", {"executionOrder": "v1"})
}

print(f"\n=== Pushing MSC-ALGO ({MSC_ALGO_ID}) ===")
r = requests.put(f"{N8N_URL}/api/v1/workflows/{MSC_ALGO_ID}", headers=HEADERS, json=payload)
if r.status_code == 200:
    print(f"  SUCCESS! Updated at {r.json().get('updatedAt')}")
else:
    print(f"  ERROR {r.status_code}: {r.text[:300]}")

# --- Push Enrichment Pipeline ---
ENRICHMENT_ID = "cVucKbJhrTRXVpzI"
with open("Workflows/Enrichment_Pipeline.json", "r", encoding="utf-8") as f:
    ep = json.load(f)

payload2 = {
    "name": ep["name"],
    "nodes": ep["nodes"],
    "connections": ep["connections"],
    "settings": ep.get("settings", {"executionOrder": "v1"})
}

print(f"\n=== Pushing Enrichment Pipeline ({ENRICHMENT_ID}) ===")
r2 = requests.put(f"{N8N_URL}/api/v1/workflows/{ENRICHMENT_ID}", headers=HEADERS, json=payload2)
if r2.status_code == 200:
    print(f"  SUCCESS! Updated at {r2.json().get('updatedAt')}")
    node_names = [n["name"] for n in r2.json().get("nodes", [])]
    print(f"  Nodes ({len(node_names)}): {node_names}")
else:
    print(f"  ERROR {r2.status_code}: {r2.text[:300]}")

# --- Re-activate Enrichment Pipeline ---
print(f"\n=== Activating Enrichment Pipeline ===")
r3 = requests.post(f"{N8N_URL}/api/v1/workflows/{ENRICHMENT_ID}/activate", headers=HEADERS)
if r3.status_code == 200:
    print(f"  Active: {r3.json().get('active')}")
else:
    print(f"  Activation: {r3.status_code}")

print("\n=== DONE ===")
print("Fixes applied:")
print("  1. Native Perplexity + Anthropic nodes (credential setup in n8n required)")
print("  2. Fixed Trigger Enrichment expression: $('Parse Form').first().json.brand")
print("  3. Fixed Code node escaping (rebuilt from Python strings)")
print("  4. Workflow chaining: fixed expression + webhook active")
print("  5. Error Trigger: kept with explanatory note (normal n8n behavior)")
