import time
import requests
import sys

URL = "https://money-printing-machine.onrender.com/docs"
TIMEOUT = 180  # 3 minutes
INTERVAL = 10

print(f"Monitoring {URL} for {TIMEOUT} seconds...")
start = time.time()

while time.time() - start < TIMEOUT:
    try:
        r = requests.get(URL, timeout=5)
        if r.status_code == 200:
            print("✅ SUCCESS: API is UP (200 OK)")
            sys.exit(0)
        else:
            print(f"⚠️ Status: {r.status_code} - Waiting...")
    except Exception as e:
        print(f"❌ Error: {e} - Waiting...")
    
    time.sleep(INTERVAL)

print("❌ TIMEOUT: API did not come up in time.")
sys.exit(1)
