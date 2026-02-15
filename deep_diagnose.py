"""
Deep diagnosis on new output file + direct API test.
"""
import csv, json, sys, requests
sys.path.insert(0, "src")
import business_logic_layer as bl

NEW_FILE = r"c:\Users\Paweł\Documents\GitHub\Money Printing Machine\Input\Margin Rules Template - msc_algo_output (3).csv"
GOLD_STD = r"c:\Users\Paweł\Documents\GitHub\Money Printing Machine\Input\Gold Standard 09.02.26 Iiyama_Growth_Opportunities - Iiyama_Growth_Opportunities.csv"

# ============================================
# PART 1: Analyze new output
# ============================================
print("=" * 60)
print("PART 1: NEW OUTPUT ANALYSIS")
print("=" * 60)

with open(NEW_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Rows: {len(rows)}")
print(f"Columns ({len(rows[0].keys())}): {list(rows[0].keys())[:15]}...")

# Segment distribution
segments = {}
priorities = {}
ga4_classes = {}
meta_classes = {}
reasons = {}
sessions_nonzero = 0
meta_spend_nonzero = 0
meta_purchases_nonzero = 0

for row in rows:
    seg = row.get("calc_segment", "")
    pri = row.get("calc_priority", "")
    g4c = row.get("ga4_class", "")
    mc = row.get("meta_class", "")
    reason = row.get("calc_reason", "")
    sess = float(row.get("ga4lp_sessions", 0) or 0)
    spend = float(row.get("meta_spend", 0) or 0)
    mpurch = float(row.get("meta_purchases", 0) or 0)
    
    segments[seg] = segments.get(seg, 0) + 1
    priorities[pri] = priorities.get(pri, 0) + 1
    ga4_classes[g4c] = ga4_classes.get(g4c, 0) + 1
    meta_classes[mc] = meta_classes.get(mc, 0) + 1
    reasons[reason] = reasons.get(reason, 0) + 1
    if sess > 0: sessions_nonzero += 1
    if spend > 0: meta_spend_nonzero += 1
    if mpurch > 0: meta_purchases_nonzero += 1

print(f"\nSegments: {json.dumps(segments, indent=2)}")
print(f"\nPriorities: {json.dumps(priorities, indent=2)}")
print(f"\nGA4 classes: {json.dumps(ga4_classes, indent=2)}")
print(f"\nMeta classes: {json.dumps(meta_classes, indent=2)}")
print(f"\nReasons: {json.dumps(reasons, indent=2)}")
print(f"\nRows with ga4lp_sessions > 0: {sessions_nonzero}/{len(rows)}")
print(f"Rows with meta_spend > 0: {meta_spend_nonzero}/{len(rows)}")
print(f"Rows with meta_purchases > 0: {meta_purchases_nonzero}/{len(rows)}")

# Check key thresholds
print("\n--- Session distribution ---")
session_ranges = {"0": 0, "1-49": 0, "50-299": 0, "300-999": 0, "1000+": 0}
for row in rows:
    s = float(row.get("ga4lp_sessions", 0) or 0)
    if s == 0: session_ranges["0"] += 1
    elif s < 50: session_ranges["1-49"] += 1
    elif s < 300: session_ranges["50-299"] += 1
    elif s < 1000: session_ranges["300-999"] += 1
    else: session_ranges["1000+"] += 1
print(f"  {session_ranges}")

# Check ga4item_views
print("\n--- GA4 Item Views distribution ---")
view_ranges = {"0": 0, "1-299": 0, "300-999": 0, "1000+": 0}
for row in rows:
    v = float(row.get("ga4item_views", 0) or 0)
    if v == 0: view_ranges["0"] += 1
    elif v < 300: view_ranges["1-299"] += 1
    elif v < 1000: view_ranges["300-999"] += 1
    else: view_ranges["1000+"] += 1
print(f"  {view_ranges}")

# Show sample rows with sessions > 0
print("\n--- Sample rows with sessions > 0 ---")
count = 0
for row in rows:
    s = float(row.get("ga4lp_sessions", 0) or 0)
    if s > 0 and count < 5:
        print(f"  ID={row.get('feed_id')}: sessions={s}, segment={row.get('calc_segment')}, "
              f"ga4_class={row.get('ga4_class')}, reason={row.get('calc_reason')}")
        count += 1

# ============================================
# PART 2: Compare with gold standard
# ============================================
print("\n" + "=" * 60)
print("PART 2: GOLD STANDARD COMPARISON")
print("=" * 60)

with open(GOLD_STD, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    gs_rows = list(reader)

gs_segments = {}
gs_sessions_nonzero = 0
for row in gs_rows:
    seg = row.get("calc_segment", "")
    gs_segments[seg] = gs_segments.get(seg, 0) + 1
    s = float(row.get("ga4lp_sessions", 0) or 0)
    if s > 0: gs_sessions_nonzero += 1

print(f"Gold std segments: {json.dumps(gs_segments, indent=2)}")
print(f"Gold std rows with sessions > 0: {gs_sessions_nonzero}/{len(gs_rows)}")

# Side by side
print("\n--- Segment comparison ---")
all_segs = sorted(set(list(segments.keys()) + list(gs_segments.keys())))
print(f"  {'Segment':<25} {'Gold':>6} {'New':>6} {'Diff':>6}")
for seg in all_segs:
    g = gs_segments.get(seg, 0)
    n = segments.get(seg, 0)
    d = n - g
    marker = " <<<" if abs(d) > 3 else ""
    print(f"  {seg:<25} {g:>6} {n:>6} {d:>+6}{marker}")

# ============================================
# PART 3: Direct API test with real feed data
# ============================================
print("\n" + "=" * 60)
print("PART 3: DIRECT API TEST")
print("=" * 60)

# Build payload from real feed data
feed_payload = []
for row in rows[:5]:
    if row.get("feed_id"):
        feed_payload.append({
            "feed_id": str(row["feed_id"]),
            "feed_title": row.get("feed_title", ""),
            "feed_link": row.get("feed_link", ""),
            "feed_brand": row.get("feed_brand", ""),
            "feed_category": row.get("feed_category", ""),
            "feed_category_full": row.get("feed_category_full", ""),
            "feed_price_str": str(row.get("calc_gross_price", "0")) + " PLN",
            "norm_url": row.get("norm_url", ""),
            "base_gross_margin": float(row.get("base_gross_margin", 0.1) or 0.1),
        })

# Create matching LP data
lp_payload = []
for item in feed_payload:
    norm = item.get("norm_url", "")
    if norm:
        path = norm
        if "/" in path and not path.startswith("/"):
            path = path[path.find("/"):]
        lp_payload.append({
            "ga4_lp_url": path,
            "ga4_norm_path": path.lstrip("/").lower().split("?")[0],
            "ga4_sessions": 500,
            "ga4_revenue": 25000.0,
            "ga4_trans": 8,
            "ga4_users": 400,
            "ga4_first_time_purchasers": 3,
        })

payload = {
    "feed": feed_payload,
    "meta_ads": [],
    "ga4_items": [],
    "ga4_lp": lp_payload,
    "config": {"brand": "Iiyama", "vat_rate": 0.23, "default_margin": 0.10, "margin_rules": []}
}

print(f"Sending: feed={len(feed_payload)}, lp={len(lp_payload)}")
for i, lp in enumerate(lp_payload):
    print(f"  LP[{i}] url={lp['ga4_lp_url'][:80]}...")

try:
    r = requests.post("https://money-printing-machine.onrender.com/process", json=payload, timeout=120)
    if r.status_code == 200:
        result = r.json()
        if isinstance(result, list):
            print(f"\nAPI returned: {len(result)} rows")
            for row in result:
                print(f"  ID={row.get('feed_id')}: sessions={row.get('ga4lp_sessions')}, "
                      f"segment={row.get('calc_segment')}, ga4_class={row.get('ga4_class')}, "
                      f"priority={row.get('calc_priority')}")
        else:
            print(f"Result type: {type(result)}, content: {str(result)[:300]}")
    else:
        print(f"ERROR: {r.status_code} - {r.text[:500]}")
except Exception as e:
    print(f"ERROR: {e}")
