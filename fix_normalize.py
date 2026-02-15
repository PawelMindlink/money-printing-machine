"""
Fix BOTH Normalize GA4 nodes to be null-safe AND check Build Config,
then push everything to n8n.
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

# Show Build Config code
for node in wf["nodes"]:
    if node["name"] == "Build Config":
        print("=== BUILD CONFIG CODE ===")
        print(node["parameters"]["jsCode"])
        print()
        break

# Fix Normalize GA4 LP — add null check for rows
for node in wf["nodes"]:
    if node["name"] == "Normalize GA4 LP":
        node["parameters"]["jsCode"] = """// NORMALIZE GA4 LP (null-safe)
const response = $input.first().json;
const rows = response.rows || [];
if (rows.length === 0) {
  console.log('WARNING: GA4 LP returned 0 rows — filter may be too strict or property ID wrong');
  return [{ json: { ga4_lp_url: '', ga4_sessions: 0, ga4_revenue: 0, ga4_trans: 0, ga4_users: 0, ga4_first_time_purchasers: 0, _empty: true } }];
}
return rows.map(row => {
  const lp = row.dimensionValues[0].value || '';
  return { json: {
    ga4_lp_url: lp,
    ga4_norm_path: lp.toLowerCase().replace(/^\\/|\\/$/g, '').split('?')[0],
    ga4_sessions: parseInt(row.metricValues[0].value),
    ga4_revenue: parseFloat(row.metricValues[1].value),
    ga4_trans: parseInt(row.metricValues[2].value),
    ga4_users: parseInt(row.metricValues[3].value),
    ga4_first_time_purchasers: parseInt(row.metricValues[4].value)
  }};
});"""
        print("Fixed Normalize GA4 LP")

# Fix Normalize GA4 Items — add null check for rows
for node in wf["nodes"]:
    if node["name"] == "Normalize GA4 Items":
        node["parameters"]["jsCode"] = """// NORMALIZE GA4 ITEMS (null-safe)
const response = $input.first().json;
const rows = response.rows || [];
if (rows.length === 0) {
  console.log('WARNING: GA4 Items returned 0 rows');
  return [{ json: { ga4_item_id: '', ga4_item_views: 0, ga4_item_rev: 0, ga4_item_purch: 0, _empty: true } }];
}
return rows.map(row => {
  return { json: {
    ga4_item_id: row.dimensionValues[0].value,
    ga4_item_views: parseInt(row.metricValues[0].value),
    ga4_item_rev: parseFloat(row.metricValues[1].value),
    ga4_item_purch: parseInt(row.metricValues[2].value)
  }};
});"""
        print("Fixed Normalize GA4 Items")

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
