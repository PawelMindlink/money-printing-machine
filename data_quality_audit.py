"""
MSC-ALGO v4 — Data Quality Audit (Direct API)
Runs the same queries n8n runs, captures raw data, and performs audit.
Brand: Iiyama (last successful run)
"""
import requests, json, sys, statistics, xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

sys.stdout.reconfigure(encoding='utf-8')

# === CONFIG (matches Iiyama run) ===
BRAND = "Iiyama"
GA4_PROPERTY = "280127077"
META_ACCOUNT = "act_1438113836305522"
META_TOKEN = "EAAUHHYb8Sr4BQnjGwBGbWrVIZCk1p3ZBZBAZCFUcnPOJMv3uoEq9TFw3LIzVW1iDBz5uAQo8NoSiU7h9ofLM6uQup2r6z0I5gvZAfTZBvSFJi1JyP7QPp6QJZAxt3kxsOecmZAkkvCZBZAZBRwHfg9fQ5ooSPd4jClKRaPnZAH1MyS9tZBnylwX1GYSe0pQqAQIwEmwZDZD"
FEED_URL = "https://iiyama-sklep.pl/modules/pricewars2/xml/alias/facebook353re3534sdfdfdef.xml"
SA_KEY = "Input/gtm-prrvq3sf-mjyyy-b6b97b820015.json"

now = datetime.now()
y1ago = now - timedelta(days=365)
DATE_FROM = y1ago.strftime("%Y-%m-%d")
DATE_TO = now.strftime("%Y-%m-%d")

audit = {"brand": BRAND, "date_range": f"{DATE_FROM} to {DATE_TO}", "streams": {}, "timestamp": now.isoformat()}

print("=" * 70)
print(f"  DATA QUALITY AUDIT — {BRAND}")
print(f"  Date Range: {DATE_FROM} to {DATE_TO}")
print("=" * 70)

# ============================================================
# STREAM 1: PRODUCT FEED
# ============================================================
print("\n[1/4] Fetching Product Feed...")
try:
    r = requests.get(FEED_URL, timeout=30)
    r.encoding = 'utf-8'
    root = ET.fromstring(r.content)
    
    # Find items (RSS or custom format)
    items_el = root.findall('.//item') or root.findall('.//{http://base.google.com/ns/1.0}item')
    if not items_el:
        # Try products/product
        items_el = root.findall('.//product')
    
    ns = {'g': 'http://base.google.com/ns/1.0'}
    
    feed_items = []
    for item in items_el:
        def get_text(tag):
            # Try with namespace
            el = item.find(f"g:{tag}", ns)
            if el is None:
                el = item.find(tag)
            return el.text.strip() if el is not None and el.text else ""
        
        price_str = get_text("price") or get_text("sale_price") or "0"
        price = float(''.join(c for c in price_str if c.isdigit() or c == '.') or '0')
        
        feed_items.append({
            "id": get_text("id"),
            "title": get_text("title")[:80],
            "price": price,
            "link": get_text("link"),
            "category": get_text("google_product_category") or get_text("product_type"),
            "brand": get_text("brand"),
        })
    
    # Analysis
    prices = [i["price"] for i in feed_items if i["price"] > 0]
    null_ids = sum(1 for i in feed_items if not i["id"])
    null_titles = sum(1 for i in feed_items if not i["title"])
    null_links = sum(1 for i in feed_items if not i["link"])
    null_cats = sum(1 for i in feed_items if not i["category"])
    
    feed_report = {
        "row_count": len(feed_items),
        "with_price": len(prices),
        "price_range": f"{min(prices):.2f} - {max(prices):.2f} PLN" if prices else "N/A",
        "price_median": f"{statistics.median(prices):.2f} PLN" if prices else "N/A",
        "price_mean": f"{statistics.mean(prices):.2f} PLN" if prices else "N/A",
        "null_ids": null_ids,
        "null_titles": null_titles,
        "null_links": null_links,
        "null_categories": null_cats,
        "sample_categories": list(set(i["category"] for i in feed_items[:50] if i["category"]))[:5],
        "issues": []
    }
    if null_ids > 0: feed_report["issues"].append(f"{null_ids} products with no ID")
    if null_links > 0: feed_report["issues"].append(f"{null_links} products with no link")
    
    audit["streams"]["feed"] = feed_report
    print(f"  {len(feed_items)} products | price: {feed_report['price_range']}")
    
