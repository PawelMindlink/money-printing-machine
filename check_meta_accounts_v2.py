"""
check_meta_accounts_v2.py
Fetches ALL ad accounts accessible via:
  1. /me/adaccounts (personal user scope)
  2. /me/businesses -> each business's /owned_ad_accounts and /client_ad_accounts (agency scope)
Fixes: amount_spent divided by 100 (API returns in smallest currency unit)
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("META_ACCESS_TOKEN")
BASE = "https://graph.facebook.com/v21.0"
ACCOUNT_FIELDS = "id,name,account_status,currency,amount_spent,account_id"

STATUS_MAP = {
    1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_REVIEW",
    9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE", 101: "CLOSED"
}

if not token:
    print("ERROR: No META_ACCESS_TOKEN in .env")
    exit(1)

print(f"Token: {token[:20]}...\n")

def paginate(url, params):
    """Fetch all pages from a Meta Graph endpoint."""
    results = []
    while url:
        r = requests.get(url, params=params)
        if r.status_code != 200:
            print(f"  [ERROR] {r.status_code}: {r.text[:200]}")
            break
        data = r.json()
        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = {}  # next URL already has params baked in
    return results

def print_account(acc, source=""):
    status = STATUS_MAP.get(acc.get("account_status"), str(acc.get("account_status")))
    name = acc.get("name", "Unknown")
    acc_id = acc.get("account_id") or acc.get("id", "Unknown")
    currency = acc.get("currency", "")
    # API returns amount_spent in smallest currency unit (cents/groszy) — divide by 100
    raw_spent = acc.get("amount_spent")
    spent = f"{int(raw_spent)/100:,.2f} {currency}" if raw_spent is not None else "N/A"
    source_tag = f" [{source}]" if source else ""
    print(f"  [{status}]{source_tag} {name}")
    print(f"           ID: act_{acc_id} | Spent: {spent}")

# ── 1. Personal user accounts ─────────────────────────────────────────────────
print("=" * 60)
print("1. Personal user ad accounts (/me/adaccounts)")
print("=" * 60)
personal = paginate(f"{BASE}/me/adaccounts", {
    "access_token": token,
    "fields": ACCOUNT_FIELDS,
    "limit": 100
})
print(f"Found: {len(personal)}\n")
for acc in personal:
    print_account(acc, "personal")
print()

# ── 2. Business Manager accounts ──────────────────────────────────────────────
print("=" * 60)
print("2. Business Manager accounts (/me/businesses)")
print("=" * 60)
businesses = paginate(f"{BASE}/me/businesses", {
    "access_token": token,
    "fields": "id,name",
    "limit": 100
})
print(f"Found {len(businesses)} business(es):\n")

all_biz_accounts = {}

for biz in businesses:
    biz_id = biz.get("id")
    biz_name = biz.get("name")
    print(f"  Business: {biz_name} (ID: {biz_id})")

    # Owned accounts
    owned = paginate(f"{BASE}/{biz_id}/owned_ad_accounts", {
        "access_token": token,
        "fields": ACCOUNT_FIELDS,
        "limit": 100
    })
    # Client accounts (agency relationship)
    client = paginate(f"{BASE}/{biz_id}/client_ad_accounts", {
        "access_token": token,
        "fields": ACCOUNT_FIELDS,
        "limit": 100
    })

    print(f"    Owned: {len(owned)} | Client: {len(client)}")
    for acc in owned + client:
        acc_id = acc.get("account_id") or acc.get("id")
        if acc_id not in all_biz_accounts:
            all_biz_accounts[acc_id] = (acc, "client" if acc in client else "owned")

print()
print(f"Total unique BM accounts: {len(all_biz_accounts)}\n")
for acc_id, (acc, rel) in all_biz_accounts.items():
    print_account(acc, rel)

# ── 3. Summary ────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
all_ids = set(
    (acc.get("account_id") or acc.get("id")) for acc in personal
) | set(all_biz_accounts.keys())
print(f"Total unique accounts accessible: {len(all_ids)}")
