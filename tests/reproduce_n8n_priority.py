
import sys
import os
import pandas as pd
import json

# Add project root to path (2 levels up if in tests/ subdir, but logic below handles it robustly)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Assert tests/ is one level deep
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import main logic
from main import _remap_df, _prepare_feed, _prepare_items, _prepare_lp, _prepare_meta, FEED_REMAP, ITEMS_REMAP, LP_REMAP, META_REMAP, process, _filter_output, GOLD_STANDARD_COLS
from src.complete_pipeline import join_and_enrich_data, run_pipeline_logic
import src.business_logic_layer as bl
from src.data_loader import load_ga4_csv

# Configuration for Simulation
BRAND = "Iiyama"
# Paths relative to project root
INPUT_DIR = os.path.join(project_root, "Input", "Iiyama")
OUTPUT_FILE = os.path.join(project_root, "Output", "Iiyama", "n8n_simulation_result.csv")

def load_local_data():
    """Load local CSVs mimicking n8n inputs."""
    data = {}
    
    # helper
    def load(fname):
        path = os.path.join(INPUT_DIR, fname)
        if os.path.exists(path):
            if path.endswith('.xml'):
                # Special handling for XML -> emulate n8n JSON Structure
                import xml.etree.ElementTree as ET
                tree = ET.parse(path)
                root = tree.getroot()
                ns = {'g': 'http://base.google.com/ns/1.0'}
                products = []
                for item in root.findall('.//item'):
                    link = item.findtext('g:link', namespaces=ns) or item.findtext('link')
                    p = {
                        'feed_id': item.findtext('g:id', namespaces=ns),
                        'feed_title': item.findtext('g:title', namespaces=ns) or item.findtext('title'),
                        'feed_price': item.findtext('g:price', namespaces=ns).replace(' PLN', '').replace(',', '.'), # n8n sends float/cleaned?
                        'feed_link': link,
                        'feed_category': item.findtext('g:google_product_category', namespaces=ns),
                        # n8n computes norm_url_path
                        'norm_url_path': bl.normalize_url(link).replace('https://', '').replace('http://', '').split('/', 1)[-1] if link else ''
                    }
                    products.append(p)
                return products
            elif path.endswith('.csv'):
                return pd.read_csv(path).to_dict(orient='records')
        return []

    data['feed'] = load(f"{BRAND.lower()}_product_feed.xml")
    
    # Meta Ads - mimic n8n structure
    # Use load_ga4_csv logic for Meta Ads too as they might have headers
    meta_raw = load_ga4_csv(os.path.join(INPUT_DIR, f"{BRAND.lower()}_meta_ads.csv"))
    if meta_raw.empty:
        # Fallback to standard read if clean
        try:
            meta_raw = pd.read_csv(os.path.join(INPUT_DIR, f"{BRAND.lower()}_meta_ads.csv"))
        except:
            pass

    # Rename commonly used keys to match what n8n sends raw
    # n8n normalize step maps to: meta_spend, meta_purch, meta_rev, meta_url
    meta_sim = []
    if not meta_raw.empty:
        for _, row in meta_raw.iterrows():
            meta_sim.append({
                'meta_ad_id': row.get('Ad ID', ''),
                'meta_ad_name': row.get('Ad Name', ''),
                'meta_url': row.get('Link (ad settings)', ''), # Crucial field
                'meta_spend': row.get('Amount spent (PLN)', 0),
                'meta_purch': row.get('Purchases', 0),
                'meta_rev': row.get('Purchases conversion value', 0),
            })
    data['meta_ads'] = meta_sim

    # GA4 Items
    items_raw = load_ga4_csv(os.path.join(INPUT_DIR, f"{BRAND.lower()}_ga4_items.csv"))
    # n8n normalize maps to: ga4_item_id, ga4_item_views, ga4_item_rev, ga4_item_purch
    items_sim = []
    if not items_raw.empty:
        for _, row in items_raw.iterrows():
            items_sim.append({
                'ga4_item_id': row.get('Item ID'),
                'ga4_item_views': row.get('Items viewed', 0),
                'ga4_item_rev': row.get('Item revenue', 0),
                'ga4_item_purch': row.get('Items purchased', 0),
            })
    data['ga4_items'] = items_sim

    # GA4 LP
    lp_path = os.path.join(INPUT_DIR, f"{BRAND.lower()}_ga4_lp.csv")
    if not os.path.exists(lp_path):
        # Try finding file with similar name
        files = os.listdir(INPUT_DIR)
        for f in files:
            if 'ga4_lp' in f and f.endswith('.csv'):
                lp_path = os.path.join(INPUT_DIR, f)
                break
    
    lp_raw = load_ga4_csv(lp_path)
    # n8n normalize maps to: ga4_lp_url, ga4_sessions, ga4_revenue, ga4_trans...
    lp_sim = []
    if not lp_raw.empty:
        # Determine LP column name
        lp_col_name = 'Landing page'
        if 'Landing page' not in lp_raw.columns and 'Landing page + query string' in lp_raw.columns:
            lp_col_name = 'Landing page + query string'
            
        for _, row in lp_raw.iterrows():
            lp_sim.append({
                'ga4_lp_url': row.get(lp_col_name, ''),
                'ga4_sessions': row.get('Sessions', 0),
                'ga4_revenue': row.get('Purchase revenue', 0),
                'ga4_trans': row.get('Purchases', 0),
                'ga4_users': row.get('Users', 0),
                'ga4_first_time_purchasers': row.get('First time purchasers', 0)
            })
    data['ga4_lp'] = lp_sim

    # Config
    data['config'] = {
        'brand': BRAND,
        'vat_rate': 0.23,
        'default_margin': 0.10,
        'margin_rules': [] # Simplified for simulation
    }
    
    return data

