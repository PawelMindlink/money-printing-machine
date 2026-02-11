import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')

N8N = "https://mindlink-n8n.ironcode.io"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTZkM2RkMi05OGY5LTRmMTYtOGIzYi1kN2I0ZjkzOTMxY2EiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTE4Y2Y3YWUtZGJiNy00NWVkLTkwNjAtZDBlNDVkMjNmNGNmIiwiaWF0IjoxNzcwODE4Njk1fQ.URFaTCPUZ2JnUwifCefk8wQmkXkWj--EfXK9oMpuhmU"
H = {"X-N8N-API-KEY": KEY}

r = requests.get(f"{N8N}/api/v1/workflows/ApRz23ENs3s5HMOl", headers=H)
wf = r.json()

for n in wf.get("nodes", []):
    name = n["name"]
    if "GA4" in name or "Meta" in name:
        params = n.get("parameters", {})
        creds = n.get("credentials")
        print(f"--- {name} ---")
        print(f"  authentication: {params.get('authentication', 'N/A')}")
        print(f"  nodeCredentialType: {params.get('nodeCredentialType', 'N/A')}")
        print(f"  credentials block: {json.dumps(creds, indent=2)}")
        print()
