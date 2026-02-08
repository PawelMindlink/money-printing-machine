import pandas as pd
import os
import sys
import json
import business_logic_layer as bl
from ga4_api_client import fetch_ga4_data, fetch_ga4_items
from data_loader import load_ga4_csv, parse_product_feed_xml

# HARDCODED PATH TO CREDENTIALS (for n8n/local execution) - Overridable via Env Var
GA4_CREDS_PATH = os.environ.get("GA4_CREDS_PATH", r"c:\Users\Paweł\Documents\GitHub\ICP Research\Core\Configs\ga4_credentials.json")

# ============================================================================
# PROCESS 2: GROWTH OPPORTUNITIES (MECE Logic)
# ============================================================================

def run_pipeline(brand, input_dir, output_dir, full_config):
    print(f"\n>>> Running Process 2 (Growth Opportunities) for: {brand}")
    brand_l = brand.lower()
    
    # 1. Get Brand Setup
    clients_list = full_config.get('clients', [])
    config = next((c for c in clients_list if c['name'].lower() == brand.lower()), {})
    if not config:
        print(f"Error: Brand configuration for {brand} not found!")
        return None
    
    # --- DIMENSION 1: FEED (The Base) ---
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    df = parse_product_feed_xml(feed_path)
    
    if df.empty:
        print(f"Warning: Feed missing. Using empty base.")
        df = pd.DataFrame(columns=['feed_id', 'feed_title', 'feed_link', 'norm_url', 'path_key', 'feed_price_str', 'feed_brand', 'feed_category'])
    else:
        print(f"Loaded {len(df)} products from Feed")

    # --- DIMENSION 2: GA4 ITEM (Desire) ---
    items_df = pd.DataFrame()
    prop_id = config.get('ga4_property_id')
    
    # API Try
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try:
           items_df = fetch_ga4_items(GA4_CREDS_PATH, prop_id, limit=50000)
        except Exception as e:
            print(f"Items API failed: {e}")

    # CSV Fallback
    if items_df.empty:
        items_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_items_freeform.csv")
        if not os.path.exists(items_path): items_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_items.csv")
        if os.path.exists(items_path): items_df = load_ga4_csv(items_path)
            
    if not items_df.empty:
        # Standardize Columns to 'ga4item_'
        item_map = {
             'Items viewed': 'ga4item_views',
             'Items purchased': 'ga4item_purchases',
             'Item revenue': 'ga4item_revenue',
             'Item ID': 'raw_item_id'
        }
        items_df.rename(columns=lambda c: item_map.get(c, c), inplace=True)
        
        # Clean ID for join
        items_df['Clean ID'] = items_df['raw_item_id'].astype(str).apply(lambda x: str(x).split('-')[0].split('.')[0])
        
        # Aggregate duplicates
        curr_cols = [c for c in items_df.columns if c.startswith('ga4item_')]
        items_agg = items_df.groupby('Clean ID')[curr_cols].sum().reset_index()
        
        # Join to Feed
        df['feed_id'] = df['feed_id'].astype(str)
        df = pd.merge(df, items_agg, left_on='feed_id', right_on='Clean ID', how='left')
        print(f"Enriched with GA4 Items (Matches: {df['Clean ID'].notna().sum()})")
    
    # --- DIMENSION 3: GA4 LANDING PAGE (Traffic/Conversion) ---
    lp_df = pd.DataFrame()
    
    # API Try
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try:
            lp_df = fetch_ga4_data(GA4_CREDS_PATH, prop_id, limit=100000)
        except Exception:
            pass

    # CSV Fallback
    if lp_df.empty:
        lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp_freeform.csv") 
        if not os.path.exists(lp_path): lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp.csv")
        if os.path.exists(lp_path): lp_df = load_ga4_csv(lp_path)

    if not lp_df.empty:
        # Find Link Column
        lp_col = next((c for c in ['Landing page', 'Landing page + query string', 'landingPage'] if c in lp_df.columns), None)
        if lp_col:
            lp_df['path_key'] = lp_df[lp_col].apply(bl.extract_path)
            
            # Map Columns
            lp_map = {
                'Sessions': 'ga4lp_sessions',
                'Users': 'ga4lp_users',
                'Purchases': 'ga4lp_purchases',
                'Purchase revenue': 'ga4lp_revenue'
            }
            # Handle potential revenue name mismatch
            if 'Purchase revenue' not in lp_df.columns:
                 rev_col = next((c for c in lp_df.columns if 'revenue' in c.lower() and 'purchase' in c.lower()), None)
                 if rev_col: lp_df.rename(columns={rev_col: 'Purchase revenue'}, inplace=True)

            lp_df.rename(columns=lambda c: lp_map.get(c, c), inplace=True)
            
            # Aggregate
            aggs = {c: 'sum' for c in lp_map.values() if c in lp_df.columns}
            lp_agg = lp_df.groupby('path_key').agg(aggs).reset_index()
            
            df = pd.merge(df, lp_agg, on='path_key', how='left')
            print(f"Enriched with GA4 LP Data")

    # --- DIMENSION 4: META ADS (The Check) ---
    meta_path = os.path.join(input_dir, brand, f"{brand_l}_meta_ads.csv")
    if os.path.exists(meta_path):
        meta_df = pd.read_csv(meta_path)
        meta_df['norm_url'] = meta_df['Link (ad settings)'].apply(bl.normalize_url)
        
        # Strict Mapping
        meta_map = {
            'Amount spent (PLN)': 'meta_spend',
            'Purchases': 'meta_purchases',
            'Purchases conversion value': 'meta_revenue'
        }
        # Fallback for col names
        if 'Amount spent (PLN)' not in meta_df.columns and 'Amount spent' in meta_df.columns:
             meta_map['Amount spent'] = 'meta_spend'
        
        meta_df.rename(columns=lambda c: meta_map.get(c, c), inplace=True)
        
        aggs = {c: 'sum' for c in meta_map.values() if c in meta_df.columns}
        meta_agg = meta_df.groupby('norm_url').agg(aggs).reset_index()
        
        df = pd.merge(df, meta_agg, on='norm_url', how='outer')
        print(f"Enriched with Meta Ads (Total Rows: {len(df)})")
        
        # Synthetic Products for Unmatched Ads
        if 'meta_spend' in df.columns:
            mask_syn = (df['feed_id'].isna()) & (df['meta_spend'] > 0)
            if mask_syn.sum() > 0:
                print(f"Creating {mask_syn.sum()} Synthetic Products for Unmatched Ads")
                def derive_title(url):
                    if pd.isna(url): return "Unknown Ad"
                    return f"Ad: {url.split('/')[-1][:50]}"
                
                df.loc[mask_syn, 'feed_title'] = df.loc[mask_syn, 'norm_url'].apply(derive_title)
                df.loc[mask_syn, 'feed_category'] = 'General / Category'
                df.loc[mask_syn, 'feed_id'] = df.loc[mask_syn, 'norm_url'].apply(lambda x: f"SYN-{hash(x) % 10000}")
                df.loc[mask_syn, 'feed_price_str'] = '0 PLN'
                df.loc[mask_syn, 'feed_brand'] = brand

    # --- CALCULATIONS ---
    # fill na
    for c in df.columns:
        if c.startswith(('meta_', 'ga4lp_', 'ga4item_')):
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Base Logic
    vat = config.get('vat_rate', 0.23)
    margin_cfg = config.get('margin_config', {})
    default_margin = margin_cfg.get('default_rate', 0.1) 
    category_overrides = margin_cfg.get('category_overrides', [])
    
    # 1. Gross Margin & Price
    df['category'] = df['feed_category']
    df['price'] = df['feed_price_str']
    
    df['base_gross_margin'] = df.apply(lambda row: bl.calculate_gross_margin(row, default_margin, category_overrides), axis=1)
    
    # 2. Financials
    df['feed_price_numeric'] = pd.to_numeric(df['feed_price_str'].astype(str).str.replace(' PLN', '').str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    
    # CP (Page Level)
    df['calc_contribution_profit'] = (
        df.get('ga4lp_revenue', 0) 
        - df.get('meta_spend', 0) 
        - (df.get('ga4lp_purchases', 0) * (df['feed_price_numeric']/(1+vat) * (1-df['base_gross_margin'])))
    )

    # 3. Classifications (MECE Logic)
    
    # Metrics for Classification
    df['calc_arpu'] = df.get('ga4lp_revenue', 0) / df.get('ga4lp_users', 1).replace(0, 1)
    
    if 'ga4item_revenue' in df.columns:
        df['calc_arpiv'] = df.apply(lambda row: bl.calculate_arpiv(row.get('ga4item_revenue', 0), row.get('ga4item_views', 0)), axis=1)
    else:
        df['calc_arpiv'] = 0.0

    df['calc_roas'] = df['meta_revenue'] / df['meta_spend'].replace(0, 1)

    # Thresholds (Dynamic)
    t_sessions = df[df['ga4lp_sessions'] > 0]['ga4lp_sessions'].quantile(0.50) if not df.empty else 100
    t_arpiv = df[df['calc_arpiv'] > 0]['calc_arpiv'].quantile(0.50) if not df.empty else 1.0
    # Min ARPIV check: If item data is missing, use ARPU or ROAS
    
    print(f"Classification Thresholds: Sessions > {t_sessions:.0f}, ARPIV > {t_arpiv:.2f}")

    def classify_mece(row):
        sessions = row.get('ga4lp_sessions', 0)
        arpiv = row.get('calc_arpiv', 0)
        roas = row.get('calc_roas', 0)
        
        # High Efficiency Signal? (Strong Desire OR Strong ROAS)
        is_efficient = (arpiv > t_arpiv) or (roas > 2.0) # 2.0 as generic healthy ROAS, could be dynamic
        
        # Traffic Signal?
        is_high_traffic = sessions > t_sessions
        
        if is_high_traffic and is_efficient:
            return "MONEY_PRINTER" # Quadrant 1
        elif not is_high_traffic and is_efficient:
            return "HIDDEN_GEM" # Quadrant 2
        elif is_high_traffic and not is_efficient:
            return "BLEEDING_STAR" # Quadrant 3
        else:
            return "ZOMBIE" # Quadrant 4

    df['calc_segment'] = df.apply(classify_mece, axis=1)
    
    # 4. Bidding & Caps
    df['calc_bid_cap'] = df.apply(lambda row: bl.calculate_bid_cap(row['feed_price_numeric'], vat, row['base_gross_margin']), axis=1)
    df['calc_cost_cap'] = df['calc_bid_cap'].apply(lambda x: bl.calculate_cost_cap(x))

    # --- OUTPUT ---
    out_dir = os.path.join(output_dir, brand)
    os.makedirs(out_dir, exist_ok=True)
    
    final_cols = [
        # IDs
        'feed_id', 'feed_title', 'feed_brand', 'feed_category', 'feed_price_numeric',
        # Classification
        'calc_segment', 'base_gross_margin',
        # Actionable Caps
        'calc_bid_cap', 'calc_cost_cap',
        # Key Metrics
        'ga4lp_sessions', 'calc_arpiv', 'calc_roas', 'calc_contribution_profit',
        # Drill Down
        'meta_spend', 'meta_revenue', 'ga4lp_purchases', 'ga4item_views'
    ]
    
    # Select only existing
    final_cols = [c for c in final_cols if c in df.columns]
    
    df[final_cols].to_csv(os.path.join(out_dir, f"{brand}_Growth_Opportunities.csv"), index=False)
    print(f"Saved Process 2 Output to: {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open("business_logic.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        run_pipeline(sys.argv[1], "Input", "Output", config)
    else:
        print("Usage: python complete_pipeline.py <Brand>")
