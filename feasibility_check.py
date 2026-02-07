
import pandas as pd
import xml.etree.ElementTree as ET
import urllib.parse
import os
import re

# Paths
INPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Input"

# Files (Best guess based on names)
GA4_ITEM_FILE = os.path.join(INPUT_DIR, "Bushido Item Breakdown GA4.csv")
META_FILE = os.path.join(INPUT_DIR, "Export-Raport.csv")
XML_FILE = os.path.join(INPUT_DIR, "facebookads_16dafb891c459c40b5bb164a 1.txt")

def normalize_url(url):
    if not isinstance(url, str):
        return ""
    try:
        # Remove query params
        url = url.split("?")[0]
        # Remove www.
        url = url.replace("www.", "")
        # Remove trailing slash
        url = url.rstrip("/")
        # Remove protocol
        url = url.replace("https://", "").replace("http://", "")
        return url
    except:
        return ""

def analyze_feasibility():
    print("--- FEASIBILITY REPORT ---")
    
    # 1. LOAD GA4 ITEMS
    print(f"\n[1] Loading GA4 Items from {os.path.basename(GA4_ITEM_FILE)}...")
    try:
        # Detect header row
        header_row = 0
        with open(GA4_ITEM_FILE, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if "Item ID" in line:
                    header_row = i
                    break
        
        print(f"    Detected Header Row at index: {header_row}")
        df_ga4 = pd.read_csv(GA4_ITEM_FILE, skiprows=header_row)
        print(f"    Loaded {len(df_ga4)} rows.")
        
        if 'Item ID' in df_ga4.columns:
            # Ensure ID is string for matching
            df_ga4['Item ID'] = df_ga4['Item ID'].astype(str).str.strip()
            sample_ids = df_ga4['Item ID'].dropna().unique()[:5]
            print(f"    Sample Item IDs: {sample_ids}")
            
            # Check for revenue
            if 'Item revenue' in df_ga4.columns:
                total_rev = df_ga4['Item revenue'].sum()
                print(f"    Total Revenue in File: {total_rev}")
        else:
            print("    ERROR: 'Item ID' column not found in GA4 file.")

    except Exception as e:
        print(f"    ERROR loading GA4: {e}")

    # 2. LOAD META ADS
    print(f"\n[2] Loading Meta Ads from {os.path.basename(META_FILE)}...")
    try:
        df_meta = pd.read_csv(META_FILE)
        print(f"    Loaded {len(df_meta)} rows.")
        
        url_col = 'Link (ad settings)' 
        if url_col in df_meta.columns:
            print(f"    Found URL Column: '{url_col}'")
            # Filter valid URLs
            df_meta = df_meta.dropna(subset=[url_col])
            df_meta['norm_url'] = df_meta[url_col].apply(normalize_url)
            
            unique_urls = df_meta['norm_url'].unique()
            print(f"    Unique Landing Pages: {len(unique_urls)}")
            print(f"    Sample URLs: {unique_urls[:5]}")
        else:
            print(f"    ERROR: Column '{url_col}' not found.")
            print(f"    Columns: {df_meta.columns.tolist()}")

    except Exception as e:
        print(f"    ERROR loading Meta: {e}")

    # 3. LOAD XML FEED
    print(f"\n[3] Parsing XML Feed from {os.path.basename(XML_FILE)}...")
    try:
        context = ET.iterparse(XML_FILE, events=('end',))
        items_checked = 0
        feed_data = []
        ns = {'g': 'http://base.google.com/ns/1.0'}
        
        for event, elem in context:
            if elem.tag.endswith('item'):
                try:
                    # Namespace handling might be tricky with iterparse structure, trying both direct and find
                    # Usually iterparse gives element, we can find children
                    # Need to handle namespaces correctly or ignore them
                    
                    # Hacky way to find children regardless of namespace for robustness
                    item_id = "N/A"
                    link = "N/A"
                    cat = "N/A"
                    
                    for child in elem:
                        if 'id' in child.tag:
                            item_id = child.text
                        elif 'link' in child.tag:
                            link = child.text
                        elif 'product_type' in child.tag:
                            cat = child.text
                            
                    feed_data.append({'id': str(item_id).strip(), 'link': link, 'cat': cat})
                except Exception as e:
                    pass

                items_checked += 1
                elem.clear() # clear memory
                if items_checked >= 100: # Check more items
                    break
        
        print(f"    Checked {items_checked} XML items.")
        
        df_feed = pd.DataFrame(feed_data)
        if not df_feed.empty:
            df_feed['norm_url'] = df_feed['link'].apply(normalize_url)
            print(f"    Sample Feed Data:\n{df_feed.head(3)}")
            
            # CHECK FEASIBILITY
            print("\n--- JOIN ANALYSIS (Sample) ---")
            
            # Match IDs (GA4 <-> Feed)
            if 'df_ga4' in locals():
                ga4_ids = set(df_ga4['Item ID'].unique())
                feed_ids = set(df_feed['id'].unique())
                common = ga4_ids.intersection(feed_ids)
                print(f"    GA4 IDs in Feed (Sample Overlap): {len(common)} found in first 100 XML items.")
                if len(common) > 0:
                     print(f"    SUCCESS: ID match confirmed (e.g. {list(common)[0]})")
                else:
                     print(f"    WARNING: No overlap in first 100 items. (Expected if GA4 has top sellers matching items later in feed)")

            # Match URLs (Meta <-> Feed)
            if 'df_meta' in locals():
                meta_urls = set(df_meta['norm_url'].unique())
                feed_urls = set(df_feed['norm_url'].unique())
                common_urls = meta_urls.intersection(feed_urls)
                print(f"    Meta URLs in Feed (Sample Overlap): {len(common_urls)} found.")
        
    except Exception as e:
        print(f"    ERROR parsing XML: {e}")

if __name__ == "__main__":
    analyze_feasibility()