def run_simulation():
    print("--- Loading Local Data (Simulating n8n Payload) ---")
    payload = load_local_data()
    print(f"Feed: {len(payload['feed'])}")
    print(f"Meta: {len(payload['meta_ads'])}")
    print(f"Items: {len(payload['ga4_items'])}")
    print(f"LP: {len(payload['ga4_lp'])}")
    
    print("\n--- Running Logic via main.py functions ---")
    # We call the functions directly to avoid mocking FastAPI request/response objects if possible
    # But main.process takes a dict payload! perfect.
    
    # We need to Bypass JSONResponse wrap if possible, or just decode it.
    # main.process returns a JSONResponse object which holds bytes.
    
    # Actually, let's just invoke the logic directly using the payload
    # This mirrors main.process internals
    
    data = payload
    feed_data = data.get('feed', [])
    meta_data = data.get('meta_ads', [])
    ga4_items_data = data.get('ga4_items', [])
    ga4_lp_data = data.get('ga4_lp', [])
    config_in = data.get('config', {})
    
    feed_df = _prepare_feed(pd.DataFrame(feed_data) if feed_data else pd.DataFrame())
    meta_df = _prepare_meta(pd.DataFrame(meta_data) if meta_data else pd.DataFrame())
    items_df = _prepare_items(pd.DataFrame(ga4_items_data) if ga4_items_data else pd.DataFrame())
    lp_df = _prepare_lp(pd.DataFrame(ga4_lp_data) if ga4_lp_data else pd.DataFrame())
    
    category_overrides = []
    default_margin = float(config_in.get('default_margin', 0.10))
    min_margin = default_margin # Simplified
    
    params = {
        'brand': config_in.get('brand', 'Simulation'),
        'vat': float(config_in.get('vat_rate', 0.23)),
        'default_margin': default_margin,
        'min_margin': min_margin,
        'category_overrides': category_overrides,
        'use_n8n_margin': True, 
    }
    
    print(f"Prepared Feed columns: {list(feed_df.columns)}")
    print(f"Prepared Meta columns: {list(meta_df.columns)}")
    
    # Join & Enrich
    print("\n[DEBUG] Feed path_key sample:")
    print(feed_df['path_key'].head(10).tolist() if 'path_key' in feed_df.columns else "No path_key")
    print("\n[DEBUG] LP path_key sample:")
    print(lp_df['path_key'].head(10).tolist() if 'path_key' in lp_df.columns else "No path_key")
    
    # Check for direct matches
    if 'path_key' in feed_df.columns and 'path_key' in lp_df.columns:
        feed_keys = set(feed_df['path_key'].dropna())
        lp_keys = set(lp_df['path_key'].dropna())
        intersection = feed_keys.intersection(lp_keys)
        print(f"\n[DEBUG] Keys intersection count: {len(intersection)}")
        print(f"[DEBUG] Feed unique keys: {len(feed_keys)}")
        print(f"[DEBUG] LP unique keys: {len(lp_keys)}")
        if len(intersection) < 10:
             print(f"Sample Intersection: {list(intersection)}")

    df, threshold_params = join_and_enrich_data(feed_df, items_df, lp_df, meta_df, params)
    params.update(threshold_params)
    
    # Run Logic
    result_df = run_pipeline_logic(df, params)
    
    result_df = _filter_output(result_df)
    
    print(f"\n--- Simulation Result ---")
    print(f"Total Rows: {len(result_df)}")
    if 'calc_priority' in result_df.columns:
        print(f"Priority Distribution:\n{result_df['calc_priority'].value_counts().sort_index()}")
    else:
        print("ERROR: calc_priority not found in result!")
        
    # Save output
    result_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_simulation()
