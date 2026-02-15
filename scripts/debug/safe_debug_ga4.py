"""
Update workflow:
1. Fetch GA4 Landing Page: Keep filter removed (for diagnosis) but set LIMIT = 1000 (for safety).
2. Push to n8n.
"""
import json, requests, os
from dotenv import load_dotenv
load_dotenv()

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "WADs1VFZV4wjeaQR"
headers = {"X-N8N-API-KEY": API_KEY}

r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers)
wf = r.json()

# Set Fetch GA4 Landing Page limit to 1000 and ensure no filter
for node in wf["nodes"]:
    if node["name"] == "Fetch GA4 Landing Page":
        print("Found Fetch GA4 Landing Page node")
        
        # New body with limit 1000 and no filter
        new_body = "={{ JSON.stringify({ dateRanges: [{ startDate: $node['Margin Resolver'].json.DATE_FROM, endDate: $node['Margin Resolver'].json.DATE_TO }], dimensions: [{ name: 'landingPagePlusQueryString' }], metrics: [{ name: 'sessions' }, { name: 'purchaseRevenue' }, { name: 'transactions' }, { name: 'totalUsers' }, { name: 'firstTimePurchasers' }], orderBys: [{ metric: { metricName: 'sessions' }, desc: true }], limit: 1000 }) }}"
        
        node["parameters"]["jsonBody"] = new_body
        print("Set GA4 Limit to 1000 (safe)")
        break

# Save locally
WF_PATH = "Workflows/MSC_ALGO_v5_Hybrid.json"
with open(WF_PATH, "w", encoding="utf-8") as f:
    json.dump(wf, f, indent=4, ensure_ascii=False)
print("Saved locally")

# Push to n8n
push_headers = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": wf.get("settings", {"executionOrder": "v1"})
}
r = requests.put(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=push_headers, json=payload)
if r.status_code == 200:
    result = r.json()
    print(f"Pushed to n8n OK! {len(result.get('nodes', []))} nodes")
else:
    print(f"ERROR {r.status_code}: {r.text[:400]}")
