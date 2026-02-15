"""
Modify workflow to:
1. Remove GA4 LP session filter (to see if ANY data exists).
2. Log DATE_FROM / DATE_TO in Python Bridge _debug output.
Then push to n8n.
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

# 1. Remove filter from Fetch GA4 Landing Page
found_ga4 = False
for node in wf["nodes"]:
    if node["name"] == "Fetch GA4 Landing Page":
        print("Found Fetch GA4 Landing Page node")
        # Ensure jsonBody doesn't have the filter
        # Original: ... metricFilter: { filter: { fieldName: 'sessions', numericFilter: { operation: 'GREATER_THAN_OR_EQUAL', value: { int64Value: '50' } } } }, ...
        # New: remove that part
        
        # It's easier to reconstruct the jsonBody entirely to be safe
        new_body = "={{ JSON.stringify({ dateRanges: [{ startDate: $node['Margin Resolver'].json.DATE_FROM, endDate: $node['Margin Resolver'].json.DATE_TO }], dimensions: [{ name: 'landingPagePlusQueryString' }], metrics: [{ name: 'sessions' }, { name: 'purchaseRevenue' }, { name: 'transactions' }, { name: 'totalUsers' }, { name: 'firstTimePurchasers' }], orderBys: [{ metric: { metricName: 'sessions' }, desc: true }], limit: 10000 }) }}"
        
        node["parameters"]["jsonBody"] = new_body
        print("Removed session filter from Fetch GA4 Landing Page")
        found_ga4 = True
        break

if not found_ga4:
    print("ERROR: Could not find Fetch GA4 Landing Page node")

# 2. Add dates to Python Bridge _debug
found_bridge = False
for node in wf["nodes"]:
    if node["name"] == "Python Bridge":
        print("Found Python Bridge node")
        # Current code ends with:
        #   _debug: { feed: feed.length, meta: meta.length, items: items.length, lp: lp.length, warnings: warnings },
        # We want to add date_from and date_to
        
        old_code = node["parameters"]["jsCode"]
        if "date_from:" not in old_code:
            new_code = old_code.replace(
                "_debug: { feed: feed.length, meta: meta.length, items: items.length, lp: lp.length, warnings: warnings },",
                "_debug: { feed: feed.length, meta: meta.length, items: items.length, lp: lp.length, warnings: warnings, date_from: config.DATE_FROM, date_to: config.DATE_TO },"
            )
            node["parameters"]["jsCode"] = new_code
            print("Added dates to Python Bridge logging")
        else:
            print("Dates already logged in Python Bridge")
        found_bridge = True
        break

if not found_bridge:
    print("ERROR: Could not find Python Bridge node")

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
