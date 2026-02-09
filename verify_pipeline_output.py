
import pandas as pd
import os
import sys

def load_data(brand):
    path = os.path.join("Output", brand, f"{brand}_Growth_Opportunities.csv")
    if not os.path.exists(path):
        print(f"[ERROR] file not found: {path}")
        return None
    return pd.read_csv(path)

def analyze_iiyama(df):
    print("\nXXX COMPARISON REPORT XXX")
    print("1. Iiyama Sample")
    print("-" * 30)
    
    # Select sample rows
    # Star (P1)
    star = df[df['calc_priority'] == 1].head(1)
    # Dog (P8 or similar low priority)
    dog = df[df['calc_priority'] == 8].head(1)
    if dog.empty: dog = df[df['calc_priority'].isin([4, 8])].head(1)
    
    # Landing Page (is_product=False)
    lp = df[~df['is_product']].head(1)
    
    cols = ['feed_title', 'calc_net_price', 'base_gross_margin', 'calc_price_cluster', 'calc_bid_cap']
    
    sample = pd.concat([star, dog, lp])
    print(sample[cols].to_string(index=False))
    
    print("\n[LOGIC CHECK] Cluster Overlap (Iiyama)")
    # Verify no cluster name exists in multiple margin groups
    # Group by cluster name and count unique margin groups
    cluster_margin_counts = df.groupby('calc_price_cluster')['base_gross_margin'].nunique()
    overlaps = cluster_margin_counts[cluster_margin_counts > 1]
    
    if not overlaps.empty:
        print(f"FAIL! Clusters crossing margin groups: {overlaps.index.tolist()}")
    else:
        print("PASS: No clusters cross margin groups.")

    print("\n[LOGIC CHECK] Zero Trap (Iiyama)")
    # Check if any active LP has price 0.0
    # Active LP = is_product=False AND (meta_spend > 0 OR ga4lp_sessions > 100)
    active_lps = df[
        (~df['is_product']) & 
        ((df['meta_spend'] > 0) | (df['ga4lp_sessions'] > 100))
    ]
    zeros = active_lps[active_lps['calc_gross_price'] == 0]
    
    if not zeros.empty:
        print(f"FAIL! Found {len(zeros)} active LPs with 0.0 price.")
        print(zeros[['feed_title', 'norm_url', 'meta_spend', 'ga4lp_sessions']].head())
    else:
        print("PASS: No active LPs with 0.0 price.")

def analyze_koszulkowy(df):
    print("\n2. Koszulkowy Sample")
    print("-" * 30)
    
    # Sort by price to find High/Low ticket
    df_sorted = df.sort_values('calc_gross_price', ascending=False)
    
    high = df_sorted.head(1)
    low = df_sorted[df_sorted['calc_gross_price'] > 0].tail(1)
    # Landing Page
    lp = df[~df['is_product']].head(1)
    
    cols = ['feed_title', 'calc_net_price', 'calc_price_cluster', 'calc_bid_cap']
    sample = pd.concat([high, low, lp])
    print(sample[cols].to_string(index=False))
    
    print("\n[GHOST HUNT] Checking 'Beze Mnie Ten Przybytek' (ID 35946)")
    ghost_hunt = df[df['feed_title'].astype(str).str.contains('35946') | df['norm_url'].astype(str).str.contains('35946')]
    if not ghost_hunt.empty:
        print(ghost_hunt[['feed_title', 'calc_net_price', 'calc_gross_price', 'is_product', 'feed_id']].to_string())
    else:
        print("Target product not found in output!")

def main():
    print("Loading data...")
    iiyama = load_data("Iiyama")
    koszulkowy = load_data("Koszulkowy")
    
    if iiyama is not None:
        analyze_iiyama(iiyama)
        
    if koszulkowy is not None:
        analyze_koszulkowy(koszulkowy)

if __name__ == "__main__":
    main()
