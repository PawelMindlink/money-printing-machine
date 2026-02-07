
import pandas as pd
import xml.etree.ElementTree as ET
import urllib.parse
import os

INPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Input"
BRANDS = ["Bushido", "Iiyama", "Koszulkowy"]

def normalize_url(url):
    if not isinstance(url, str): return ""
    try:
        url = url.split("?")[0].replace("www.", "").replace("https://", "").replace("http://", "").rstrip("/")
        return url
    except: return ""

def analyze_brand(brand):
    print(f"\n>>> ANALYZING [{brand}] <<<")
    base_path = os.path.join(INPUT_DIR, brand)
    
    files = {
        "ga4_items": os.path.join(base_path, "ga4_items.csv"),
        "ga4_lp": os.path.join(base_path, "ga4_lp.csv"),
        "meta": os.path.join(base_path, "meta_ads.csv"),
        "feed": os.path.join(base_path, "product_feed.xml")
    }
    
    data = {}
    report = {"Brand": brand}

    # 1. FEED
    try:
        context = ET.iterparse(files['feed'], events=('end',))
        feed_items = []
        count = 0
        for event, elem in context:
            if elem.tag.endswith('item'):
                i_id, i_link, i_cat = "N/A", "N/A", "N/A"
                for child in elem:
                    if 'id' in child.tag: i_id = child.text
                    elif 'link' in child.tag: i_link = child.text
                    elif 'product_type' in child.tag: i_cat = child.text
                feed_items.append({'id': str(i_id).strip(), 'link': i_link, 'cat': i_cat})
                count += 1
                elem.clear()
                if count > 2000: break # Sample size
        
        df_feed = pd.DataFrame(feed_items)
        df_feed['norm_url'] = df_feed['link'].apply(normalize_url)
        data['feed'] = df_feed
        report['Feed_Count'] = len(df_feed)
        report['Has_Category'] = df_feed['cat'].nunique() > 1
    except Exception as e:
        report['Feed_Status'] = f"Error: {str(e)[:50]}"

    # 2. GA4 ITEMS (Check ID Match)
    try:
        # Detect header
        h_row = 0
        with open(files['ga4_items'], 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if "Item ID" in line or "Item name" in line: h_row = i; break
        
        df_ga4 = pd.read_csv(files['ga4_items'], skiprows=h_row)
        if 'Item ID' in df_ga4.columns:
            df_ga4['Item ID'] = df_ga4['Item ID'].astype(str).str.strip()
            data['ga4'] = df_ga4
            
            # MATCH
            if 'feed' in data:
                common = set(df_ga4['Item ID']).intersection(set(data['feed']['id']))
                report['GA4_ID_Match_Count'] = len(common)
                report['GA4_ID_Match_Pct'] = round(len(common) / len(df_ga4) * 100, 1)
        else:
            report['GA4_Status'] = "No 'Item ID' column"
    except Exception as e:
        report['GA4_Status'] = f"Error: {str(e)[:50]}"

    # 3. META ADS (Check URL Match)
    try:
        df_meta = pd.read_csv(files['meta'])
        # Identify URL col
        url_col = next((c for c in df_meta.columns if "Link" in c or "URL" in c or "Landing" in c), None)
        
        if url_col:
            df_meta = df_meta.dropna(subset=[url_col])
            df_meta['norm_url'] = df_meta[url_col].apply(normalize_url)
            data['meta'] = df_meta
            
            # MATCH
            if 'feed' in data:
                meta_urls = set(df_meta['norm_url'])
                feed_urls = set(data['feed']['norm_url'])
                common = meta_urls.intersection(feed_urls)
                report['Meta_URL_Match_Count'] = len(common)
                report['Meta_URL_Match_Pct'] = round(len(common) / len(df_meta) * 100, 1)
        else:
             report['Meta_Status'] = "No URL column found"
    except Exception as e:
        report['Meta_Status'] = f"Error: {str(e)[:50]}"

    return report

print("--- UNIVERSAL FEASIBILITY CHECK ---")
results = []
for b in BRANDS:
    results.append(analyze_brand(b))

print("\n--- SUMMARY ---")
print(pd.DataFrame(results).to_string())