except Exception as e:
    print(f"  ERROR: {e}")
    audit["streams"]["feed"] = {"error": str(e), "row_count": 0}

# ============================================================
# STREAM 2: GA4 LANDING PAGES
# ============================================================
print("\n[2/4] Fetching GA4 Landing Pages...")
try:
    creds = service_account.Credentials.from_service_account_file(SA_KEY)
    client = BetaAnalyticsDataClient(credentials=creds)
    
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[DateRange(start_date=DATE_FROM, end_date=DATE_TO)],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="purchaseRevenue"),
            Metric(name="transactions"),
        ],
        limit=10000
    )
    
    response = client.run_report(request=request)
    
    ga4_lp = []
    for row in response.rows:
        lp = row.dimension_values[0].value
        sessions = int(row.metric_values[0].value)
        revenue = float(row.metric_values[1].value)
        transactions = int(row.metric_values[2].value)
        ga4_lp.append({"url": lp, "sessions": sessions, "revenue": revenue, "transactions": transactions})
    
    total_sess = sum(r["sessions"] for r in ga4_lp)
    total_rev = sum(r["revenue"] for r in ga4_lp)
    total_trans = sum(r["transactions"] for r in ga4_lp)
    with_rev = sum(1 for r in ga4_lp if r["revenue"] > 0)
    
    # URL quality
    product_urls = [r for r in ga4_lp if any(x in r["url"] for x in ["/p/", "/product/", ".html", "/monitor", "/akcesoria"])]
    
    ga4_lp_report = {
        "row_count": len(ga4_lp),
        "total_sessions": total_sess,
        "total_revenue": f"{total_rev:.2f} PLN",
        "total_transactions": total_trans,
        "pages_with_revenue": with_rev,
        "conversion_rate": f"{(total_trans/total_sess*100):.2f}%" if total_sess > 0 else "N/A",
        "top_5_by_sessions": sorted(ga4_lp, key=lambda x: x["sessions"], reverse=True)[:5],
        "top_5_by_revenue": sorted(ga4_lp, key=lambda x: x["revenue"], reverse=True)[:5],
        "issues": []
    }
    
    audit["streams"]["ga4_lp"] = ga4_lp_report
    print(f"  {len(ga4_lp)} landing pages | {total_sess} sessions | {total_rev:.0f} PLN revenue")

except Exception as e:
    print(f"  ERROR: {e}")
    audit["streams"]["ga4_lp"] = {"error": str(e), "row_count": 0}

# ============================================================
# STREAM 3: GA4 ITEMS
# ============================================================
print("\n[3/4] Fetching GA4 Items...")
try:
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[DateRange(start_date=DATE_FROM, end_date=DATE_TO)],
        dimensions=[Dimension(name="itemId")],
        metrics=[
            Metric(name="itemsViewed"),
            Metric(name="itemRevenue"),
            Metric(name="itemsPurchased"),
        ],
        limit=10000
    )
    
    response = client.run_report(request=request)
    
    ga4_items = []
    for row in response.rows:
        item_id = row.dimension_values[0].value
        views = int(row.metric_values[0].value)
        revenue = float(row.metric_values[1].value)
        purchases = int(row.metric_values[2].value)
        ga4_items.append({"id": item_id, "views": views, "revenue": revenue, "purchases": purchases})
    
    total_views = sum(i["views"] for i in ga4_items)
    total_item_rev = sum(i["revenue"] for i in ga4_items)
    total_purch = sum(i["purchases"] for i in ga4_items)
    with_purch = sum(1 for i in ga4_items if i["purchases"] > 0)
    
    ga4_items_report = {
        "row_count": len(ga4_items),
        "total_views": total_views,
        "total_revenue": f"{total_item_rev:.2f} PLN",
        "total_purchases": total_purch,
        "items_with_purchases": with_purch,
        "items_view_only": len(ga4_items) - with_purch,
        "top_5_by_revenue": sorted(ga4_items, key=lambda x: x["revenue"], reverse=True)[:5],
        "issues": []
    }
    
    # Cross-check: does item revenue ~ LP revenue?
    rev_diff = abs(total_item_rev - total_rev) / max(total_rev, 1) * 100
    ga4_items_report["revenue_vs_lp_diff"] = f"{rev_diff:.1f}%"
    if rev_diff > 20:
        ga4_items_report["issues"].append(f"Revenue mismatch vs LP: {rev_diff:.1f}% difference")
    
    audit["streams"]["ga4_items"] = ga4_items_report
    print(f"  {len(ga4_items)} items | {total_purch} purchases | {total_item_rev:.0f} PLN revenue")

