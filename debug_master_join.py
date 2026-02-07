
import pandas as pd
import os

BASE_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Output"
BRANDS = ["Bushido", "Iiyama", "Koszulkowy"]

def debug():
    for brand in BRANDS:
        print(f"\n[{brand}] DEBUG KEYS")
        path = os.path.join(BASE_DIR, brand, "Normalized")
        try:
            feed = pd.read_csv(os.path.join(path, "feed_clean.csv"), dtype=str)
            ga4 = pd.read_csv(os.path.join(path, "ga4_items_clean.csv"), dtype=str)
            meta = pd.read_csv(os.path.join(path, "meta_ads_clean.csv"), dtype=str)
            
            print(f"  Feed IDs (Head): {feed['id'].head(3).tolist()}")
            if 'Item ID' in ga4.columns:
                 print(f"  GA4 IDs (Head): {ga4['Item ID'].head(3).tolist()}")
            else:
                 print(f"  GA4 Cols: {ga4.columns.tolist()}")

            print(f"  Feed URLs (Head): {feed['norm_url'].head(3).tolist()}")
            print(f"  Meta URLs (Head): {meta['norm_url'].head(3).tolist()}")
            
            # Check overlap
            if 'Item ID' in ga4.columns:
                common_id = set(feed['id']).intersection(set(ga4['Item ID']))
                print(f"  ID Overlap: {len(common_id)}")
            
            common_url = set(feed['norm_url']).intersection(set(meta['norm_url']))
            print(f"  URL Overlap: {len(common_url)}")

        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    debug()
