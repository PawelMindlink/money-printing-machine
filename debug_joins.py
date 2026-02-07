
import pandas as pd
import xml.etree.ElementTree as ET
import os

INPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Input"
BRANDS = ["Bushido", "Iiyama", "Koszulkowy"]

def get_feed_samples(path):
    ids, links = [], []
    try:
        context = ET.iterparse(path, events=('end',))
        for event, elem in context:
            if elem.tag.endswith('item'):
                for child in elem:
                    if 'id' in child.tag: ids.append(child.text)
                    elif 'link' in child.tag: links.append(child.text)
                elem.clear()
                if len(ids) > 5: break
    except: pass
    return ids, links

def debug_brand(brand):
    print(f"\n>>> DEBUG [{brand}] <<<")
    base = os.path.join(INPUT_DIR, brand)
    
    # 1. FEED KEYS
    feed_ids, feed_links = get_feed_samples(os.path.join(base, "product_feed.xml"))
    print(f"FEED IDs: {feed_ids}")
    print(f"FEED URLs: {[l[:60] for l in feed_links]}")

    # 2. GA4 KEYS
    try:
        # Detect header
        h_row = 0
        with open(os.path.join(base, "ga4_items.csv"), 'r', errors='ignore') as f:
            for i, line in enumerate(f):
                if "Item ID" in line: h_row = i; break
        
        df = pd.read_csv(os.path.join(base, "ga4_items.csv"), skiprows=h_row, nrows=5)
        if 'Item ID' in df.columns:
            print(f"GA4 IDs: {df['Item ID'].tolist()}")
        else:
            print("GA4 IDs: Column 'Item ID' not found")
    except: print("GA4: Error reading")

    # 3. META KEYS
    try:
        df = pd.read_csv(os.path.join(base, "meta_ads.csv"), nrows=5)
        url_col = next((c for c in df.columns if "Link" in c or "Landing" in c), None)
        if url_col:
            print(f"META URLs: {df[url_col].dropna().tolist()}")
        else:
            print("META URLs: Column not found")
    except: print("META: Error reading")

for b in BRANDS:
    debug_brand(b)