except Exception as e:
    print(f"  ERROR: {e}")
    audit["streams"]["ga4_items"] = {"error": str(e), "row_count": 0}

# ============================================================
# STREAM 4: META ADS
# ============================================================
print("\n[4/4] Fetching Meta Ads...")
try:
    url = f"https://graph.facebook.com/v21.0/{META_ACCOUNT}/insights"
    params = {
        "access_token": META_TOKEN,
        "level": "ad",
        "fields": "ad_id,ad_name,spend,actions,action_values,impressions,clicks,cpc,cpm,reach",
        "time_range": json.dumps({"since": DATE_FROM, "until": DATE_TO}),
        "limit": 500
    }
    
    r = requests.get(url, params=params)
    data = r.json()
    
    if "error" in data:
        raise Exception(data["error"].get("message", str(data["error"])))
    
    ads = data.get("data", [])
    
    def extract_action(actions, action_type):
        if not isinstance(actions, list): return 0
        match = next((a for a in actions if a.get("action_type") == action_type), None)
        return float(match["value"]) if match else 0
    
    meta_items = []
    for ad in ads:
        spend = float(ad.get("spend", 0))
        purchases = extract_action(ad.get("actions", []), "offsite_conversion.fb_pixel_purchase") or \
                   extract_action(ad.get("actions", []), "purchase")
        purchase_value = extract_action(ad.get("action_values", []), "offsite_conversion.fb_pixel_purchase") or \
                        extract_action(ad.get("action_values", []), "purchase")
        roas = purchase_value / spend if spend > 0 else 0
        
        meta_items.append({
            "ad_id": ad.get("ad_id"),
            "ad_name": ad.get("ad_name", "")[:60],
            "spend": spend,
            "purchases": purchases,
            "purchase_value": purchase_value,
            "roas": roas,
            "impressions": int(ad.get("impressions", 0)),
            "clicks": int(ad.get("clicks", 0)),
        })
    
    total_spend = sum(i["spend"] for i in meta_items)
    total_meta_rev = sum(i["purchase_value"] for i in meta_items)
    total_meta_purch = sum(i["purchases"] for i in meta_items)
    blended_roas = total_meta_rev / total_spend if total_spend > 0 else 0
    ads_profitable = sum(1 for i in meta_items if i["roas"] > 1)
    ads_with_sales = sum(1 for i in meta_items if i["purchases"] > 0)
    
    # ROAS distribution
    roas_vals = [i["roas"] for i in meta_items if i["spend"] > 0]
    
    meta_report = {
        "row_count": len(meta_items),
        "total_spend": f"{total_spend:.2f} PLN",
        "total_revenue": f"{total_meta_rev:.2f} PLN",
        "total_purchases": total_meta_purch,
        "blended_roas": f"{blended_roas:.2f}x",
        "ads_with_sales": ads_with_sales,
        "ads_profitable": ads_profitable,
        "ads_unprofitable": len(meta_items) - ads_profitable,
        "median_roas": f"{statistics.median(roas_vals):.2f}x" if roas_vals else "N/A",
        "top_5_by_roas": sorted(meta_items, key=lambda x: x["roas"], reverse=True)[:5],
        "bottom_5_spend_no_sales": sorted(
            [i for i in meta_items if i["purchases"] == 0 and i["spend"] > 0],
            key=lambda x: x["spend"], reverse=True
        )[:5],
        "has_pagination": "paging" in data and "next" in data.get("paging", {}),
        "issues": []
    }
    
    if meta_report["has_pagination"]:
        meta_report["issues"].append("WARNING: Pagination detected! Not all ads fetched (>500)")
    
    audit["streams"]["meta_ads"] = meta_report
    print(f"  {len(meta_items)} ads | {total_spend:.0f} PLN spend | ROAS: {blended_roas:.2f}x")

