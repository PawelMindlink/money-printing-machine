"""Check Margin Resolver code and fix all Normalize nodes."""
import json, requests, os
from dotenv import load_dotenv
load_dotenv()

N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")
WORKFLOW_ID = "WADs1VFZV4wjeaQR"
headers = {"X-N8N-API-KEY": API_KEY}

r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers)
wf = r.json()

# 1. Print full Margin Resolver code
print("=== MARGIN RESOLVER CODE ===")
for node in wf["nodes"]:
    if node["name"] == "Margin Resolver":
        print(node["parameters"]["jsCode"])
        break

print("\n=== NORMALIZE GA4 ITEMS CODE ===")
for node in wf["nodes"]:
    if node["name"] == "Normalize GA4 Items":
        print(node["parameters"]["jsCode"])
        break

print("\n=== NORMALIZE META ADS CODE ===")
for node in wf["nodes"]:
    if node["name"] == "Normalize Meta Ads":
        print(node["parameters"]["jsCode"])
        break
