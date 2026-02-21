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
from src.meta_api_client import fetch_meta_ads_data
from src.ga4_api_client import fetch_ga4_landing_pages, fetch_ga4_items
from src.data_loader import parse_product_feed_xml_from_url
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
    'ga4_users': 'Users',
    'ga4_first_time_purchasers': 'First time purchasers',
}

META_REMAP = {
    'meta_spend': 'Amount spent (PLN)',
    'meta_purch': 'Purchases',
    'meta_rev': 'Purchases conversion value',
    'meta_url': 'Link (ad settings)',       # n8n Normalize Meta Ads → website_url
    'meta_ad_url': 'Link (ad settings)',    # Alternative name (backward compat)
}

# Gold-standard output columns (expanded to include all diagnostic fields)
GOLD_STANDARD_COLS = [
    'feed_id', 'feed_title', 'feed_brand', 'feed_category',
    'feed_price_str', 'feed_price_numeric',
    'calc_gross_price', 'is_price_missing', 'is_price_inferred',
    '_is_price_anomaly', '_original_price',
    'is_product', 'calc_entity_type',
    'feed_link', 'feed_image_link', 'norm_url',
    'calc_priority', 'calc_segment', 'calc_reason',
    'calc_is_actionable', 'calc_action_type',
    'meta_class', 'ga4_class',
    'base_gross_margin', 'calc_contribution_profit', 'calc_price_cluster',
    'critical_roas', 'scaling_roas', 'calc_critical_roas', 'calc_roas',
    'calc_gpps', 'calc_cr', 'calc_frequency', 'calc_gppv',
    'arpu', 'arpiv',
    'meta_spend', 'meta_revenue', 'meta_purchases', 'meta_aov',
    'ga4lp_sessions', 'ga4lp_users', 'ga4lp_revenue', 'ga4lp_purchases',
    'ga4lp_first_time_purchasers',
    'ga4_aov',
    'ga4item_views', 'ga4item_revenue', 'ga4item_purchases',
    'calc_net_revenue_meta', 'calc_net_revenue_lp', 'calc_net_revenue_item',
    'calc_gross_profit_meta', 'calc_gross_profit_lp', 'calc_gross_profit_item',
    'calc_net_price', 'calc_bid_cap', 'calc_cost_cap',
    'cluster_avg_margin',
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

    # FIX: n8n sends 'norm_url_path' which is mapped to 'path_key'.
    # n8n strips leading slash, but internal logic expects it.
    if 'path_key' in feed_df.columns:
        feed_df['path_key'] = feed_df['path_key'].fillna('').astype(str).str.strip()
        feed_df['path_key'] = feed_df['path_key'].apply(
            lambda x: f"/{x}" if x and not x.startswith('/') else x
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
    return {
        "status": "ok",
        "service": "msc-algo-v2",
        "version": "2.2.0",
        "gold_standard_cols": len(GOLD_STANDARD_COLS),
    }


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

        # Diagnostic: log raw input sizes BEFORE remapping
        print(f"[API] RAW input: feed={len(feed_data)}, meta={len(meta_data)}, items={len(ga4_items_data)}, lp={len(ga4_lp_data)}")
        if ga4_lp_data:
            print(f"[API] LP sample keys: {list(ga4_lp_data[0].keys())}")
            print(f"[API] LP sample[0]: ga4_lp_url={ga4_lp_data[0].get('ga4_lp_url', 'MISSING')[:80]}, sessions={ga4_lp_data[0].get('ga4_sessions', 'MISSING')}")
        else:
            print("[API] WARNING: ga4_lp is EMPTY - LP join will produce 0 sessions for all rows!")
        if meta_data:
            print(f"[API] Meta sample keys: {list(meta_data[0].keys())}")
        else:
            print("[API] WARNING: meta_ads is EMPTY - all rows will be 'No Ads'!")

        # Convert to DataFrames + apply remapping
        feed_df = _prepare_feed(pd.DataFrame(feed_data) if feed_data else pd.DataFrame())
        meta_df = _prepare_meta(pd.DataFrame(meta_data) if meta_data else pd.DataFrame())
        items_df = _prepare_items(pd.DataFrame(ga4_items_data) if ga4_items_data else pd.DataFrame())
        lp_df = _prepare_lp(pd.DataFrame(ga4_lp_data) if ga4_lp_data else pd.DataFrame())

        # Diagnostic: log columns AFTER remapping
        print(f"[API] After remap: lp_cols={list(lp_df.columns) if not lp_df.empty else 'EMPTY'}")
        print(f"[API] After remap: meta_cols={list(meta_df.columns) if not meta_df.empty else 'EMPTY'}")

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
                    'category': rule.get('match_value', ''),
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

@app.post("/run_extraction")
def run_extraction(payload: dict):
    """
    Process n8n data by fetching it directly from APIs (Orchestrator-Worker model).
    Requires only 'config' block in payload.
    """
    try:
        data = payload
        if isinstance(data, list):
            if not data:
                return JSONResponse(content=[])
            data = data[0]

        config_in = data.get('config', data) # fallback to root if no 'config' wrapper
        
        brand = config_in.get('BRAND', config_in.get('brand', 'N8N_Run'))
        date_from = config_in.get('DATE_FROM', config_in.get('date_from'))
        date_to = config_in.get('DATE_TO', config_in.get('date_to'))
        ga4_property_id = config_in.get('GA4_PROPERTY_ID', config_in.get('ga4_property_id'))
        meta_account_id = config_in.get('META_ACCOUNT_ID', config_in.get('meta_account_id'))
        feed_url = config_in.get('FEED_URL', config_in.get('feed_url'))

        print(f"[EXTRACT] Starting extraction for {brand}...")
        
        use_cache = config_in.get('USE_CACHE', False)
        cache_dir = 'Cache'
        os.makedirs(cache_dir, exist_ok=True)
        
        def _get_or_fetch(cache_name, fetch_func, *args, **kwargs):
            cache_path = os.path.join(cache_dir, cache_name)
            if use_cache and os.path.exists(cache_path):
                print(f"[CACHE] Loading {cache_name} from disk...")
                return pd.read_pickle(cache_path)
            else:
                df = fetch_func(*args, **kwargs)
                if not df.empty:
                    df.to_pickle(cache_path)
                    print(f"[CACHE] Saved {cache_name} to disk.")
                return df

        # 1. Fetch XML Feed
        if feed_url:
            if use_cache and os.path.exists(os.path.join(cache_dir, 'feed_raw.pkl')):
                 print("[CACHE] Loading feed_raw.pkl from disk...")
                 feed_raw = pd.read_pickle(os.path.join(cache_dir, 'feed_raw.pkl'))
            elif feed_url.startswith('http'):
                 feed_raw = parse_product_feed_xml_from_url(feed_url)
                 feed_raw.to_pickle(os.path.join(cache_dir, 'feed_raw.pkl'))
            else:
                 from src.data_loader import parse_product_feed_xml
                 print(f"[EXTRACT] Using local feed file: {feed_url}")
                 feed_raw = parse_product_feed_xml(feed_url)
                 feed_raw.to_pickle(os.path.join(cache_dir, 'feed_raw.pkl'))
        else:
            print("[EXTRACT] No feed_url provided.")
            feed_raw = pd.DataFrame()

        # 2. Fetch GA4 Data
        ga4_creds = os.environ.get("GA4_CREDS_PATH", "")
        if ga4_property_id and ga4_creds:
            ga4_items_raw = _get_or_fetch('ga4_items_raw.pkl', fetch_ga4_items, ga4_creds, ga4_property_id, start_date=date_from, end_date=date_to, limit=50000)
            ga4_lp_raw = _get_or_fetch('ga4_lp_raw.pkl', fetch_ga4_landing_pages, ga4_creds, ga4_property_id, start_date=date_from, end_date=date_to, limit=50000)
        else:
            print("[EXTRACT] Missing GA4 property ID or credentials.")
            ga4_items_raw = pd.DataFrame()
            ga4_lp_raw = pd.DataFrame()

        # 3. Fetch Meta Ads
        if meta_account_id:
            try:
                meta_raw = _get_or_fetch('meta_raw.pkl', fetch_meta_ads_data, meta_account_id, date_from, date_to)
            except Exception as e:
                print(f"[EXTRACT] Meta API Error: {e}")
                meta_raw = pd.DataFrame()
        else:
            print("[EXTRACT] Missing Meta account ID.")
            meta_raw = pd.DataFrame()

        # Extract margin rules from config
        margin_rules = config_in.get('MARGIN_RULES', config_in.get('margin_rules', []))
        category_overrides = []
        # Priority: DEFAULT_MARGIN (uppercase, from our local scripts) > default_margin (lowercase, from n8n) > 0.10
        default_margin = float(
            config_in.get('DEFAULT_MARGIN',
            config_in.get('default_margin', 0.10))
        )
             
        # Convert n8n margin_rules format to Python category_overrides format
        for rule in margin_rules:
            if rule.get('match_type') in ('CATEGORY_EXACT', 'KEYWORD'):
                category_overrides.append({
                    'category': rule.get('match_value', ''),
                    'rate': float(rule.get('margin_rate', default_margin)),
                    'match_type': rule.get('match_type', 'KEYWORD'),
                })

        min_margin_rates = [default_margin] + [o['rate'] for o in category_overrides]
        min_margin = min(min_margin_rates) if min_margin_rates else default_margin

        params = {
            'brand': brand,
            'vat': float(config_in.get('VAT_RATE', config_in.get('vat_rate', 0.23))),
            'default_margin': default_margin,
            'min_margin': min_margin,
            'category_overrides': category_overrides,
            'use_n8n_margin': False,  # Pipeline should calculate margin from rules
            'CLUSTER_THRESHOLD': float(config_in.get('CLUSTER_THRESHOLD', 1.5)),
        }

        print(f"[EXTRACT] Fetched: Feed={len(feed_raw)}, Items={len(ga4_items_raw)}, LP={len(ga4_lp_raw)}, Meta={len(meta_raw)}")

        # Convert and prepare data using existing mappers
        # We need to map raw data from API to expected internal names using _prepare_X.
        # Note: The API clients currently output data resembling the CSV formats (e.g. 'Item ID' or 'Landing page + query string').
        # Since _prepare_X maps from n8n-normalized names, we need to carefully pass raw format.
        # Actually our API clients ALREADY return the exact same column names as the CSVs!
        # And the pipeline (`join_and_enrich_data`) expects CSV-like names!
        # Wait, if we pass it directly to `join_and_enrich_data`, it expects CSV names.
        # `process()` uses `_prepare_feed()` to map n8n names to CSV names.
        # Here we already have CSV like names. But let's check `parse_product_feed_xml_from_url`.
        # It creates `feed_title`, `feed_category`, etc. - this is EXACTLY what `join_and_enrich_data` expects.
        
        if feed_raw.empty and meta_raw.empty:
             return JSONResponse(content=[])

        # Join & Enrich
        df, threshold_params = join_and_enrich_data(feed_raw, ga4_items_raw, ga4_lp_raw, meta_raw, params)
        params.update(threshold_params)

        # Run Logic (Waterfall)
        result_df = run_pipeline_logic(df, params)

        # Filter to gold-standard columns
        result_df = _filter_output(result_df)

        print(f"[EXTRACT] Output: {len(result_df)} rows")

        # Output
        result = json.loads(result_df.to_json(orient='records', date_format='iso'))
        return JSONResponse(content=result)

    except Exception as e:
        error_response = {
            "error": str(e),
            "trace": traceback.format_exc()
        }
        with open("clean_traceback.txt", "w") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_response)
