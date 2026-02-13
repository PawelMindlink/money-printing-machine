"""Dump key V5 workflow nodes for analysis."""
import requests, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
headers = {"X-N8N-API-KEY": API_KEY}

r = requests.get(f"{N8N_URL}/api/v1/workflows/WADs1VFZV4wjeaQR", headers=headers)
wf = r.json()

target_nodes = ["Python Bridge", "Python Brain (API)", "Parse API Response", "Output to Google Sheets"]
for n in wf["nodes"]:
    if n["name"] in target_nodes:
        print(f"===== {n['name']} =====")
        print(f"Type: {n['type']}")
        params = n.get("parameters", {})
        print(json.dumps(params, indent=2, ensure_ascii=False))
        print()

# Also dump connections
print("===== CONNECTIONS =====")
for src, conns in wf["connections"].items():
    if src in target_nodes or any(
        c["node"] in target_nodes 
        for conn_type in conns.values() 
        for conn_list in conn_type 
        for c in conn_list
    ):
        print(f"{src} ->")
        print(json.dumps(conns, indent=2, ensure_ascii=False))
        print()
