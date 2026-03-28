import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("META_ACCESS_TOKEN")
if not token:
    print("ERROR: No META_ACCESS_TOKEN found in .env")
    exit(1)

print(f"Token found: {token[:20]}...")

url = "https://graph.facebook.com/v21.0/me/adaccounts"
params = {
    "access_token": token,
    "fields": "id,name,account_status,currency,amount_spent",
    "limit": 100
}

r = requests.get(url, params=params)
print(f"HTTP Status: {r.status_code}")

if r.status_code != 200:
    print(f"Error response: {r.text}")
    exit(1)

data = r.json()
accounts = data.get("data", [])
print(f"\nFound {len(accounts)} ad accounts:\n")

status_map = {
    1: "ACTIVE",
    2: "DISABLED",
    3: "UNSETTLED",
    7: "PENDING_REVIEW",
    9: "IN_GRACE_PERIOD",
    100: "PENDING_CLOSURE",
    101: "CLOSED"
}

for acc in accounts:
    status_code = acc.get("account_status")
    status = status_map.get(status_code, str(status_code))
    name = acc.get("name", "Unknown")
    acc_id = acc.get("id", "Unknown")
    spent = acc.get("amount_spent", "N/A")
    currency = acc.get("currency", "")
    print(f"  [{status}] {name}")
    print(f"           ID: {acc_id} | Spent: {spent} {currency}")
    print()

next_page = data.get("paging", {}).get("next")
if next_page:
    print("[!] More pages exist - results may be incomplete")
else:
    print("[OK] All pages fetched")
