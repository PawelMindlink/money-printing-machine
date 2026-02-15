"""
Align n8n workflow with local script:
1. Parse Form: Default DATE_FROM = '2024-01-01' (instead of y1ago).
2. Fetch GA4 Landing Page: Use 'ecommercePurchases' instead of 'transactions'.
3. Normalize GA4 LP: Update metric index mapping if needed.
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

# 1. Update Parse Form defaults
for node in wf["nodes"]:
    if node["name"] == "Parse Form":
        code = node["parameters"]["jsCode"]
        # Replace y1ago logic with hardcoded 2024-01-01
        if "_date_from:" in code:
            # We want to replace:
            #   _date_from: (form['Date From (YYYY-MM-DD)'] || '').trim() || y1ago.toISOString().split('T')[0],
            # with:
            #   _date_from: (form['Date From (YYYY-MM-DD)'] || '').trim() || '2024-01-01',
            
            # Use strict replace to avoid messing up
            new_code = code.replace("y1ago.toISOString().split('T')[0]", "'2024-01-01'")
            node["parameters"]["jsCode"] = new_code
            print("Updated Parse Form default date to 2024-01-01")
        break

# 2. Update Fetch GA4 Landing Page metrics
for node in wf["nodes"]:
    if node["name"] == "Fetch GA4 Landing Page":
        print("Found Fetch GA4 Landing Page")
        # Body: metrics: [{ name: 'sessions' }, { name: 'purchaseRevenue' }, { name: 'transactions' }, { name: 'totalUsers' }, { name: 'firstTimePurchasers' }]
        # Change 'transactions' to 'ecommercePurchases'
        body = node["parameters"]["jsonBody"]
        if "'transactions'" in body:
            new_body = body.replace("'transactions'", "'ecommercePurchases'")
            node["parameters"]["jsonBody"] = new_body
            print("Updated metric: transactions -> ecommercePurchases")
        break

# 3. Update Fetch GA4 Items metrics (just in case)
for node in wf["nodes"]:
    if node["name"] == "Fetch GA4 Items":
        print("Found Fetch GA4 Items")
        # Body: metrics: [{ name: 'itemsViewed' }, { name: 'itemRevenue' }, { name: 'itemsPurchased' }]
        # Local script uses: itemsViewed, itemsPurchased, itemRevenue
        # NO change needed here as names match GA4 item metrics (check ga4_api_client.py lines 82-84)
        # itemsViewed, itemsPurchased, itemRevenue -> matches n8n
        pass

# 4. Update Normalize GA4 LP (index mapping might change?)
# In Fetch GA4 LP, the order was: sessions, purchaseRevenue, transactions, totalUsers, firstTimePurchasers
# We just renamed 'transactions' to 'ecommercePurchases', order stays same.
# So Normalize GA4 LP index 2 is still the purchase count.
# No code change needed in Normalize GA4 LP (it just reads metricValues[2]).

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
