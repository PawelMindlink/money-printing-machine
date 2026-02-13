"""Extract V5 node code to files for analysis."""
import requests, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
headers = {"X-N8N-API-KEY": API_KEY}

r = requests.get(f"{N8N_URL}/api/v1/workflows/WADs1VFZV4wjeaQR", headers=headers)
wf = r.json()

for n in wf["nodes"]:
    name = n["name"].replace(" ", "_").replace("(", "").replace(")", "")
    params = n.get("parameters", {})
    
    # Extract JS/Python code
    code = params.get("jsCode", params.get("pythonCode", ""))
    if code:
        with open(f"debug_{name}.js", "w", encoding="utf-8") as f:
            f.write(code)
        print(f"Saved: debug_{name}.js ({len(code)} chars)")
    
    # Save full parameters
    with open(f"debug_{name}_params.json", "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, ensure_ascii=False)
    print(f"Saved: debug_{name}_params.json")

# Save connections
with open("debug_connections.json", "w", encoding="utf-8") as f:
    json.dump(wf["connections"], f, indent=2, ensure_ascii=False)
print("Saved: debug_connections.json")
