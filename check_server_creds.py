import requests, json, sys, os
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

N8N = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
KEY = os.getenv("N8N_API_KEY")
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
