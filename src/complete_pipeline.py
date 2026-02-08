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
# PROCESS 2: GROWTH OPPORTUNITIES (MSC-ALGO v1.0)
# ============================================================================

def run_pipeline(brand, input_dir, output_dir, full_config):
    print(f"\n>>> Running Process 2 (MSC-ALGO v1.0) for: {brand}")
    brand_l = brand.lower()
    
    # 1. Get Brand Setup
    clients_list = full_config.get('clients', [])
    config = next((c for c in clients_list if c['name'].lower() == brand.lower()), {})
    if not config:
        print(f"Error: Brand configuration for {brand} not found!")
        return None
        
    vat = config.get('vat_rate', 0.23)
    margin_cfg = config.get('margin_config', {})
    default_margin = margin_cfg.get('default_rate', 0.1) 
    category_overrides = margin_cfg.get('category_overrides', [])
    
    # --- DIMENSION 1: FEED (The Base) ---
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    df = parse_product_feed_xml(feed_path)
    
    if df.empty:
        print(f"Warning: Feed missing. Using empty base.")
        df = pd.DataFrame(columns=['feed_id', 'feed_title', 'feed_brand', 'feed_category', 'feed_link', 'norm_url', 'path_key', 'feed_price_str'])

    # --- DIMENSION 2: GA4 ITEM (Desire) ---
    items_df = pd.DataFrame()
    prop_id = config.get('ga4_property_id')
    
    # API / CSV Load logic (Condensed for brevity, same as before)
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try: items_df = fetch_ga4_items(GA4_CREDS_PATH, prop_id, limit=50000)
        except: pass
    if items_df.empty:
        items_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_items_freeform.csv")
        if not os.path.exists(items_path): items_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_items.csv")
        if os.path.exists(items_path): items_df = load_ga4_csv(items_path)
            
    if not items_df.empty:
        item_map = {'Items viewed': 'ga4item_views', 'Items purchased': 'ga4item_purchases', 'Item revenue': 'ga4item_revenue', 'Item ID': 'raw_item_id'}
        items_df.rename(columns=lambda c: item_map.get(c, c), inplace=True)
        items_df['Clean ID'] = items_df['raw_item_id'].astype(str).apply(lambda x: str(x).split('-')[0].split('.')[0])
        curr_cols = [c for c in items_df.columns if c.startswith('ga4item_')]
        items_agg = items_df.groupby('Clean ID')[curr_cols].sum().reset_index()
        df['feed_id'] = df['feed_id'].astype(str)
        df = pd.merge(df, items_agg, left_on='feed_id', right_on='Clean ID', how='left')
    
    # --- DIMENSION 3: GA4 LANDING PAGE (Traffic/Conversion) ---
    lp_df = pd.DataFrame()
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try: lp_df = fetch_ga4_data(GA4_CREDS_PATH, prop_id, limit=100000)
        except: pass
    if lp_df.empty:
        lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp_freeform.csv") 
        if not os.path.exists(lp_path): lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp.csv")
        if os.path.exists(lp_path): lp_df = load_ga4_csv(lp_path)

    if not lp_df.empty:
        lp_col = next((c for c in ['Landing page', 'Landing page + query string', 'landingPage'] if c in lp_df.columns), None)
        if lp_col:
            lp_df['path_key'] = lp_df[lp_col].apply(bl.extract_path)
            lp_map = {'Sessions': 'ga4lp_sessions', 'Users': 'ga4lp_users', 'Purchases': 'ga4lp_purchases', 'Purchase revenue': 'ga4lp_revenue'}
            if 'Purchase revenue' not in lp_df.columns:
                 rev_col = next((c for c in lp_df.columns if 'revenue' in c.lower() and 'purchase' in c.lower()), None)
                 if rev_col: lp_df.rename(columns={rev_col: 'Purchase revenue'}, inplace=True)
            lp_df.rename(columns=lambda c: lp_map.get(c, c), inplace=True)
            aggs = {c: 'sum' for c in lp_map.values() if c in lp_df.columns}
            lp_agg = lp_df.groupby('path_key').agg(aggs).reset_index()
            df = pd.merge(df, lp_agg, on='path_key', how='left')

    # --- DIMENSION 4: META ADS (The Check) ---
    meta_path = os.path.join(input_dir, brand, f"{brand_l}_meta_ads.csv")
    if os.path.exists(meta_path):
        meta_df = pd.read_csv(meta_path)
        meta_df['norm_url'] = meta_df['Link (ad settings)'].apply(bl.normalize_url)
        meta_map = {'Amount spent (PLN)': 'meta_spend', 'Purchases': 'meta_purchases', 'Purchases conversion value': 'meta_revenue'}
        if 'Amount spent (PLN)' not in meta_df.columns and 'Amount spent' in meta_df.columns: meta_map['Amount spent'] = 'meta_spend'
        meta_df.rename(columns=lambda c: meta_map.get(c, c), inplace=True)
        aggs = {c: 'sum' for c in meta_map.values() if c in meta_df.columns}
        meta_agg = meta_df.groupby('norm_url').agg(aggs).reset_index()
        df = pd.merge(df, meta_agg, on='norm_url', how='outer')
        
        # Synthetic Products Logic (Same as before)
        if 'meta_spend' in df.columns:
            mask_syn = (df['feed_id'].isna()) & (df['meta_spend'] > 0)
            if mask_syn.sum() > 0:
                df.loc[mask_syn, 'feed_brand'] = brand
                df.loc[mask_syn, 'calc_entity_type'] = 'CATEGORY_OR_AD'
            
            # Non-synthetic are products
            df.loc[~df['feed_id'].astype(str).str.startswith('SYN-'), 'calc_entity_type'] = 'PRODUCT'
            df['calc_entity_type'] = df['calc_entity_type'].fillna('PRODUCT') # Fallback
        else:
            df['calc_entity_type'] = 'PRODUCT'
    else:
        df['calc_entity_type'] = 'PRODUCT'

    # --- 3. PRE-PROCESSING & FINANCIALS (Phase O) ---
    # Fill NA
    for c in df.columns:
        if c.startswith(('meta_', 'ga4lp_', 'ga4item_')):
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Base Fields
    df['category'] = df['feed_category']
    df['product_type'] = df.get('feed_product_type', '')
    df['price'] = df['feed_price_str']
    df['base_gross_margin'] = df.apply(lambda row: bl.calculate_gross_margin(row, default_margin, category_overrides), axis=1)
    df['feed_price_numeric'] = pd.to_numeric(df['feed_price_str'].astype(str).str.replace(' PLN', '').str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)

    # 1. Net Revenue (All Sources)
    df['calc_net_revenue_meta'] = df['meta_revenue'] / (1 + vat)
    df['calc_net_revenue_lp'] = df['ga4lp_revenue'] / (1 + vat)
    df['calc_net_revenue_item'] = df.get('ga4item_revenue', 0) / (1 + vat)

    # 2. Gross Profit (All Sources)
    df['calc_gross_profit_meta'] = df['calc_net_revenue_meta'] * df['base_gross_margin']
    df['calc_gross_profit_lp'] = df['calc_net_revenue_lp'] * df['base_gross_margin']
    df['calc_gross_profit_item'] = df['calc_net_revenue_item'] * df['base_gross_margin']

    # 3. Efficiency Metrics
    # CM (Meta)
    df['calc_contribution_profit'] = df['calc_gross_profit_meta'] - df['meta_spend']
    
    # GPPS (LP) - Gross Profit Per Session
    df['calc_gpps'] = df.apply(lambda row: bl.calculate_gpps(row['calc_gross_profit_lp'], row['ga4lp_sessions']), axis=1)
    
    # CR (LP) - Conversion Rate
    df['calc_cr'] = df.apply(lambda row: bl.calculate_cr(row['ga4lp_purchases'], row['ga4lp_sessions']), axis=1)
    
    # GPPV (Item) - Gross Profit Per View
    df['calc_gppv'] = df.apply(lambda row: bl.calculate_gppv(row['calc_gross_profit_item'], row.get('ga4item_views', 0)), axis=1)

    # --- 4. DYNAMIC THRESHOLDS (P75 from History) ---
    # We calculate quantiles based on non-zero data to capture "Good" performance
    
    def get_p75(series):
        s = series[series > 0]
        return s.quantile(0.75) if not s.empty else 0
        
    P75_VOL_META = get_p75(df['meta_revenue'])
    P75_EFF_META = get_p75(df['calc_contribution_profit'])
    
    P75_VOL_GA = get_p75(df['ga4lp_sessions'])
    P75_EFF_GA = get_p75(df['calc_gpps'])
    
    P75_VOL_ITEM = get_p75(df.get('ga4item_views', pd.Series([0])))
    P75_EFF_ITEM = get_p75(df['calc_gppv'])
    
    # Significance Gates
    AVG_CR = (df['ga4lp_purchases'].sum() / df['ga4lp_sessions'].sum()) if df['ga4lp_sessions'].sum() > 0 else 0.01
    MIN_META_TRANS = 10
    MIN_ORGANIC_SESSIONS = min(2000, 100 / (AVG_CR if AVG_CR > 0 else 0.01))
    
    print(f"--- MSC-ALGO PARAMETERS ---")
    print(f"P75 Meta Vol: {P75_VOL_META:.2f} | P75 Meta Eff: {P75_EFF_META:.2f}")
    print(f"P75 GA Vol: {P75_VOL_GA:.2f} | P75 GA Eff: {P75_EFF_GA:.4f}")
    print(f"Min Organic Sessions: {MIN_ORGANIC_SESSIONS:.0f}")

    # --- 5. MSC-ALGO CORE LOGIC (Waterfall) ---
    
    def run_msc_algo(row):
        flags = []
        
        # --- PHASE 1: META ADS FILTRATION ---
        if row['meta_purchases'] >= MIN_META_TRANS:
            if row['calc_contribution_profit'] > 0:
                # Profitable
                if row['meta_revenue'] >= P75_VOL_META and row['calc_contribution_profit'] >= P75_EFF_META:
                    return 1, "PROVEN_STAR"
                else:
                    return 2, "PROVEN_COW"
            else:
                # Unprofitable (CM <= 0)
                flags.append("META_LOSER")
                # Fall through to Phase 2
        
        # --- PHASE 2: GA4 LANDING PAGE FILTRATION ---
        
        if row['ga4lp_sessions'] >= MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4lp_sessions'] >= P75_VOL_GA
            is_high_eff = row['calc_gpps'] >= P75_EFF_GA
            
            if is_high_vol and is_high_eff:
                # Scenario A: High Vol + High Eff
                if "META_LOSER" in flags:
                    return 3, "RECOVERY_LAUNCH"
                else:
                    return 3, "NEW_STAR_LAUNCH"
            
            elif is_high_vol and not is_high_eff:
                # Scenario B: High Vol + Low Eff -> FIX IT
                return 99, "FIX_LANDING_PAGE"
                
            elif not is_high_vol and is_high_eff:
                # Scenario C: Low Vol + High Eff -> SCALE IT
                return 5, "SCALE_UP"
                
            else:
                # Scenario D: Low Vol + Low Eff -> DOG
                flags.append("LP_FAILURE")
                # Fall through to Phase 3
        
        # --- PHASE 3: GA4 ITEM FILTRATION ---
        
        # Critical Check: Only analyze ITEM data for actual PRODUCTS
        if row.get('calc_entity_type') != "PRODUCT":
            return 8, "IGNORE"

        if row.get('ga4item_views', 0) >= MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4item_views'] >= P75_VOL_ITEM
            is_high_eff = row['calc_gppv'] >= P75_EFF_ITEM
            
            if is_high_vol and is_high_eff:
                # Scenario E: Hidden Star
                return 6, "DIRECT_TO_PDP"
                
            elif not is_high_vol and is_high_eff:
                # Scenario F: Hidden Gem
                return 7, "FEED_DPA"
                
            elif is_high_vol and not is_high_eff:
                # Scenario G: Window Shopping
                return 8, "IGNORE"
                
        return 8, "IGNORE"

    # Apply Logic
    msc_results = df.apply(run_msc_algo, axis=1, result_type='expand')
    df['calc_priority'] = msc_results[0]
    df['calc_segment'] = msc_results[1]

    # 6. Actionable Caps (Standard)
    df['calc_net_price'] = df['feed_price_numeric'] / (1 + vat)
    df['calc_bid_cap'] = df['calc_net_price'] * df['base_gross_margin']
    df['calc_cost_cap'] = df['calc_bid_cap'] * 0.7
    df['calc_break_even_roas'] = 1 / df['base_gross_margin'].replace(0, float('inf'))
    df['calc_roas'] = df['meta_revenue'] / df['meta_spend'].replace(0, 1)
    
    # 7. MISSING METRICS (per DATA_DICTIONARY_FINAL.md)
    # Classification columns
    df['meta_class'] = df.apply(lambda r: bl.classify_meta_ads(r['calc_contribution_profit'], r['meta_spend']), axis=1)
    
    # GA4 Classification thresholds
    ga4_thresholds = {
        'min_activity': MIN_ORGANIC_SESSIONS,
        'trans_75': get_p75(df['ga4lp_purchases']),
        'arpu_75': get_p75(df['calc_gpps'])
    }
    df['ga4_class'] = df.apply(lambda r: bl.classify_ga4_product(
        r['ga4lp_sessions'], r['ga4lp_purchases'], r['calc_gpps'], ga4_thresholds
    ), axis=1)
    
    # Financial metrics
    df['critical_roas'] = df['calc_bid_cap'].apply(lambda x: bl.calculate_critical_roas(x))
    df['scaling_roas'] = df['base_gross_margin'].apply(lambda m: bl.calculate_scaling_roas(vat, m))
    
    # Efficiency metrics
    df['arpu'] = df['ga4lp_revenue'] / df.get('ga4lp_users', df['ga4lp_sessions']).replace(0, 1)
    df['arpiv'] = df.apply(lambda r: bl.calculate_arpiv(r.get('ga4item_revenue', 0), r.get('ga4item_views', 0)), axis=1)
    
    # Product flag
    df['is_product'] = df['calc_entity_type'] == 'PRODUCT'

    # --- OUTPUT ---
    out_dir = os.path.join(output_dir, brand)
    os.makedirs(out_dir, exist_ok=True)
    
    # Sort by Priority
    df.sort_values(by=['calc_priority', 'calc_contribution_profit'], ascending=[True, False], inplace=True)
    
    final_cols = [
        # Core Identifiers
        'feed_id', 'feed_title', 'feed_brand', 'feed_category', 'feed_price_numeric', 'is_product',
        # Classification (MSC-ALGO + Legacy)
        'calc_priority', 'calc_segment', 'meta_class', 'ga4_class',
        # Margin & Profit
        'base_gross_margin', 'calc_contribution_profit',
        # Efficiency Metrics
        'calc_gpps', 'calc_cr', 'calc_gppv', 'arpu', 'arpiv',
        # Financial Caps & ROAS
        'calc_bid_cap', 'calc_cost_cap', 'critical_roas', 'scaling_roas', 'calc_break_even_roas',
        # Meta Ads Data
        'meta_spend', 'meta_revenue', 'meta_purchases', 'calc_roas',
        # GA4 Landing Page Data
        'ga4lp_sessions', 'ga4lp_revenue',
        # GA4 Item Data  
        'ga4item_views', 'ga4item_revenue'
    ]
    
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
