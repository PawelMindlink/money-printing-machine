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
    default_margin = margin_cfg.get('default_rate', 0.5)
    category_overrides = margin_cfg.get('category_overrides', [])
    
    # Calculate Min Margin for Fallback
    all_rates = [default_margin] + [o['rate'] for o in category_overrides]
    min_margin = min(all_rates) if all_rates else default_margin
    # --- DIMENSION 1: FEED (The Base) ---
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    df = parse_product_feed_xml(feed_path)
    
    if df.empty:
        print(f"Warning: Feed missing. Using empty base.")
        df = pd.DataFrame(columns=['feed_id', 'feed_title', 'feed_brand', 'feed_category', 'feed_link', 'norm_url', 'path_key', 'feed_price_str'])

    # --- LANDING PAGE NAMING (Part 1) ---
    # Will be applied later after merge, but ensuring columns exist


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
            lp_map = {
                'Sessions': 'ga4lp_sessions', 
                'Users': 'ga4lp_users', 
                'Purchases': 'ga4lp_purchases', 
                'Purchase revenue': 'ga4lp_revenue',
                'First time purchasers': 'ga4lp_first_time_purchasers'
            }
            if 'Purchase revenue' not in lp_df.columns:
                 rev_col = next((c for c in lp_df.columns if 'revenue' in c.lower() and 'purchase' in c.lower()), None)
                 if rev_col: lp_df.rename(columns={rev_col: 'Purchase revenue'}, inplace=True)
            
            # Map columns
            lp_df.rename(columns=lambda c: lp_map.get(c, c), inplace=True)
            
            # Add path_key
            lp_df['path_key'] = lp_df[lp_col].apply(bl.extract_path)
            
            # Aggregate
            aggs = {c: 'sum' for c in lp_map.values() if c in lp_df.columns}
            lp_agg = lp_df.groupby('path_key').agg(aggs).reset_index()

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
        
        # --- NEW MATCHING LOGIC (SmartMatcher Cascade) ---
        print("[MERGE] Running SmartMatcher Cascade for Meta Ads...")
        # 1. Initialize Matcher with Feed
        matcher = bl.SmartMatcher(df, id_col='feed_id', url_col='norm_url')
        
        # 2. Enrich Meta Data with Feed IDs
        # meta_agg has 'norm_url', we want to find matching 'feed_id' from df
        meta_enriched = matcher.enrich_dataframe(meta_agg, url_col='norm_url')
        
        # 3. Merge back to Main DF
        # We need to merge on 'feed_id' where possible, or 'norm_url' if not.
        # Strat: 
        #  a) Separate Meta rows that found a Feed Match vs those that didn't.
        #  b) For Matched: Merge on feed_id.
        #  c) For Unmatched: Append as new rows (Category/Synthetic).
        
        # A simpler approach that fits current structure:
        # The main DF is the FEED. We want to attach Meta stats to it.
        # But we ALSO want to keep Meta rows that didn't match (Synthetic).
        
        # Left Join Feed <- Meta (via SmartMatch)
        # We can't just do pd.merge because the keys vary.
        # Instead, let's map Meta stats to Feed IDs.
        
        # Aggregate Meta stats by matched feed_id
        meta_matched = meta_enriched[meta_enriched['feed_feed_id'].notna()]
        if not meta_matched.empty:
            # Group by found feed_id (handling 1-to-many matches if any)
            meta_to_feed = meta_matched.groupby('feed_feed_id')[list(aggs.keys())].sum().reset_index()
            # Merge into main DF
            df = pd.merge(df, meta_to_feed, left_on='feed_id', right_on='feed_feed_id', how='left')
            # drop temp join col
            df.drop(columns=['feed_feed_id'], inplace=True, errors='ignore')
        else:
             # Just add columns with 0
             for col in aggs.keys():
                 df[col] = 0.0

        # Identify Unmatched Meta Rows (Ghost/Category candidates)
        meta_unmatched = meta_enriched[meta_enriched['feed_feed_id'].isna()].copy()
        
        # We need to append these to the DF, but they lack feed info.
        # Align columns
        for col in df.columns:
            if col not in meta_unmatched.columns:
                meta_unmatched[col] = None
        
        # Set criticals
        meta_unmatched['calc_entity_type'] = 'CATEGORY_OR_AD'
        meta_unmatched['is_product'] = False
        meta_unmatched['feed_brand'] = brand
        
        # Append
        df = pd.concat([df, meta_unmatched], ignore_index=True)
        
        # Fill NaNs for metrics
        for col in aggs.keys():
            df[col] = df[col].fillna(0)
        
        # Synthetic Products Logic (Same as before)
        if 'meta_spend' in df.columns:
            # 1. Default to PRODUCT
            df['calc_entity_type'] = 'PRODUCT'
            
            # 2. Identify items NOT in feed but with Spend as CATEGORY_OR_AD
            # feed_id is NaN for these rows (outer join from Meta)
            mask_syn = (df['feed_id'].isna()) & (df['meta_spend'] > 0)
            if mask_syn.sum() > 0:
                df.loc[mask_syn, 'feed_brand'] = brand
                df.loc[mask_syn, 'calc_entity_type'] = 'CATEGORY_OR_AD'
                
    else:
        df['calc_entity_type'] = 'PRODUCT'

    # Set is_product flag EARLY for margin calculation
    df['is_product'] = df['calc_entity_type'] == 'PRODUCT'

    # --- LATE MERGE: GA4 LANDING PAGE ---
    # Now that we have all rows (including Synthetic from Meta), fill path_key and merge LP data
    if 'norm_url' in df.columns and 'path_key' in df.columns:
         mask_missing_key = df['path_key'].isna() & df['norm_url'].notna()
         if mask_missing_key.sum() > 0:
             df.loc[mask_missing_key, 'path_key'] = df.loc[mask_missing_key, 'norm_url'].apply(bl.extract_path)
    
    if 'lp_agg' in locals() and not lp_agg.empty:
        df = pd.merge(df, lp_agg, on='path_key', how='left')

    # --- 3. PRE-PROCESSING & FINANCIALS (Phase O) ---
    
    # LANDING PAGE NAMING (Logic Refactor 1)
    # If feed_title is missing (or is_product=False), generate friendly name
    mask_needs_name = (df['feed_title'].isna()) | (df['feed_title'] == '') | (~df['is_product'])
    
    # We prioritize feed_title for proper products. for others we regenerate.
    # Actually, prompt says: "Check if is_product is FALSE... Take norm_url... Sanitize..."
    
    # Apply to all non-products
    mask_non_prod = ~df['is_product']
    if mask_non_prod.sum() > 0:
        # Use norm_url or feed_link
        df.loc[mask_non_prod, 'feed_title'] = df.loc[mask_non_prod].apply(
            lambda r: bl.generate_friendly_name(r['norm_url'] if pd.notna(r['norm_url']) else r.get('feed_link', '')),
            axis=1
        )

    # Fill NA users/sessions
    for c in df.columns:
        if c.startswith(('meta_', 'ga4lp_', 'ga4item_')):
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
    # --- SANITIZE GHOST PRICES (Anomaly Detection) ---
    print("[LOGIC] Running Sanitize Ghost Prices...")
    # Ensure calc_gross_price is ready (it's calculated later, so we might need to place this call AFTER price calc)
    # Actually, price is calculated in next block. We should move this call OR ensure price is calc'd first.
    # Looking at code flow: Price is calc'd in "Logic Refactor 3" block around line 190.
    # So we should Insert this logic AFTER that block.
    # Let's just add a placeholder comment here and do the insertion in the correct place.
    # But wait, the user instructions say "modify Data Merging section". 
    # Sanitize needs PRICE, which comes later. 
    # I will insert it after price calculation.
    pass

    df['category'] = df['feed_category']
    df['product_type'] = df.get('feed_product_type', '')
    df['price'] = df['feed_price_str']
    
    # Gross Margin with Fallback for Non-Products
    df['base_gross_margin'] = df.apply(lambda row: bl.calculate_gross_margin(
        row, default_margin, category_overrides, min_margin=min_margin, is_product=row['is_product']
    ), axis=1)
    
    df['feed_price_numeric'] = pd.to_numeric(df['feed_price_str'].astype(str).str.replace(' PLN', '').str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    
    # --- NON-PRODUCT PRICING (Logic Refactor 2) ---
    # "The Conservative Estimation"
    # Calculate calc_gross_price for non-products as MIN(Feed, Meta_AOV, GA4_AOV)
    
    # 1. Calculate AOVs
    # Meta AOV
    df['meta_aov'] = df['meta_revenue'] / df['meta_purchases'].replace(0, 1)
    df.loc[df['meta_purchases'] == 0, 'meta_aov'] = 0
    
    # GA4 AOV
    df['ga4_aov'] = df['ga4lp_revenue'] / df['ga4lp_purchases'].replace(0, 1)
    df.loc[df['ga4lp_purchases'] == 0, 'ga4_aov'] = 0
    
    df['ga4_aov'] = df['ga4lp_revenue'] / df['ga4lp_purchases'].replace(0, 1)
    df.loc[df['ga4lp_purchases'] == 0, 'ga4_aov'] = 0
    
    df['calc_gross_price'] = df.apply(
        lambda row: bl.calculate_conservative_price(
            row.get('feed_price_numeric', 0),
            row.get('meta_aov', 0),
            row.get('ga4_aov', 0),
            is_product=row.get('is_product', False)
        ), axis=1
    )
    
    # Flag 0 prices
    df['is_price_missing'] = df['calc_gross_price'] == 0
    
    # --- SANITIZE GHOST PRICES (The Safety Valve) ---
    # Clamp extreme anomalies (Ghost Products with prices > 2.5x Category Avg)
    print("[LOGIC] Running Sanitize Ghost Prices...")
    df = bl.sanitize_ghost_prices(df, price_col='calc_gross_price', category_col='feed_category', is_product_col='is_product')
    
    # Cleanup temporary columns if needed (keeping AOVs for debug)
    df['is_price_inferred'] = ~df['is_product'] # Broad definition for now
    
    # Price Cluster (Logic Refactor 3)
    # "The Core Logic"
    # Group by MARGIN GROUP first (we use base_gross_margin as proxy for margin group)
    df['calc_price_cluster'] = 'Other'
    
    for margin in df['base_gross_margin'].unique():
        mask = df['base_gross_margin'] == margin
        if mask.sum() > 0:
            subset = df.loc[mask].copy()
            # Use the NEW Conservative Price
            subset['price_numeric'] = subset['calc_gross_price']
            # Only cluster items with price > 0
            subset_valid = subset[subset['price_numeric'] > 0].copy()
            
            if not subset_valid.empty:
                clusters = bl.assign_price_cluster(subset_valid, price_col='price_numeric')
                df.loc[subset_valid.index, 'calc_price_cluster'] = clusters
                
    # --- BIDDING STRATEGY (Logic Refactor 4) ---
    # Cluster-Based Caps
    # 1. Calc Cluster Stats
    cluster_stats = []
    
    for margin in df['base_gross_margin'].unique():
        margin_mask = df['base_gross_margin'] == margin
        # Get unique clusters in this margin group
        clusters = df.loc[margin_mask, 'calc_price_cluster'].unique()
        
        for cluster_name in clusters:
            if pd.isna(cluster_name) or cluster_name == 'Other':
                continue
                
            cluster_mask = margin_mask & (df['calc_price_cluster'] == cluster_name)
            cluster_df = df.loc[cluster_mask]
            
            stats = bl.calculate_cluster_stats(
                cluster_df, 
                price_col='calc_gross_price', 
                margin_rate_col='base_gross_margin', 
                vat_rate=vat
            )
            stats['calc_price_cluster'] = cluster_name
            stats['base_gross_margin'] = margin
            cluster_stats.append(stats)
            
    # 2. Merge Stats back
    if cluster_stats:
        stats_df = pd.DataFrame(cluster_stats)
        # Merge on Cluster AND Margin (to be safe, though Cluster names theoretically unique per run)
        # Actually assign_price_cluster returns "TOP X PLN", which might duplicate across margin groups?
        # assign_price_cluster logic relies on price ranges. "TOP 1000 PLN" could exist in High Margin and Low Margin groups.
        # So we MUST merge on both.
        
        df = pd.merge(df, stats_df, on=['calc_price_cluster', 'base_gross_margin'], how='left')
        
    # Fill NaNs for items without cluster (Other/Price=0)
    df['bid_cap'] = df.get('bid_cap', 0.0).fillna(0.0)
    df['cost_cap'] = df.get('cost_cap', 0.0).fillna(0.0)
    df['cluster_avg_margin'] = df.get('cluster_avg_margin', 0.0).fillna(0.0)

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

    # Frequency (LP) - Purchases per First Time Purchaser
    df['calc_frequency'] = df.apply(lambda row: bl.calculate_frequency(row['ga4lp_purchases'], row.get('ga4lp_first_time_purchasers', 0)), axis=1)
    
    # GPPV (Item) - Gross Profit Per View
    df['calc_gppv'] = df.apply(lambda row: bl.calculate_gppv(row['calc_gross_profit_item'], row.get('ga4item_views', 0)), axis=1)

    # --- 4. DYNAMIC THRESHOLDS (P75 from History) ---
    # We calculate quantiles based on non-zero data to capture "Good" performance
    
    def get_p75(series):
        s = series[series > 0]
        if s.empty:
            return 1.0  # Minimum threshold to prevent division by zero
        return max(1.0, s.quantile(0.75))  # At least 1.0 to avoid edge cases
        
    P75_VOL_META = get_p75(df['meta_revenue'])
    P75_EFF_META = get_p75(df['calc_contribution_profit'])
    
    P75_VOL_GA = get_p75(df['ga4lp_sessions'])
    P75_EFF_GA = get_p75(df['calc_gpps'])
    
    P75_VOL_ITEM = get_p75(df.get('ga4item_views', pd.Series([0])))
    P75_EFF_ITEM = get_p75(df['calc_gppv'])
    
    # Significance Gates
    AVG_CR = (df['ga4lp_purchases'].sum() / df['ga4lp_sessions'].sum()) if df['ga4lp_sessions'].sum() > 0 else 0.01
    MIN_META_TRANS = 10
    # Significance Floor: Ensure we have enough data (50 sesji/rok to mało -> threshold usually higher)
    # Target 300 sessions (~25/mo) as a floor for "Activity"
    SIGNIFICANCE_FLOOR = 300
    MIN_ORGANIC_SESSIONS = max(SIGNIFICANCE_FLOOR, min(2000, 100 / (AVG_CR if AVG_CR > 0 else 0.01)))
    
    print(f"--- MSC-ALGO PARAMETERS ---")
    print(f"P75 Meta Vol: {P75_VOL_META:.2f} | P75 Meta Eff: {P75_EFF_META:.2f}")
    print(f"P75 GA Vol: {P75_VOL_GA:.2f} | P75 GA Eff: {P75_EFF_GA:.4f}")
    print(f"Min Organic Sessions: {MIN_ORGANIC_SESSIONS:.0f}")

    # --- 5. MSC-ALGO CORE LOGIC (Waterfall) ---
    
    def run_msc_algo(row):
        flags = []
        
        # --- PHASE 1: META ADS FILTRATION ---
        meta_purchases = row.get('meta_purchases', 0)
        contribution_profit = row.get('calc_contribution_profit', 0)
        meta_revenue = row.get('meta_revenue', 0)
        
        # Null-safe comparison
        if pd.notna(meta_purchases) and meta_purchases >= MIN_META_TRANS:
            if pd.notna(contribution_profit) and contribution_profit > 0:
                # Profitable
                if pd.notna(meta_revenue) and meta_revenue >= P75_VOL_META and contribution_profit >= P75_EFF_META:
                    return 1, "PROVEN_STAR", "High ad revenue + profit"
                else:
                    return 2, "PROVEN_COW", "Profitable ads, moderate scale"
            else:
                # Unprofitable (CM <= 0)
                flags.append("META_LOSER")
                # Fall through to Phase 2
        
        # --- PHASE 2: GA4 LANDING PAGE FILTRATION ---
        ga4lp_sessions = row.get('ga4lp_sessions', 0)
        calc_gpps = row.get('calc_gpps', 0)
        
        if pd.notna(ga4lp_sessions) and ga4lp_sessions >= MIN_ORGANIC_SESSIONS:
            is_high_vol = ga4lp_sessions >= P75_VOL_GA
            is_high_eff = pd.notna(calc_gpps) and calc_gpps >= P75_EFF_GA
            
            if is_high_vol and is_high_eff:
                # Scenario A: High Vol + High Eff
                if "META_LOSER" in flags:
                    return 3, "RECOVERY_LAUNCH", "High organic demand, fix ads"
                else:
                    return 3, "NEW_STAR_LAUNCH", "High organic demand, untapped"
            
            elif is_high_vol and not is_high_eff:
                # Scenario B: High Vol + Low Eff -> FIX IT
                return 4, "FIX_LANDING_PAGE", "High traffic, low conversion"
                
            elif not is_high_vol and is_high_eff:
                # Scenario C: Low Vol + High Eff -> SCALE IT
                return 5, "SCALE_UP", "Good CR, needs more traffic"
                
            else:
                # Scenario D: Low Vol + Low Eff -> DOG
                flags.append("LP_FAILURE")
                # Fall through to Phase 3
        
        # --- PHASE 3: GA4 ITEM FILTRATION ---
        
        # Critical Check: Only analyze ITEM data for actual PRODUCTS
        if row.get('calc_entity_type') != "PRODUCT":
            return 8, "IGNORE", "Non-product page"

        if row.get('ga4item_views', 0) >= MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4item_views'] >= P75_VOL_ITEM
            is_high_eff = row['calc_gppv'] >= P75_EFF_ITEM
            
            if is_high_vol and is_high_eff:
                # Scenario E: Hidden Star
                return 6, "DIRECT_TO_PDP", "High PDP views + profit"
                
            elif not is_high_vol and is_high_eff:
                # Scenario F: Hidden Gem
                return 7, "FEED_DPA", "Profitable, low PDP visibility"
                
            elif is_high_vol and not is_high_eff:
                # Scenario G: Window Shopping
                return 8, "IGNORE", "High views, no purchases"
                
        return 8, "IGNORE", "Insufficient data"


    # Apply Logic
    msc_results = df.apply(run_msc_algo, axis=1, result_type='expand')
    df['calc_priority'] = msc_results[0]
    df['calc_segment'] = msc_results[1]
    df['calc_reason'] = msc_results[2]
    
    # Priority Remapping & Actionable Flags
    # Map 99 (FIX_LP) to 4 for better sorting. Rest of priorities remain.
    df.loc[df['calc_priority'] == 99, 'calc_priority'] = 4
    
    # Define Actionability
    df['calc_is_actionable'] = df['calc_priority'].isin([1, 2, 3, 4, 5, 6, 7])
    
    # Define Action Type
    action_map = {
        1: "SCALE_SPEND",
        2: "MAINTAIN_SPEND",
        3: "NEW_AD_CREATIVES",
        4: "UX_PRICE_AUDIT",
        5: "BROAD_AD_TARGETING",
        6: "CONVERSION_CAMPAIGN",
        7: "CATALOG_ADS_DPA",
        8: "IGNORE"
    }
    df['calc_action_type'] = df['calc_priority'].map(action_map).fillna("IGNORE")
    # 6. Actionable Caps (Standard)
    df['calc_net_price'] = df['calc_gross_price'] / (1 + vat)
    
    # Renaming for export consistency with new logic
    df['calc_bid_cap'] = df['bid_cap'] # Cluster-based
    df['calc_cost_cap'] = df['cost_cap'] # Cluster-based
    
    # ROAS Targets (Function of Margin & VAT)
    df['critical_roas'] = df['base_gross_margin'].apply(lambda x: bl.calculate_critical_roas(vat, x))
    df['scaling_roas'] = df['base_gross_margin'].apply(lambda x: bl.calculate_scaling_roas(vat, x))
    df['calc_break_even_roas'] = df['critical_roas'] # Alias due to naming convention
    
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
    
    # Efficiency metrics
    df['arpu'] = df['ga4lp_revenue'] / df.get('ga4lp_users', df['ga4lp_sessions']).replace(0, 1)
    df['arpiv'] = df.apply(lambda r: bl.calculate_arpiv(r.get('ga4item_revenue', 0), r.get('ga4item_views', 0)), axis=1)
    
    # is_product is already calculated earlier
    
    # --- OUTPUT ---
    out_dir = os.path.join(output_dir, brand)
    os.makedirs(out_dir, exist_ok=True)
    
    # Sort by Priority
    df.sort_values(by=['calc_priority', 'calc_contribution_profit'], ascending=[True, False], inplace=True)
    
    # Final Export Column Update
    final_cols = [
        # Core Identifiers
        'feed_id', 'feed_title', 'feed_brand', 'feed_category', 'calc_gross_price', 'is_product', 'is_price_inferred',
        # URL for ad targeting
        'feed_link', 'norm_url',
        # Classification (MSC-ALGO + Actionable Bits)
        'calc_priority', 'calc_segment', 'calc_reason', 'calc_is_actionable', 'calc_action_type',
        'meta_class', 'ga4_class',
        # Financial Metrics
        'base_gross_margin', 'calc_contribution_profit', 'calc_price_cluster',
        # ROAS Targets
        'critical_roas', 'scaling_roas', 'calc_break_even_roas',
        # Efficiency Metrics
        'calc_gpps', 'calc_cr', 'calc_frequency', 'calc_gppv', 'arpu', 'arpiv',
        # Actual Performance (FUNNEL)
        'meta_spend', 'meta_revenue', 'meta_purchases', 'calc_roas',
        'ga4lp_sessions', 'ga4lp_revenue', 'ga4lp_purchases', 'ga4lp_first_time_purchasers',
        'ga4item_views', 'ga4item_revenue',
        # Technical/Debug
        'calc_net_price', 'calc_bid_cap', 'calc_cost_cap', 'cluster_avg_margin'
    ]
    
    
    # Mapping old 'feed_price_numeric' to 'calc_gross_price' for backward compat in viewing logic if needed, 
    # but we are replacing it in the output.
    
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