except Exception as e:
    print(f"  ERROR: {e}")
    audit["streams"]["meta_ads"] = {"error": str(e), "row_count": 0}

# ============================================================
# CROSS-STREAM ANALYSIS
# ============================================================
print("\n" + "=" * 70)
print("  CROSS-STREAM ANALYSIS")
print("=" * 70)

cross = {}

# Feed vs GA4 Items overlap
if "feed" in audit["streams"] and "ga4_items" in audit["streams"]:
    feed_ids = set(i["id"] for i in feed_items if i["id"])
    ga4_ids = set(i["id"] for i in ga4_items if i["id"])
    overlap = feed_ids & ga4_ids
    cross["feed_ga4_items_overlap"] = {
        "feed_products": len(feed_ids),
        "ga4_items": len(ga4_ids),
        "matched": len(overlap),
        "match_rate": f"{len(overlap)/max(len(ga4_ids),1)*100:.1f}%",
        "ga4_only": len(ga4_ids - feed_ids),
        "feed_only": len(feed_ids - ga4_ids),
    }
    print(f"\n  Feed <-> GA4 Items:")
    print(f"    Feed products:  {len(feed_ids)}")
    print(f"    GA4 items:      {len(ga4_ids)}")
    print(f"    Matched:        {len(overlap)} ({len(overlap)/max(len(ga4_ids),1)*100:.1f}%)")

# Feed URL vs GA4 LP URL overlap
if "feed" in audit["streams"] and "ga4_lp" in audit["streams"]:
    def norm_url(url):
        if not url: return ""
        return url.lower().replace("https://", "").replace("http://", "").replace("www.", "").split("?")[0].rstrip("/")
    
    feed_urls = set(norm_url(i["link"]) for i in feed_items if i["link"])
    ga4_urls = set(norm_url(r["url"]) for r in ga4_lp if r["url"])
    url_overlap = feed_urls & ga4_urls
    cross["feed_ga4_lp_url_overlap"] = {
        "feed_urls": len(feed_urls),
        "ga4_lp_urls": len(ga4_urls),
        "matched": len(url_overlap),
        "match_rate": f"{len(url_overlap)/max(len(feed_urls),1)*100:.1f}%",
    }
    print(f"\n  Feed URLs <-> GA4 LP URLs (normalized):")
    print(f"    Feed URLs:      {len(feed_urls)}")
    print(f"    GA4 LP URLs:    {len(ga4_urls)}")
    print(f"    Matched:        {len(url_overlap)} ({len(url_overlap)/max(len(feed_urls),1)*100:.1f}%)")

audit["cross_stream"] = cross

# Save full audit
with open("data_quality_audit.json", "w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2, ensure_ascii=False, default=str)

print(f"\n  Full audit saved to data_quality_audit.json")

# ============================================================
# VERDICT
# ============================================================
print("\n" + "=" * 70)
print("  DATA QUALITY VERDICT")
print("=" * 70)

all_issues = []
for stream_name, stream_data in audit["streams"].items():
    issues = stream_data.get("issues", [])
    all_issues.extend(issues)
    
print(f"\n  Total streams:  4")
print(f"  Total issues:   {len(all_issues)}")
for issue in all_issues:
    print(f"    [!] {issue}")

if not all_issues:
    print("\n  VERDICT: CLEAN & TRUSTWORTHY")
elif all("CRITICAL" not in i for i in all_issues):
    print("\n  VERDICT: ACCEPTABLE WITH CAVEATS")
else:
    print("\n  VERDICT: REQUIRES ATTENTION")

print("=" * 70)
