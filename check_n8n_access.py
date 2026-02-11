import requests
import json
import sys

# Force UTF-8 for output
sys.stdout.reconfigure(encoding='utf-8')

N8N_URL = "https://mindlink-n8n.ironcode.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTZkM2RkMi05OGY5LTRmMTYtOGIzYi1kN2I0ZjkzOTMxY2EiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTE4Y2Y3YWUtZGJiNy00NWVkLTkwNjAtZDBlNDVkMjNmNGNmIiwiaWF0IjoxNzcwODE4Njk1fQ.URFaTCPUZ2JnUwifCefk8wQmkXkWj--EfXK9oMpuhmU"

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
