
import requests
import json
from reproduce_n8n_priority import load_local_data

URL = "https://money-printing-machine.onrender.com/process"

def test_live():
    print("--- Loading Payload ---")
    data = load_local_data()
    
    # Sanitize payload (replace NaN with None/0)
    import math
    def sanitize(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(x) for x in obj]
        return obj

    data = sanitize(data)
    
    # Send request
    print(f"Sending POST to {URL}...")
    try:
        resp = requests.post(URL, json=data, timeout=120)
        if resp.status_code == 200:
            print("Success! Parsing response...")
            result = resp.json()
            if isinstance(result, list) and len(result) > 0:
                print(f"Received {len(result)} items.")
                
                # Check Priority Distribution
                priorities = {}
                for item in result:
                    p = item.get('calc_priority', 'Unknown')
                    priorities[p] = priorities.get(p, 0) + 1
                
                print("Priority Distribution:")
                for k in sorted(priorities.keys()):
                    print(f"{k}: {priorities[k]}")
                    
                # Check sample item 1252
                sample = next((x for x in result if str(x.get('feed_id')) == '1252'), None)
                if sample:
                    print(f"\nItem 1252 Priority: {sample.get('calc_priority')}")
                    print(f"Item 1252 Sessions: {sample.get('ga4lp_sessions')}")
                    print(f"Item 1252 Path Key: {sample.get('path_key', 'N/A')}")
                else:
                    print("\nItem 1252 not found in response.")
            else:
                print("Response is empty list or invalid format.")
        else:
            print(f"Error: {resp.status_code}")
            print(resp.text[:500])
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_live()
