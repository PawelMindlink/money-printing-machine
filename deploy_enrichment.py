"""
Deploy Enrichment Pipeline to n8n.
1. Generate pinned test data from Iiyama Growth Opportunities
2. Add pinData to workflow JSON
3. Push to n8n server
"""
import json
import os
import sys
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
N8N_URL = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "cVucKbJhrTRXVpzI"  # Enrichment Pipeline

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# --- Step 1: Generate pinned test data from Iiyama ---
print("=== Step 1: Generating pinned test data ===")
csv_path = os.path.join(PROJECT_ROOT, "Output", "Iiyama", "Iiyama_Growth_Opportunities.csv")
df = pd.read_csv(csv_path)
actionable = df[df["calc_is_actionable"] == True].head(3)
print(f"Pinning {len(actionable)} Iiyama products for testing:")
for _, row in actionable.iterrows():
    title = str(row.get("feed_title", ""))[:60]
    cat = str(row.get("feed_category", ""))
    print(f"  - {row['feed_id']}: {title} | {cat}")

pin_items = []
for _, row in actionable.iterrows():
    item = {}
    for col in row.index:
        val = row[col]
        if pd.isna(val):
            item[col] = ""
        else:
            item[col] = val
    pin_items.append({"json": item})

# --- Step 2: Load workflow + add pinData ---
print("\n=== Step 2: Loading workflow JSON ===")
wf_path = os.path.join(PROJECT_ROOT, "Workflows", "Enrichment_Pipeline.json")
with open(wf_path, "r", encoding="utf-8") as f:
    workflow = json.load(f)

# pinData: save locally for manual pin in n8n UI
# (n8n PUT API does not accept pinData in body)
pin_data_path = os.path.join(PROJECT_ROOT, "tests", "iiyama_pin_data.json")
with open(pin_data_path, "w", encoding="utf-8") as f:
    json.dump(pin_items, f, indent=2, ensure_ascii=False, default=str)
print(f"Pin data saved to: {pin_data_path}")
print("  → Open 'Read Growth CSV' node in n8n, paste this data, and pin it")

print(f"Loaded {len(workflow['nodes'])} nodes")

# --- Step 3: Push to n8n ---
print(f"\n=== Step 3: Pushing to n8n ({WORKFLOW_ID}) ===")
payload = {
    "name": workflow["name"],
    "nodes": workflow["nodes"],
    "connections": workflow["connections"],
    "settings": workflow.get("settings", {"executionOrder": "v1"})
}

resp = requests.put(
    f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
    headers=HEADERS,
    json=payload
)

if resp.status_code == 200:
    result = resp.json()
    print(f"\nSUCCESS! Workflow updated at {result.get('updatedAt')}")
    print(f"Nodes on server: {[n['name'] for n in result.get('nodes', [])]}")
    print(f"URL: {N8N_URL}/workflow/{WORKFLOW_ID}")
else:
    print(f"\nERROR {resp.status_code}: {resp.text[:500]}")
    sys.exit(1)

print("\n=== Done! ===")
print("Next: Open in n8n, verify nodes render correctly, then test Phase 1")
