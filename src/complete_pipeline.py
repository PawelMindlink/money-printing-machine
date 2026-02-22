import pandas as pd
import os
import sys
import json
import business_logic_layer as bl
from ga4_api_client import fetch_ga4_data, fetch_ga4_items
from data_loader import load_ga4_csv, parse_product_feed_xml

from dotenv import load_dotenv
load_dotenv()

# GA4 Credentials — set GA4_CREDS_PATH in your .env file (see .env.template)
GA4_CREDS_PATH = os.environ.get("GA4_CREDS_PATH", "")

def get_p75(series):
    """Calculate 75th percentile of positive values."""
    s = series[series > 0]
    if s.empty:
        return 1.0
    return max(1.0, s.quantile(0.75))


def _col(df, name, default=0):
    """Safe column access: always returns a Series, never a scalar."""
    if name in df.columns:
        return df[name]
    return pd.Series(default, index=df.index)


def _ensure_cols(df, cols, default=0):
    """Ensure columns exist in df with default value."""
    for c in cols:
        if c not in df.columns:
            df[c] = default
    return df


# ============================================================================
# API FUNCTIONS (Used by FastAPI main.py — accept pre-loaded DataFrames)
# ============================================================================

def join_and_enrich_data(feed_df, items_df, lp_df, meta_df, params):
    """
    Join 4 data streams and calculate financial metrics.
    Returns (enriched_df, threshold_params).
    """
    df = feed_df.copy() if not feed_df.empty else pd.DataFrame()

    vat = params.get('vat', 0.23)
    default_margin = params.get('default_margin')
    if default_margin is None:
        raise ValueError(
            "[MSC-ALGO] FATAL: 'default_margin' not found in params. "
            "This must be set in brand_config sheet of the Margin Rules Template. "
            "Without it, all margin calculations will be wrong. "
            "Example: default_margin=0.10 for Iiyama, 0.58 for Bushido."
        )
    default_margin = float(default_margin)
    min_margin = params.get('min_margin', 0.1)
    category_overrides = params.get('category_overrides', [])
    brand = params.get('brand', 'API_Run')

    # --- GA4 Items merge ---
    if not items_df.empty:
        item_map = {'Items viewed': 'ga4item_views', 'Items purchased': 'ga4item_purchases',
                    'Item revenue': 'ga4item_revenue', 'Item ID': 'raw_item_id'}
        items_df = items_df.rename(columns=lambda c: item_map.get(c, c))
        if 'raw_item_id' in items_df.columns:
            items_df['Clean ID'] = items_df['raw_item_id'].astype(str).apply(lambda x: str(x).split('-')[0].split('.')[0])
            curr_cols = [c for c in items_df.columns if c.startswith('ga4item_')]
            items_agg = items_df.groupby('Clean ID')[curr_cols].sum().reset_index()
            if 'feed_id' in df.columns:
                df['feed_id'] = df['feed_id'].astype(str)
                df = pd.merge(df, items_agg, left_on='feed_id', right_on='Clean ID', how='left')

    # --- GA4 Landing Page merge ---
    lp_agg = pd.DataFrame()
    if not lp_df.empty:
        lp_col = next((c for c in ['Landing page', 'Landing page + query string', 'landingPage'] if c in lp_df.columns), None)
        if lp_col:
            lp_map = {'Sessions': 'ga4lp_sessions', 'Users': 'ga4lp_users',
                       'Purchases': 'ga4lp_purchases', 'Purchase revenue': 'ga4lp_revenue',
                       'First time purchasers': 'ga4lp_first_time_purchasers'}
            if 'Purchase revenue' not in lp_df.columns:
                rev_col = next((c for c in lp_df.columns if 'revenue' in c.lower() and 'purchase' in c.lower()), None)
                if rev_col:
                    lp_df = lp_df.rename(columns={rev_col: 'Purchase revenue'})
            lp_df = lp_df.rename(columns=lambda c: lp_map.get(c, c))
            lp_df['path_key'] = lp_df[lp_col].apply(bl.extract_path)
            aggs = {c: 'sum' for c in lp_map.values() if c in lp_df.columns}
            lp_agg = lp_df.groupby('path_key').agg(aggs).reset_index()

    # --- Meta Ads merge (SmartMatcher Cascade) ---
    if not meta_df.empty and not df.empty:
        meta_map = {'Amount spent (PLN)': 'meta_spend', 'Purchases': 'meta_purchases',
                    'Purchases conversion value': 'meta_revenue'}
        if 'Amount spent (PLN)' not in meta_df.columns and 'Amount spent' in meta_df.columns:
            meta_map['Amount spent'] = 'meta_spend'
        meta_df = meta_df.rename(columns=lambda c: meta_map.get(c, c))
        if 'norm_url' not in meta_df.columns and 'Link (ad settings)' in meta_df.columns:
            meta_df['norm_url'] = meta_df['Link (ad settings)'].apply(bl.normalize_url)
        aggs = {c: 'sum' for c in meta_map.values() if c in meta_df.columns}
        if 'norm_url' in meta_df.columns:
            meta_agg = meta_df.groupby('norm_url').agg(aggs).reset_index()
        else:
            meta_agg = meta_df

        if 'norm_url' in df.columns and 'feed_id' in df.columns:
            matcher = bl.SmartMatcher(df, id_col='feed_id', url_col='norm_url')
            meta_enriched = matcher.enrich_dataframe(meta_agg, url_col='norm_url')
            meta_matched = meta_enriched[meta_enriched['feed_feed_id'].notna()]
            if not meta_matched.empty:
                meta_to_feed = meta_matched.groupby('feed_feed_id')[list(aggs.keys())].sum().reset_index()
                df = pd.merge(df, meta_to_feed, left_on='feed_id', right_on='feed_feed_id', how='left')
                df.drop(columns=['feed_feed_id'], inplace=True, errors='ignore')
            else:
                for col in aggs.keys():
                    df[col] = 0.0

            # Unmatched → synthetic
            meta_unmatched = meta_enriched[meta_enriched['feed_feed_id'].isna()].copy()
            for col in df.columns:
                if col not in meta_unmatched.columns:
                    meta_unmatched[col] = None
            meta_unmatched['calc_entity_type'] = 'CATEGORY_OR_AD'
            meta_unmatched['is_product'] = False
            meta_unmatched['feed_brand'] = brand
            df = pd.concat([df, meta_unmatched], ignore_index=True)
            for col in aggs.keys():
                df[col] = df[col].fillna(0)
    
    # Ensure meta/item/feed columns exist (BEFORE LP merge to avoid _x/_y suffix collisions)
    df = _ensure_cols(df, [
        'meta_spend', 'meta_revenue', 'meta_purchases',
        'ga4item_views', 'ga4item_revenue', 'ga4item_purchases',
        'feed_price_str', 'feed_category', 'feed_title', 'feed_link', 'feed_image_link', 'feed_id'
    ], default=0)
    # String columns need empty string default
    for sc in ['feed_price_str', 'feed_category', 'feed_title', 'feed_link', 'feed_image_link', 'feed_id']:
        df[sc] = df[sc].fillna('')

    if 'calc_entity_type' not in df.columns:
        df['calc_entity_type'] = 'PRODUCT'
    if 'meta_spend' in df.columns:
        df.loc[df['calc_entity_type'].isna(), 'calc_entity_type'] = 'PRODUCT'
        # Treat empty strings as NaN for feed_id (n8n sends '' not NaN)
        _feed_id_missing = df['feed_id'].isna() | (df['feed_id'].astype(str).str.strip() == '')
        mask_syn = _feed_id_missing & (df['meta_spend'] > 0)
        df.loc[mask_syn, 'calc_entity_type'] = 'CATEGORY_OR_AD'

    df['is_product'] = df['calc_entity_type'] == 'PRODUCT'

    # LP merge
    if 'norm_url' in df.columns:
        if 'path_key' not in df.columns:
            df['path_key'] = df['norm_url'].apply(lambda x: bl.extract_path(x) if pd.notna(x) else None)
        else:
            mask = df['path_key'].isna() & df['norm_url'].notna()
            df.loc[mask, 'path_key'] = df.loc[mask, 'norm_url'].apply(bl.extract_path)
    if not lp_agg.empty and 'path_key' in df.columns:
        df = pd.merge(df, lp_agg, on='path_key', how='left')

    # NOW ensure ga4lp columns exist (AFTER LP merge — safe from _x/_y collisions)
    df = _ensure_cols(df, [
        'ga4lp_sessions', 'ga4lp_users', 'ga4lp_purchases', 'ga4lp_revenue',
        'ga4lp_first_time_purchasers',
    ], default=0)

    # --- Financials ---
    # Ensure numeric columns
    for c in df.columns:
        if c.startswith(('meta_', 'ga4lp_', 'ga4item_')):
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Friendly names for non-products
    mask_non_prod = ~df['is_product']
    if mask_non_prod.sum() > 0 and 'feed_title' in df.columns:
        df.loc[mask_non_prod, 'feed_title'] = df.loc[mask_non_prod].apply(
            lambda r: bl.generate_friendly_name(r.get('norm_url', '') or r.get('feed_link', '') or ''),
            axis=1
        )

    # Margins — use n8n pre-computed if available, otherwise calculate
    if params.get('use_n8n_margin') and 'base_gross_margin' in df.columns:
        # n8n already computed margins via Margin Resolver, just fill NaN
        df['base_gross_margin'] = pd.to_numeric(df['base_gross_margin'], errors='coerce').fillna(default_margin)
    else:
        df['base_gross_margin'] = df.apply(lambda row: bl.calculate_gross_margin(
            row, default_margin, category_overrides, min_margin=min_margin, is_product=row.get('is_product', True)
        ), axis=1)

    # Prices
    if 'feed_price_str' in df.columns:
        df['feed_price_numeric'] = pd.to_numeric(
            df['feed_price_str'].astype(str).str.replace(' PLN', '').str.replace(',', '.').str.replace(' ', ''),
            errors='coerce'
        ).fillna(0)
    else:
        df['feed_price_numeric'] = 0

    df['meta_aov'] = df['meta_revenue'] / df['meta_purchases'].replace(0, 1)
    df.loc[df['meta_purchases'] == 0, 'meta_aov'] = 0
    df['ga4_aov'] = df['ga4lp_revenue'] / df['ga4lp_purchases'].replace(0, 1)
    df.loc[df['ga4lp_purchases'] == 0, 'ga4_aov'] = 0

    df['calc_gross_price'] = df.apply(
        lambda row: bl.calculate_conservative_price(
            row.get('feed_price_numeric', 0), row.get('meta_aov', 0), row.get('ga4_aov', 0),
            is_product=row.get('is_product', False)
        ), axis=1
    )
    df['is_price_missing'] = df['calc_gross_price'] == 0
    df = bl.sanitize_ghost_prices(df, price_col='calc_gross_price', category_col='feed_category', is_product_col='is_product')
    df['is_price_inferred'] = ~df['is_product']

    # Price Clusters
    cluster_threshold = float(params.get('CLUSTER_THRESHOLD', 1.5))
    df['calc_price_cluster'] = 'Other'
    for margin in df['base_gross_margin'].unique():
        mask = df['base_gross_margin'] == margin
        if mask.sum() > 0:
            subset = df.loc[mask].copy()
            subset['price_numeric'] = subset['calc_gross_price']
            subset_valid = subset[subset['price_numeric'] > 0].copy()
            if not subset_valid.empty:
                clusters = bl.assign_price_cluster(subset_valid, price_col='price_numeric', default_threshold=cluster_threshold)
                df.loc[subset_valid.index, 'calc_price_cluster'] = clusters.astype(str)

    # Cluster Stats → Bid/Cost Caps
    cluster_stats = []
    for margin in df['base_gross_margin'].unique():
        margin_mask = df['base_gross_margin'] == margin
        for cluster_name in df.loc[margin_mask, 'calc_price_cluster'].unique():
            if pd.isna(cluster_name) or cluster_name == 'Other':
                continue
            cluster_mask = margin_mask & (df['calc_price_cluster'] == cluster_name)
            stats = bl.calculate_cluster_stats(df.loc[cluster_mask], price_col='calc_gross_price',
                                                margin_rate_col='base_gross_margin', vat_rate=vat)
            stats['calc_price_cluster'] = cluster_name
            stats['base_gross_margin'] = margin
            cluster_stats.append(stats)
    if cluster_stats:
        stats_df = pd.DataFrame(cluster_stats)
        df = pd.merge(df, stats_df, on=['calc_price_cluster', 'base_gross_margin'], how='left')
    df = _ensure_cols(df, ['bid_cap', 'cost_cap'], default=0.0)
    df['bid_cap'] = df['bid_cap'].fillna(0.0)
    df['cost_cap'] = df['cost_cap'].fillna(0.0)

    # Net revenue + Gross Profit
    df['calc_net_revenue_meta'] = df['meta_revenue'] / (1 + vat)
    df['calc_net_revenue_lp'] = df['ga4lp_revenue'] / (1 + vat)
    df['calc_net_revenue_item'] = df['ga4item_revenue'] / (1 + vat)
    df['calc_gross_profit_meta'] = df['calc_net_revenue_meta'] * df['base_gross_margin']
    df['calc_gross_profit_lp'] = df['calc_net_revenue_lp'] * df['base_gross_margin']
    df['calc_gross_profit_item'] = df['calc_net_revenue_item'] * df['base_gross_margin']

    # Efficiency
    df['calc_contribution_profit'] = df['calc_gross_profit_meta'] - df['meta_spend']
    df['calc_gpps'] = df.apply(lambda r: bl.calculate_gpps(r.get('calc_gross_profit_lp', 0), r.get('ga4lp_sessions', 0)), axis=1)
    df['calc_cr'] = df.apply(lambda r: bl.calculate_cr(r.get('ga4lp_purchases', 0), r.get('ga4lp_sessions', 0)), axis=1)
    df['calc_frequency'] = df.apply(lambda r: bl.calculate_frequency(r.get('ga4lp_purchases', 0), r.get('ga4lp_first_time_purchasers', 0)), axis=1)
    df['calc_gppv'] = df.apply(lambda r: bl.calculate_gppv(r.get('calc_gross_profit_item', 0), r.get('ga4item_views', 0)), axis=1)

    # ── MSC V3: Pure Product Demand Thresholds ──
    # Sum of LP purchases (verified checkouts) and item-level purchases
    df['_total_tx'] = df.get('ga4lp_purchases', pd.Series(0, index=df.index)).fillna(0) + \
                      df.get('ga4item_purchases', pd.Series(0, index=df.index)).fillna(0)
    
    non_zero_tx = df[df['_total_tx'] > 0]['_total_tx']
    P90_TX = non_zero_tx.quantile(0.90) if len(non_zero_tx) > 0 else 0
    P75_TX = non_zero_tx.quantile(0.75) if len(non_zero_tx) > 0 else 0
    
    # Establish minimum thresholds for significance
    THRESHOLD_A = max(15, int(P90_TX))  # Bestseller
    THRESHOLD_B = max(5, int(P75_TX))   # Strong Seller

    # Meta thresholds
    P75_VOL_META = get_p75(df['meta_revenue'])
    P75_EFF_META = get_p75(df['calc_contribution_profit'])
    MIN_META_TRANS = 10

    # Traffic distribution for CRO anomalies
    P75_VOL_GA = get_p75(df['ga4lp_sessions'])

    threshold_params = {
        'THRESHOLD_A': THRESHOLD_A, 'THRESHOLD_B': THRESHOLD_B,
        'P75_VOL_META': P75_VOL_META, 'P75_EFF_META': P75_EFF_META,
        'P75_VOL_GA': P75_VOL_GA, 'MIN_META_TRANS': MIN_META_TRANS,
        'MIN_LP_SESSIONS': 300, 'vat': vat
    }

    threshold_params = {
        'P75_TX': P75_TX, 'MIN_DEMAND_TX': MIN_DEMAND_TX,
        'P75_VOL_META': P75_VOL_META, 'P75_EFF_META': P75_EFF_META,
        'P75_VOL_GA': P75_VOL_GA, 'P75_EFF_GA': P75_EFF_GA,
        'P75_VOL_ITEM': P75_VOL_ITEM, 'P75_EFF_ITEM': P75_EFF_ITEM,
        'AVG_CR': AVG_CR, 'MIN_META_TRANS': MIN_META_TRANS,
        'MIN_LP_SESSIONS': 300, 'MIN_ITEM_VIEWS': 50,
        'top_categories': _top_categories, 'category_col': _cat_col,
        'vat': vat,
    }

    return df, threshold_params


