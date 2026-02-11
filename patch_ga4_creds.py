"""
Force-patch GA4 nodes on n8n server to use googleServiceAccountApi.
Removes stale googleApi credential references that override the correct type.
"""
import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')

N8N = "https://mindlink-n8n.ironcode.io"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTZkM2RkMi05OGY5LTRmMTYtOGIzYi1kN2I0ZjkzOTMxY2EiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTE4Y2Y3YWUtZGJiNy00NWVkLTkwNjAtZDBlNDVkMjNmNGNmIiwiaWF0IjoxNzcwODE4Njk1fQ.URFaTCPUZ2JnUwifCefk8wQmkXkWj--EfXK9oMpuhmU"
WF_ID = "ApRz23ENs3s5HMOl"
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}

# 1. Fetch current workflow
r = requests.get(f"{N8N}/api/v1/workflows/{WF_ID}", headers=H)
wf = r.json()

# 2. Patch GA4 nodes
patched = 0
for node in wf.get("nodes", []):
    if node["name"] in ("Fetch GA4 Landing Page", "Fetch GA4 Items"):
        # Force correct credential type
        node["parameters"]["nodeCredentialType"] = "googleServiceAccountApi"
        
        # Clean credentials: remove googleApi, keep googleServiceAccountApi
        creds = node.get("credentials", {})
        if "googleApi" in creds:
            # Take the user's actual credential ID from googleApi and move it to googleServiceAccountApi
            user_cred = creds.pop("googleApi")
            creds["googleServiceAccountApi"] = user_cred
            print(f"PATCHED {node['name']}: moved credential {user_cred['id']} from googleApi -> googleServiceAccountApi")
        node["credentials"] = creds
        patched += 1

        print(f"  Final nodeCredentialType: {node['parameters']['nodeCredentialType']}")
        print(f"  Final credentials: {json.dumps(node['credentials'])}")

# 3. Push back
payload = {
    "name": wf.get("name", ""),
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": wf.get("settings", {})
}
r2 = requests.put(f"{N8N}/api/v1/workflows/{WF_ID}", headers=H, json=payload)
if r2.status_code == 200:
    print(f"\nSUCCESS: Patched {patched} nodes on server.")
else:
    print(f"\nERROR: {r2.status_code} - {r2.text}")
