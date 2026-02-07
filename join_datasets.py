
import pandas as pd
import os

# --- CONFIG ---
BASE_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine"
OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
BRANDS = ["Bushido", "Iiyama", "Koszulkowy"]

def join_data():
    for brand in BRANDS:
        print(f"\n[{brand}] JOINING DATASETS...")
        path = os.path.join(OUTPUT_DIR, brand, "Normalized")
        
        # Load
        try:
            feed = pd.read_csv(os.path.join(path, "feed_clean.csv"), dtype={'id': str})
            ga4 = pd.read_csv(os.path.join(path, "ga4_items_clean.csv"), dtype={'Item ID': str})
            meta = pd.read_csv(os.path.join(path, "meta_ads_clean.csv"))
        except FileNotFoundError as e:
            print(f"  Skipping {brand} (Missing file: {e})")
            continue

        # 1. PREPARE FEED (ANCHOR)
        # Ensure unique IDs
        master = feed.drop_duplicates(subset=['id']).copy()
        print(f"  Feed Items: {len(master)}")

        # 2. JOIN GA4 (on Item ID)
        # GA4 cols to keep
        ga4_cols = ['Item ID', 'Item revenue', 'Items purchased', 'Items viewed']
        # Filter strictly
        ga4_clean = ga4[ga4['Item ID'].isin(master['id'])]
        
        master = master.merge(ga4[ga4_cols], left_on='id', right_on='Item ID', how='left')
        master.drop(columns=['Item ID'], inplace=True)
        
        matches_ga4 = master['Item revenue'].notna().sum()
        print(f"  GA4 Matches: {matches_ga4} products")

        # 3. JOIN META (on URL)
        # Count items per URL for Spend Split
        url_counts = master['norm_url'].value_counts()
        master['items_sharing_url'] = master['norm_url'].map(url_counts).fillna(1)
        
        # Merge
        meta_cols = ['norm_url', 'Amount spent (PLN)', 'Purchases', 'Purchases conversion value']
        master = master.merge(meta[meta_cols], on='norm_url', how='left')
        
        # Split Spend & Revenue by Item Count logic (Pro-rated)
        # If 3 items share a URL, we divide spend by 3 to estimate per-item cost
        # (This is a heuristic, better than duplication)
        master['ad_spend_prorated'] = master['Amount spent (PLN)'] / master['items_sharing_url']
        master['meta_rev_prorated'] = master['Purchases conversion value'] / master['items_sharing_url']
        
        matches_meta = master['Amount spent (PLN)'].notna().sum()
        print(f"  Meta Matches: {matches_meta} products")

        # 4. SAVE
        final_path = os.path.join(OUTPUT_DIR, brand, "Master_Report.csv")
        master.to_csv(final_path, index=False)
        print(f"  SAVED: {final_path}")

if __name__ == "__main__":
    join_data()
