"""
MSC-ALGO FastAPI Microservice (Root)
Wraps src/complete_pipeline.py logic as a REST API.
POST /process → accepts JSON payload → returns classified items.
"""
import sys
import os
import json
import traceback

# Add project root AND src/ to path so complete_pipeline.py's internal imports work
_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, 'src'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd

# Import logic from src
from src.complete_pipeline import run_pipeline_logic, join_and_enrich_data
import business_logic_layer as bl

app = FastAPI(
    title="MSC-ALGO API",
    description="Python SSOT for MSC-ALGO Waterfall Classification",
    version="2.0.0"
)

# ============================================================================
# COLUMN REMAPPING: n8n Normalize node names → Python expected names
# ============================================================================

FEED_REMAP = {
    'feed_price': 'feed_price_str',      # n8n sends numeric, Python expects "1234.56 PLN"
    'norm_url_path': 'path_key',         # n8n sends path only, Python uses path_key
}

ITEMS_REMAP = {
    'ga4_item_id': 'Item ID',
    'ga4_item_views': 'Items viewed',
    'ga4_item_rev': 'Item revenue',
    'ga4_item_purch': 'Items purchased',
}

LP_REMAP = {
    'ga4_lp_url': 'Landing page',
    'ga4_norm_path': '_ga4_norm_path',   # Keep but rename to avoid collision
    'ga4_sessions': 'Sessions',
    'ga4_revenue': 'Purchase revenue',
    'ga4_trans': 'Purchases',
}

META_REMAP = {
    'meta_spend': 'Amount spent (PLN)',
    'meta_purch': 'Purchases',
    'meta_rev': 'Purchases conversion value',
    'meta_url': 'Link (ad settings)',     # If n8n provides URL
    'meta_ad_url': 'Link (ad settings)',  # Alternative name
}

# Gold-standard output columns (42 cols)
GOLD_STANDARD_COLS = [
    'feed_id', 'feed_title', 'feed_brand', 'feed_category',
    'calc_gross_price', 'is_product', 'is_price_inferred',
    'feed_link', 'norm_url',
    'calc_priority', 'calc_segment', 'calc_reason',
    'calc_is_actionable', 'calc_action_type',
    'meta_class', 'ga4_class',
    'base_gross_margin', 'calc_contribution_profit', 'calc_price_cluster',
    'critical_roas', 'scaling_roas', 'calc_break_even_roas',
    'calc_gpps', 'calc_cr', 'calc_frequency', 'calc_gppv',
    'arpu', 'arpiv',
    'meta_spend', 'meta_revenue', 'meta_purchases', 'calc_roas',
    'ga4lp_sessions', 'ga4lp_revenue', 'ga4lp_purchases',
    'ga4lp_first_time_purchasers',
    'ga4item_views', 'ga4item_revenue',
    'calc_net_price', 'calc_bid_cap', 'calc_cost_cap',
    'cluster_avg_margin',
    'calc_entity_type',
]


def _remap_df(df, mapping):
    """Rename columns using mapping dict, only for columns that exist."""
    rename = {k: v for k, v in mapping.items() if k in df.columns}
    if rename:
        df = df.rename(columns=rename)
    return df


def _prepare_feed(feed_df):
    """Prepare feed DataFrame: remap columns + fix formats."""
    if feed_df.empty:
        return feed_df

    feed_df = _remap_df(feed_df, FEED_REMAP)

    # Convert numeric price to "1234.56 PLN" string format if needed
    if 'feed_price_str' in feed_df.columns:
        # If it's numeric, convert to string with PLN suffix
        sample = feed_df['feed_price_str'].dropna().iloc[0] if not feed_df['feed_price_str'].dropna().empty else ''
        if not isinstance(sample, str) or 'PLN' not in str(sample):
            feed_df['feed_price_str'] = feed_df['feed_price_str'].apply(
                lambda x: f"{float(x):.2f} PLN" if pd.notna(x) and x != '' else "0 PLN"
            )

    # Generate norm_url from feed_link if missing
    if 'norm_url' not in feed_df.columns and 'feed_link' in feed_df.columns:
        feed_df['norm_url'] = feed_df['feed_link'].apply(
            lambda x: bl.normalize_url(x) if pd.notna(x) and x else ''
        )

    # Generate path_key from norm_url if missing
    if 'path_key' not in feed_df.columns and 'norm_url' in feed_df.columns:
        feed_df['path_key'] = feed_df['norm_url'].apply(
            lambda x: bl.extract_path(x) if pd.notna(x) and x else ''
        )

    # If n8n pre-computed base_gross_margin, keep it (Python will recalculate if category_overrides given)
    # It's already named correctly: base_gross_margin

    return feed_df


