
import pandas as pd
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

import src.business_logic_layer as bl
from src.data_loader import load_ga4_csv, parse_product_feed_xml

BRAND = "Iiyama"
INPUT_DIR = "Input/Iiyama"

def debug_keys():
    print("--- Loading Data ---")
    feed_path = os.path.join(INPUT_DIR, f"{BRAND.lower()}_product_feed.xml")
    feed_df = parse_product_feed_xml(feed_path)
    
    lp_path = os.path.join(INPUT_DIR, f"{BRAND.lower()}_ga4_lp.csv")
    lp_df = load_ga4_csv(lp_path)
    
    # Target Item
    target_id = '1252'
    
    # 1. Feed Key
    feed_item = feed_df[feed_df['feed_id'] == target_id]
    if feed_item.empty:
        print(f"Item {target_id} not found in feed")
        return
    
    raw_link = feed_item.iloc[0]['feed_link']
    norm_url = bl.normalize_url(raw_link)
    norm_url_path = norm_url.replace('https://', '').replace('http://', '').split('/', 1)[-1] if raw_link else ''
    
    # Apply logic from main.py fix
    path_key_feed = f"/{norm_url_path}" if norm_url_path and not norm_url_path.startswith('/') else norm_url_path
    
    print(f"\n[FEED] ID: {target_id}")
    print(f"Raw Link: '{raw_link}'")
    print(f"Norm URL Path (n8n style): '{norm_url_path}'")
    print(f"Calculated Path Key: '{path_key_feed}'")
    print(f"Bytes: {path_key_feed.encode('utf-8')}")

    # 2. LP Key
    # search for this path in LP
    # extract_path logic
    lp_df['path_key'] = lp_df['Landing page'].apply(bl.extract_path)
    
    # Try validation
    match = lp_df[lp_df['path_key'] == path_key_feed]
    print(f"\n[LP] Matches found: {len(match)}")
    
    if len(match) == 0:
        print("No exact match. Searching for partial...")
        # fuzzy search
        partial = lp_df[lp_df['path_key'].str.contains('1252', na=False)]
        if not partial.empty:
            print("Found partial matches (1252):")
            for _, row in partial.head().iterrows():
                pk = row['path_key']
                print(f"LP Key: '{pk}'")
                print(f"Bytes:  {pk.encode('utf-8')}")
                if pk == path_key_feed:
                    print("  -> EQUAL! (Why didn't it match?)")
                else:
                    print("  -> NOT EQUAL")
                    # Compare chars
                    common_len = min(len(pk), len(path_key_feed))
                    for i in range(common_len):
                        if pk[i] != path_key_feed[i]:
                            print(f"     Difference at index {i}: '{pk[i]}' vs '{path_key_feed[i]}'")
                            break
                    if len(pk) != len(path_key_feed):
                        print(f"     Length mismatch: {len(pk)} vs {len(path_key_feed)}")

if __name__ == "__main__":
    debug_keys()
