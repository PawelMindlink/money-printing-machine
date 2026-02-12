import requests
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 for output
sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = os.getenv("N8N_URL", "https://mindlink-n8n.ironcode.io").rstrip("/")
API_KEY = os.getenv("N8N_API_KEY")

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def check_access():
    print(f"Connecting to {N8N_URL}...")
    try:
        response = requests.get(f"{N8N_URL}/api/v1/workflows", headers=HEADERS)
        if response.status_code == 200:
            print("SUCCESS! Connection established.")
            data = response.json()
            workflows = data.get('data', [])
            print(f"Found {len(workflows)} workflows:")
            for w in workflows:
                print(f" - ID: {w['id']} | Name: {w['name']}")
        else:
            print(f"ERROR: Code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    check_access()