def run_pipeline_logic(df, params):
    """
    Apply MSC-ALGO V3 (Pure Product Meritocracy).

    WHAT (Product Merit) -> Determines 1-8 priority queue.
    HOW (Ad Context) -> Handled downstream by creative_context grouping.
    
    Dimensions assessed:
    1. Demand: A (Bestseller), B (Strong Seller), C (Low Seller), D (Zero Sales)
    2. Meta Status: Winner, Loser, Testing, Untested
    3. Traffic Leak: High traffic with 0 conversions
    """
    vat = params.get('vat', 0.23)
    THRESHOLD_A = params.get('THRESHOLD_A', 15)
    THRESHOLD_B = params.get('THRESHOLD_B', 5)
    P75_VOL_META = params.get('P75_VOL_META', 1)
    P75_EFF_META = params.get('P75_EFF_META', 1)
    P75_VOL_GA = params.get('P75_VOL_GA', 1)
    MIN_META_TRANS = params.get('MIN_META_TRANS', 10)
    MIN_LP_SESSIONS = params.get('MIN_LP_SESSIONS', 300)

    # Ensure _total_tx exists in case pipeline skips threshold step
    if '_total_tx' not in df.columns:
        df['_total_tx'] = df.get('ga4lp_purchases', pd.Series(0, index=df.index)).fillna(0) + \
                          df.get('ga4item_purchases', pd.Series(0, index=df.index)).fillna(0)

    def run_msc_algo(row):
        total_tx = row.get('_total_tx', 0) or 0
        meta_purchases = row.get('meta_purchases', 0) or 0
        meta_cp = row.get('calc_contribution_profit', 0) or 0
        meta_spend = row.get('meta_spend', 0) or 0
        ga4_sessions = row.get('ga4lp_sessions', 0) or 0
        
        # Determine Demand Tag
        if total_tx >= THRESHOLD_A: demand = 'A'
        elif total_tx >= THRESHOLD_B: demand = 'B'
        elif total_tx >= 1: demand = 'C'
        else: demand = 'D'
            
        # Determine Meta Status Tag
        if meta_purchases >= MIN_META_TRANS and meta_cp > 0:
            meta_status = 'WINNER'
        elif meta_spend > 100 and meta_cp < 0:
            meta_status = 'LOSER'
        elif meta_spend > 0:
            meta_status = 'TESTING'
        else:
            meta_status = 'UNTESTED'
            
        # Exceptions
        if row.get('calc_entity_type', 'PRODUCT') != "PRODUCT":
            return 8, "NON_PRODUCT", "Non-product page"
        
        # Core Classification Matrix
        if meta_status == 'WINNER' and demand in ['A', 'B']:
            return 1, "SCALE_HERO", "Top Meta profit + Strong organic demand"
            
        if demand == 'A':
            return 2, "ORGANIC_BESTSELLER", "Top 10% organic market volume"
            
        if demand == 'B':
            return 3, "CATALOG_PROVEN", "Top 25% organic volume, robust catalog"
            
        # Only punish for Meta loss if it's NOT a bestseller naturally
        if meta_status == 'LOSER' and demand in ['C', 'D']:
            return 8, "DEAD_WEIGHT", "Proven Meta loss-maker with low organic demand"
        elif meta_status == 'LOSER' and demand in ['A', 'B']:
            # It loses money on ads, but sells organically. Put it in broad DPA, don't force manual ads.
            return 6, "LONG_TAIL", "Organic winner but Meta loss-maker, keep in background DPA"
            
        if meta_status == 'WINNER' and demand in ['C', 'D']:
            return 4, "META_MODERATE", "Profitable Meta ads, but low organic scale"
            
        if demand == 'D' and ga4_sessions >= max(MIN_LP_SESSIONS, P75_VOL_GA):
            return 5, "TRAFFIC_LEAK", "High traffic volume, zero conversions"
            
        if demand == 'C':
            return 6, "LONG_TAIL", "Occasional sales, broad DPA inclusion"
            
        if demand == 'D' and meta_status == 'UNTESTED':
            return 7, "COLD_TEST", "Zero sales, untested on Meta"
            
        return 7, "COLD_TEST", "Fallback rule"

    if not df.empty:
        msc_results = df.apply(run_msc_algo, axis=1, result_type='expand')
        df['calc_priority'] = msc_results[0]
        df['calc_segment'] = msc_results[1]
        df['calc_reason'] = msc_results[2]
        df['calc_is_actionable'] = df['calc_priority'].isin([1, 2, 3, 4, 5, 6, 7])
    else:
        df['calc_priority'] = pd.Series(dtype=int)
        df['calc_segment'] = pd.Series(dtype=str)
        df['calc_reason'] = pd.Series(dtype=str)
        df['calc_is_actionable'] = pd.Series(dtype=bool)

    # Action types map directly to specific tasks independent of creative theme
    action_map = {
        1: "MANUAL_SCALE_ADS",      # Media Buyer: Scale budget on existing hero ads
        2: "LAUNCH_NEW_CREATIVES",  # Copywriter: Top priority for new ad angles
        3: "ADVANTAGE_PLUS_DPA",    # Media Buyer: Add reliably to catalog
        4: "MAINTAIN_SPEND",        # Media Buyer: Don't scale, but keep running
        5: "CRO_AUDIT_PDP",         # Developer: Fix the landing page
        6: "BROAD_CATALOG_ONLY",    # Automated: Background DPA fodder
        7: "TESTING_QUEUE",         # Copywriter: Test when core queue is empty
        8: "EXCLUDE_FROM_ADS",      # Exclude entirely
    }
    df['calc_action_type'] = df['calc_priority'].map(action_map).fillna("EXCLUDE_FROM_ADS")
    df = _ensure_cols(df, ['calc_gross_price', 'bid_cap', 'cost_cap', 'meta_revenue', 'meta_spend',
                            'ga4lp_revenue', 'ga4lp_sessions', 'ga4lp_purchases', 'ga4lp_users',
                            'ga4item_views', 'ga4item_revenue', 'calc_contribution_profit', 'calc_gpps'])
    df['calc_net_price'] = df['calc_gross_price'] / (1 + vat)
    df['calc_bid_cap'] = df['bid_cap']
    df['calc_cost_cap'] = df['cost_cap']
    df['critical_roas'] = df['base_gross_margin'].apply(lambda x: bl.calculate_critical_roas(vat, x))
    df['scaling_roas'] = df['base_gross_margin'].apply(lambda x: bl.calculate_scaling_roas(vat, x))
    df['calc_critical_roas'] = df['critical_roas']
    df['calc_roas'] = df['meta_revenue'] / df['meta_spend'].replace(0, 1)
    df['meta_class'] = df.apply(lambda r: bl.classify_meta_ads(r.get('calc_contribution_profit', 0), r.get('meta_spend', 0)), axis=1)
    ga4_thresholds = {
        'min_activity': MIN_LP_SESSIONS,
        'trans_75': get_p75(df['ga4lp_purchases']),
        'arpu_75': get_p75(df['calc_gpps'])
    }
    df['ga4_class'] = df.apply(lambda r: bl.classify_ga4_product(
        r.get('ga4lp_sessions', 0), r.get('ga4lp_purchases', 0), r.get('calc_gpps', 0), ga4_thresholds
    ), axis=1)
    df['arpu'] = df['ga4lp_revenue'] / _col(df, 'ga4lp_users', df['ga4lp_sessions']).replace(0, 1)
    df['arpiv'] = df.apply(lambda r: bl.calculate_arpiv(r.get('ga4item_revenue', 0), r.get('ga4item_views', 0)), axis=1)
    df.sort_values(by=['calc_priority', 'calc_contribution_profit'], ascending=[True, False], inplace=True)

    # Row cap with activity priority (Issue 4)
    # Active rows first, empty CATEGORY_OR_AD at the end, capped at 1000 total
    MAX_OUTPUT_ROWS = 1000
    _has_activity = (
        (_col(df, 'ga4lp_sessions') > 0) |
        (_col(df, 'meta_spend') > 0) |
        (_col(df, 'ga4item_views') > 0)
    )
    df_active = df[_has_activity]
    df_empty = df[~_has_activity]
    remaining = max(0, MAX_OUTPUT_ROWS - len(df_active))
    df = pd.concat([df_active, df_empty.head(remaining)], ignore_index=True)

    return df


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
    default_margin = margin_cfg.get('default_rate')
    if default_margin is None:
        raise ValueError(
            f"[MSC-ALGO] FATAL: 'default_rate' not found in margin_config for brand '{brand}'. "
            f"Set it in business_logic.json under clients → {brand} → margin_config → default_rate. "
            f"Example: 0.10 for Iiyama, 0.58 for Bushido."
        )
    default_margin = float(default_margin)
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

    # --- ADD MECE CREATIVE CONTEXT ---
    df['creative_context'] = df['feed_title'].apply(lambda t: bl.apply_mece_waterfall(t, brand))

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
    if prop_id and GA4_CREDS_PATH and os.path.exists(GA4_CREDS_PATH):
        print(f"[GA4] Attempting API Fetch for LP (Prop: {prop_id})")
        try: lp_df = fetch_ga4_data(GA4_CREDS_PATH, prop_id, limit=200000)
        except Exception as e: print(f"[GA4] LP API Error: {e}")
    else:
        print(f"[GA4] API Config Missing. CREDS_PATH: {GA4_CREDS_PATH}, exists: {os.path.exists(GA4_CREDS_PATH) if GA4_CREDS_PATH else False}")

    if lp_df.empty:
        print("[GA4] Falling back to CSV for LP Data")
        lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp_freeform.csv") 
        if not os.path.exists(lp_path): lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp.csv")
        if not os.path.exists(lp_path): lp_path = os.path.join(input_dir, brand, f"ga4_landing_page.csv")
        if os.path.exists(lp_path): 
            print(f"[GA4] Loading CSV: {lp_path}")
            lp_df = load_ga4_csv(lp_path)

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
        if not df.empty and 'feed_id' in df.columns:
            matcher = bl.SmartMatcher(df, id_col='feed_id', url_col='norm_url')
            
            # 2. Enrich Meta Data with Feed IDs
            meta_enriched = matcher.enrich_dataframe(meta_agg, url_col='norm_url')
        else:
            meta_enriched = meta_agg.copy()
            meta_enriched['feed_feed_id'] = None

        match_col = 'feed_feed_id' if 'feed_feed_id' in meta_enriched.columns else 'feed_id'
        if match_col not in meta_enriched.columns:
            meta_enriched[match_col] = None
        
        # 3. Merge back to Main DF
        meta_matched = meta_enriched[meta_enriched[match_col].notna()]
        if not meta_matched.empty:
            # Group by found feed_id (handling 1-to-many matches if any)
            meta_to_feed = meta_matched.groupby(match_col)[list(aggs.keys())].sum().reset_index()
            # Merge into main DF
            df = pd.merge(df, meta_to_feed, left_on='feed_id', right_on=match_col, how='left')
            # drop temp join col
            df.drop(columns=[match_col], inplace=True, errors='ignore')
        else:
             # Just add columns with 0
             for col in aggs.keys():
                 if col not in df.columns:
                     df[col] = 0.0

        # Identify Unmatched Meta Rows (Ghost/Category candidates)
        meta_unmatched = meta_enriched[meta_enriched[match_col].isna()].copy()
        
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
            # Treat empty strings as NaN (n8n sends '' not NaN)
            _feed_id_missing = df['feed_id'].isna() | (df['feed_id'].astype(str).str.strip() == '')
            mask_syn = _feed_id_missing & (df['meta_spend'] > 0)
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
        
        # Apply MECE Context globally to the newly named Non-Products (URLs)
        df.loc[mask_non_prod, 'creative_context'] = df.loc[mask_non_prod, 'feed_title'].apply(
            lambda t: bl.apply_mece_waterfall(t, brand)
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

    # --- 4 & 5. MSC-ALGO V3 (Pure Product Meritocracy) ---
    # Build params dict from live data and delegate to the shared V3 logic function
    def _get_p75(series):
        s = series[series > 0]
        return max(1.0, s.quantile(0.75)) if not s.empty else 1.0

    df['_total_tx'] = df.get('ga4lp_purchases', pd.Series(0, index=df.index)).fillna(0) + \
                      df.get('ga4item_purchases', pd.Series(0, index=df.index)).fillna(0)
    P75_TX = _get_p75(df['_total_tx'])
    
    params_v3 = {
        'vat': vat,
        'THRESHOLD_A': max(1, int(P75_TX * 2)),   # Top 10% proxy
        'THRESHOLD_B': max(1, int(P75_TX)),         # Top 25% proxy
        'P75_TX': P75_TX,
        'P75_VOL_META': _get_p75(df['meta_revenue']),
        'P75_EFF_META': _get_p75(df['calc_contribution_profit']),
        'P75_VOL_GA': _get_p75(df['ga4lp_sessions']),
        'MIN_META_TRANS': 10,
        'MIN_LP_SESSIONS': 300,
    }
    
    print(f"--- MSC-ALGO V3 PARAMETERS ---")
    print(f"P75_TX: {P75_TX:.1f} | THRESHOLD_A: {params_v3['THRESHOLD_A']} | THRESHOLD_B: {params_v3['THRESHOLD_B']}")
    
    df = run_pipeline_logic(df, params_v3)
    
    # --- 6. ADDITIONAL METRICS (post V3 classification) ---
    df['calc_net_price'] = df['calc_gross_price'] / (1 + vat)
    
    # Renaming for export consistency with new logic
    df['calc_bid_cap'] = df['bid_cap'] # Cluster-based
    df['calc_cost_cap'] = df['cost_cap'] # Cluster-based
    
    # ROAS Targets (Function of Margin & VAT)
    df['critical_roas'] = df['base_gross_margin'].apply(lambda x: bl.calculate_critical_roas(vat, x))
    df['scaling_roas'] = df['base_gross_margin'].apply(lambda x: bl.calculate_scaling_roas(vat, x))
    df['calc_critical_roas'] = df['critical_roas']
    
    df['calc_roas'] = df['meta_revenue'] / df['meta_spend'].replace(0, 1)
    
    # 7. MISSING METRICS (per DATA_DICTIONARY_FINAL.md)
    # Classification columns
    df['meta_class'] = df.apply(lambda r: bl.classify_meta_ads(r['calc_contribution_profit'], r['meta_spend']), axis=1)
    
    # GA4 Classification thresholds
    ga4_thresholds = {
        'min_activity': 300,
        'trans_75': _get_p75(df['ga4lp_purchases']),
        'arpu_75': _get_p75(df['calc_gpps'])
    }
    df['ga4_class'] = df.apply(lambda r: bl.classify_ga4_product(
        r.get('ga4lp_sessions', 0), r.get('ga4lp_purchases', 0), r.get('calc_gpps', 0), ga4_thresholds
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
        'critical_roas', 'scaling_roas', 'calc_critical_roas',
        # Efficiency Metrics
        'calc_gpps', 'calc_cr', 'calc_frequency', 'calc_gppv', 'arpu', 'arpiv',
        # Actual Performance (FUNNEL)
        'meta_spend', 'meta_revenue', 'meta_purchases', 'calc_roas',
        'ga4lp_sessions', 'ga4lp_revenue', 'ga4lp_purchases', 'ga4lp_first_time_purchasers',
        'ga4item_views', 'ga4item_revenue',
        # Technical/Debug
        'calc_net_price', 'calc_bid_cap', 'calc_cost_cap', 'cluster_avg_margin',
        # Ad Context — appended last as enrichment column
        'creative_context',
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
