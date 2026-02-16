import pandas as pd
import json
import os
import sys 
import business_logic_layer as bl
from data_loader import parse_product_feed_xml

# ============================================================================
# CONFIG & UTILS
# ============================================================================

def load_config(path='business_logic.json'):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ============================================================================
# PROCESS 1: AD LEVEL ANALYSIS (Enriched with Feed)
# ============================================================================

def run_ad_analysis(brand, input_dir, output_dir):
    print(f"\n>>> Running Process 1: Ad-Level Analysis for {brand}")
    brand_l = brand.lower()
    
    # 1. Load Logic
    logic = load_config()
    client_conf = next((c for c in logic['clients'] if c['name'].lower() == brand_l), {})
    default_margin = client_conf.get('margin_config', {}).get('default_rate', 0.10) # FIX: Use correct path
    vat_rate = client_conf.get('vat_rate', 0.23)
    margin_cfg = client_conf.get('margin_config', {})
    category_overrides = margin_cfg.get('category_overrides', [])

    # 2. Load Feed (for accurate Margin & Price Cluster)
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    feed_df = parse_product_feed_xml(feed_path)
    
    if not feed_df.empty:
        print(f"Loaded Feed: {len(feed_df)} products.")
        # Prepare for Join
        feed_df['norm_url'] = feed_df['norm_url'].astype(str)
        # Drop duplicates on URL to prevent fan-out (keep first product for that URL)
        feed_df = feed_df.drop_duplicates(subset=['norm_url'])
    else:
        print("Warning: Feed empty. Margins will fallback to default.")

    # 3. Load Meta Ads
    ads_path = os.path.join(input_dir, brand, f"{brand_l}_meta_ads.csv")
    if not os.path.exists(ads_path):
        print(f"Error: Meta Ads file not found: {ads_path}")
        return

    df = pd.read_csv(ads_path)
    
    # Map Columns (Strictly what user asked for + necessities)
    col_map = {
        'Ad name': 'meta_ad_name',
        'Ad ID': 'meta_ad_id',
        'Campaign name': 'meta_campaign_name',
        'Ad set name': 'meta_adset_name',
        'Amount spent (PLN)': 'meta_spend', 
        'Amount spent': 'meta_spend',
        'Purchase ROAS (return on ad spend)': 'meta_roas',
        'Purchase ROAS': 'meta_roas',
        'Purchases': 'meta_purchases',
        'Conversion value': 'meta_revenue',
        'Link (ad settings)': 'meta_link', # Crucial for joining
    }
    
    df.rename(columns=lambda x: next((v for k, v in col_map.items() if k in x), x), inplace=True)
    
    # Cleaning
    df = df.loc[:, ~df.columns.duplicated()] # Dedup columns
    
    num_cols = ['meta_spend', 'meta_revenue', 'meta_purchases']
    for c in num_cols:
        if c not in df.columns: 
            # Try fuzzy find
            fuzzy = next((col for col in df.columns if col.replace(' ', '').lower() in c.replace('_', '')), None)
            if fuzzy: df.rename(columns={fuzzy: c}, inplace=True)
            else: df[c] = 0
            
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        
    # 4. JOIN WITH FEED (to get Margin Group & Price Cluster)
    if 'meta_link' in df.columns:
        df['norm_url'] = df['meta_link'].apply(bl.normalize_url)
        
        if not feed_df.empty:
            # Join
            df = pd.merge(df, feed_df[['norm_url', 'feed_category', 'feed_price_str', 'feed_link']], on='norm_url', how='left')
    else:
        print("Warning: 'Link (ad settings)' column missing. Cannot join with Feed.")
        df['feed_category'] = 'Unknown'
        df['feed_price_str'] = '0'
        df['feed_link'] = ''

    # 5. CALCULATIONS
    
    # A. Margin
    # Prepare row for calculate_gross_margin (expects 'category', 'price')
    df['category'] = df.get('feed_category', 'Unknown')
    df['product_type'] = df.get('feed_product_type', '')
    df['price'] = df.get('feed_price_str', '0')
    
    df['base_gross_margin'] = df.apply(lambda row: bl.calculate_gross_margin(row, default_margin, category_overrides), axis=1)
    
    # B. Price Cluster
    # Parse price to numeric
    df['price_numeric'] = pd.to_numeric(df['price'].astype(str).str.replace(' PLN', '').str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    
    # We need to assign clusters based on the GROUP (Margin) logic
    df['calc_price_cluster'] = 'Other'
    for margin in df['base_gross_margin'].unique():
        mask = df['base_gross_margin'] == margin
        if mask.values.sum() > 0:
            # We use the business logic specific to this subset
            subset = df.loc[mask].copy()
            clusters = bl.assign_price_cluster(subset)
            df.loc[mask, 'calc_price_cluster'] = clusters

    # C. Profitability (Ad Level)
    df['calc_contribution_profit'] = df.apply(lambda row: bl.calculate_contribution_profit(
        row['meta_revenue'], vat_rate, row['base_gross_margin'], row['meta_spend']
    ), axis=1)
    
    # D. New Metrics (Requested by User)
    df['calc_net_price'] = df['price_numeric'] / (1 + vat_rate)
    df['calc_bid_cap'] = df['calc_net_price'] * df['base_gross_margin']
    df['calc_cost_cap'] = df['calc_bid_cap'] * 0.7
    
    # ROAS Metrics
    df['calc_critical_roas'] = df['base_gross_margin'].apply(lambda m: bl.calculate_critical_roas(vat_rate, m))
    df['calc_scaling_roas'] = df['base_gross_margin'].apply(lambda m: bl.calculate_scaling_roas(vat_rate, m))
    
    # E. Action Logic
    def decide_action(row):
        profit = row['calc_contribution_profit']
        spend = row['meta_spend']
        # Use calculated ROAS or clean Meta ROAS
        roas = row['meta_revenue'] / spend if spend > 0 else 0
        
        # 1. Proven Winner (Profit > 0)
        # "Proof of Profitability"
        if profit > 0: return "COPY (PROFIT)"
        
        # 2. Potential Winner (High ROAS)
        # Even if profit < 0 (maybe low volume), if ROAS is healthy, it's scalable.
        if roas >= row['calc_critical_roas'] and spend > 0: return "COPY (ROAS)"
        
        # 3. Proven Loser
        # If we spent enough to know it's bad. 
        # Threshold: Spend > 2x Bid Cap (or generic 50 PLN if no Bid Cap)
        threshold = row['calc_bid_cap'] * 2 if row['calc_bid_cap'] > 0 else 50
        if spend > threshold and profit < 0: return "PAUSE (LOSER)"
        
        # 4. Testing / Unknown
        return "TESTING"
        
    df['calc_action'] = df.apply(decide_action, axis=1)

    # 6. OUTPUT
    # Requested Columns
    final_cols = [
        'meta_campaign_name',
        'meta_adset_name',
        'meta_ad_name',
        'meta_ad_id',
        'meta_link',       
        'feed_link',       
        'base_gross_margin',
        'calc_price_cluster',
        'meta_spend',
        'meta_revenue',
        'meta_roas',
        # New Metrics
        'calc_bid_cap',
        'calc_cost_cap',
        'calc_critical_roas',
        'calc_scaling_roas',
        'calc_contribution_profit',
        'calc_action'
    ]
    
    # Ensure all exist
    for c in final_cols:
        if c not in df.columns: df[c] = None
        
    out_path = os.path.join(output_dir, brand, f"{brand}_Ad_Analysis.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df[final_cols].to_csv(out_path, index=False)
    print(f"Saved Process 1 to: {out_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        brand_arg = sys.argv[1]
        run_ad_analysis(brand_arg, "Input", "Output")
    else:
        print("Usage: python ad_analysis.py <Brand>")
        # Default for debugging
        # run_ad_analysis("Iiyama", "Input", "Output")
