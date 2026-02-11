import time
import requests
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

# --- KONFIGURACJA ---
N8N_URL = "https://mindlink-n8n.ironcode.io"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMTZkM2RkMi05OGY5LTRmMTYtOGIzYi1kN2I0ZjkzOTMxY2EiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiNTE4Y2Y3YWUtZGJiNy00NWVkLTkwNjAtZDBlNDVkMjNmNGNmIiwiaWF0IjoxNzcwODE4Njk1fQ.URFaTCPUZ2JnUwifCefk8wQmkXkWj--EfXK9oMpuhmU"

# Workflow do synchronizacji
WORKFLOW_ID = "ApRz23ENs3s5HMOl"  # MSC_ALGO_v4_Pipeline

# Plik, ktory obserwujemy
FILE_PATH = os.path.join("Workflows", "MSC_ALGO_v4_Pipeline.json")

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def sync_to_n8n():
    """Obserwuje plik JSON i wysyla go do n8n po kazdej zmianie."""
    if not os.path.exists(FILE_PATH):
        print(f"Error: File {FILE_PATH} not found!")
        return

    print(f"--- LIVE SYNC ENABLED ---")
    print(f"File:     {FILE_PATH}")
    print(f"Target:   {N8N_URL}/api/v1/workflows/{WORKFLOW_ID}")
    print(f"Save the file in VS Code -> n8n updates automatically.\n")

    last_mtime = os.path.getmtime(FILE_PATH)

    while True:
        try:
            time.sleep(1)
            current_mtime = os.path.getmtime(FILE_PATH)

            if current_mtime != last_mtime:
                print(f"[{time.strftime('%H:%M:%S')}] Change detected! Syncing...")

                try:
                    with open(FILE_PATH, 'r', encoding='utf-8') as f:
                        local_data = json.load(f)

                    # n8n PUT API accepts only: name, nodes, connections, settings
                    payload = {
                        "name": local_data.get("name", "MSC_ALGO_v4_Pipeline"),
                        "nodes": local_data["nodes"],
                        "connections": local_data["connections"],
                        "settings": local_data.get("settings", {"executionOrder": "v1"})
                    }

                    response = requests.put(
                        f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}",
                        headers=HEADERS,
                        json=payload
                    )

                    if response.status_code == 200:
                        result = response.json()
                        nodes = [n['name'] for n in result.get('nodes', [])]
                        print(f"[{time.strftime('%H:%M:%S')}] SUCCESS: {len(nodes)} nodes -> {nodes}")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ERROR {response.status_code}: {response.text[:200]}")

                except json.JSONDecodeError:
                    print(f"[{time.strftime('%H:%M:%S')}] INVALID JSON - fix syntax.")
                except Exception as e:
                    print(f"[{time.strftime('%H:%M:%S')}] ERROR: {e}")

                last_mtime = current_mtime

        except KeyboardInterrupt:
            print("\nStopped.")
            break

if __name__ == "__main__":
    sync_to_n8n()