def _prepare_items(items_df):
    """Prepare GA4 Items DataFrame."""
    if items_df.empty:
        return items_df
    return _remap_df(items_df, ITEMS_REMAP)


def _prepare_lp(lp_df):
    """Prepare GA4 Landing Page DataFrame."""
    if lp_df.empty:
        return lp_df
    return _remap_df(lp_df, LP_REMAP)


def _prepare_meta(meta_df):
    """Prepare Meta Ads DataFrame."""
    if meta_df.empty:
        return meta_df

    meta_df = _remap_df(meta_df, META_REMAP)

    # If no URL column exists for SmartMatcher, create empty one
    # (SmartMatcher won't match, but pipeline won't crash)
    if 'Link (ad settings)' not in meta_df.columns:
        # Try to use meta_ad_name as a fallback hint
        meta_df['Link (ad settings)'] = ''

    return meta_df


def _filter_output(df):
    """Filter to gold-standard columns only, in correct order."""
    available = [c for c in GOLD_STANDARD_COLS if c in df.columns]
    return df[available]


@app.get("/health")
def health():
    """Health check for monitoring."""
    return {"status": "ok", "service": "msc-algo-v2"}


@app.post("/process")
def process(payload: dict):
    """
    Process n8n data through the Python pipeline.
    """
    try:
        # Handle both direct object and list wrapper
        data = payload
        if isinstance(data, list):
            if not data:
                return JSONResponse(content=[])
            data = data[0]

        # Extract and remap inputs
        feed_data = data.get('feed', [])
        meta_data = data.get('meta_ads', [])
        ga4_items_data = data.get('ga4_items', [])
        ga4_lp_data = data.get('ga4_lp', [])

        # Convert to DataFrames + apply remapping
        feed_df = _prepare_feed(pd.DataFrame(feed_data) if feed_data else pd.DataFrame())
        meta_df = _prepare_meta(pd.DataFrame(meta_data) if meta_data else pd.DataFrame())
        items_df = _prepare_items(pd.DataFrame(ga4_items_data) if ga4_items_data else pd.DataFrame())
        lp_df = _prepare_lp(pd.DataFrame(ga4_lp_data) if ga4_lp_data else pd.DataFrame())

        # Config from n8n
        config_in = data.get('config', {})

        # Extract margin rules from config
        margin_rules = config_in.get('margin_rules', [])
        category_overrides = []
        default_margin = float(config_in.get('default_margin', 0.10))

        # Convert n8n margin_rules format to Python category_overrides format
        for rule in margin_rules:
            if rule.get('match_type') in ('CATEGORY_EXACT', 'KEYWORD'):
                category_overrides.append({
                    'category_pattern': rule.get('match_value', ''),
                    'rate': float(rule.get('margin_rate', default_margin)),
                    'match_type': rule.get('match_type', 'KEYWORD'),
                })

        min_margin_rates = [default_margin] + [o['rate'] for o in category_overrides]
        min_margin = min(min_margin_rates) if min_margin_rates else default_margin

        params = {
            'brand': config_in.get('brand', 'N8N_Run'),
            'vat': float(config_in.get('vat_rate', 0.23)),
            'default_margin': default_margin,
            'min_margin': min_margin,
            'category_overrides': category_overrides,
            'use_n8n_margin': True,  # Flag: use n8n pre-computed margin if available
        }

        # Log input summary
        print(f"[API] Brand: {params['brand']}")
        print(f"[API] Feed: {len(feed_df)} rows, Items: {len(items_df)} rows")
        print(f"[API] LP: {len(lp_df)} rows, Meta: {len(meta_df)} rows")
        print(f"[API] Margin: default={default_margin}, overrides={len(category_overrides)}")

        # Validation
        if feed_df.empty and meta_df.empty:
            return JSONResponse(content=[])

        # Join & Enrich (SmartMatcher)
        df, threshold_params = join_and_enrich_data(feed_df, items_df, lp_df, meta_df, params)
        params.update(threshold_params)

        # Run Logic (Waterfall)
        result_df = run_pipeline_logic(df, params)

        # Filter to gold-standard columns
        result_df = _filter_output(result_df)

        # Log output summary
        print(f"[API] Output: {len(result_df)} rows, {len(result_df.columns)} cols")
        if 'calc_segment' in result_df.columns:
            print(f"[API] Segments: {result_df['calc_segment'].value_counts().to_dict()}")

        # Output
        result = json.loads(result_df.to_json(orient='records', date_format='iso'))
        return JSONResponse(content=result)

    except Exception as e:
        error_response = {
            "error": str(e),
            "trace": traceback.format_exc()
        }
        # Print stack trace to logs
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_response)
