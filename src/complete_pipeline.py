
import pandas as pd
import os
import re
import xml.etree.ElementTree as ET
from io import StringIO
import sys
import json
from pathlib import Path
from ga4_api_client import fetch_ga4_data, fetch_ga4_items
import business_logic_layer as bl

# HARDCODED PATH TO CREDENTIALS (for n8n/local execution) - Overridable via Env Var
GA4_CREDS_PATH = os.environ.get("GA4_CREDS_PATH", r"c:\Users\Paweł\Documents\GitHub\ICP Research\Core\Configs\ga4_credentials.json")

# ============================================================================
# UTILS
# ============================================================================

def load_ga4_csv(filepath):
    """Load GA4 CSV by dynamically finding the header row"""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return pd.DataFrame()
        
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    header_idx = -1
    keywords = ['Item name', 'Item ID', 'Landing page', 'landingPage', 'Page path']
    
    for i, line in enumerate(lines):
        if any(kw in line for kw in keywords):
            header_idx = i
            break
            
    if header_idx == -1:
        for i, line in enumerate(lines):
            if not line.strip().startswith('#') and line.strip() != '':
                header_idx = i
                break
                
    if header_idx == -1:
        return pd.DataFrame()

    header_line = lines[header_idx]
    data_lines = lines[header_idx+1:]
    
    filtered_data = []
    for line in data_lines:
        clean_line = line.strip()
        if clean_line and not any(total_marker in clean_line.lower() for total_marker in ['grand total', 'total']):
            filtered_data.append(line)
            
    csv_str = header_line + ''.join(filtered_data)
    df = pd.read_csv(StringIO(csv_str))
    
    if not df.empty:
        first_col = df.columns[0]
        df = df[df[first_col].notna()].copy()
        
    return df

def parse_product_feed_xml(filepath):
    """Parse Facebook/Google Product Feed XML - EXTENDED with all useful fields"""
    if not os.path.exists(filepath):
        print(f"Feed not found: {filepath}")
        return pd.DataFrame()
        
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {'g': 'http://base.google.com/ns/1.0'}
    
    products = []
    for item in root.findall('.//item'):
        # Extract Category properly (Iiyama case: '305')
        cat_raw = item.findtext('g:google_product_category', namespaces=ns)
        # Mapping for known obscur codes
        if cat_raw == '305': 
            cat_clean = 'Monitors'
        else:
            cat_clean = cat_raw

        p = {
            # Core identifiers
            'id': item.findtext('g:id', namespaces=ns),
            'title': item.findtext('g:title', namespaces=ns) or item.findtext('title'),
            'link': item.findtext('g:link', namespaces=ns) or item.findtext('link'),
            
            # Categories
            'category': cat_clean,
            'product_type': item.findtext('g:product_type', namespaces=ns),
            
            # Pricing
            'price': item.findtext('g:price', namespaces=ns),
            
            # Media & Creative (for copywriter/creative team)
            'image_link': item.findtext('g:image_link', namespaces=ns),
            'description': item.findtext('description') or item.findtext('g:description', namespaces=ns),
            
            # Brand & Identification
            'brand': item.findtext('g:brand', namespaces=ns),
            'gtin': item.findtext('g:gtin', namespaces=ns),
            'mpn': item.findtext('g:mpn', namespaces=ns),
            
            # Availability
            'availability': item.findtext('g:availability', namespaces=ns),
        }
        p['norm_url'] = bl.normalize_url(p['link'])
        p['path_key'] = bl.extract_path(p['link'])
        products.append(p)
        
    return pd.DataFrame(products)


# ============================================================================
# PIPELINE - FEED-FIRST APPROACH (Enriched with Category Ads)
# ============================================================================

def run_pipeline(brand, input_dir, output_dir, full_config):
    print(f"\n>>> Running Optimized Pipeline for: {brand}")
    brand_l = brand.lower()
    
    # 1. Get Brand Setup
    clients_list = full_config.get('clients', [])
    config = next((c for c in clients_list if c['name'].lower() == brand.lower()), {})
    if not config:
        print(f"Error: Brand configuration for {brand} not found in business_logic.json!")
        return None
    
    # 2. Load Feed
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    df = parse_product_feed_xml(feed_path)
    # If feed is empty, we must create an empty DF with correct columns for Outer Join to work
    if df.empty:
        print(f"Warning: Feed empty or missing at {feed_path}. Proceeding with Ad Data only.")
        df = pd.DataFrame(columns=['id', 'title', 'link', 'norm_url', 'path_key', 'price', 'brand', 'category'])
    else:
        print(f"Loaded {len(df)} products from Feed")

    # 3. Enrich with Items (Metric Depth - Hybrid API/CSV)
    items_df = pd.DataFrame()
    items_source = "CSV"
    
    # Try API if Property ID exists
    prop_id = config.get('ga4_property_id')
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try:
            items_df = fetch_ga4_items(GA4_CREDS_PATH, prop_id, limit=50000)
            if not items_df.empty:
                items_source = "API"
        except Exception as e:
            print(f"Items API failed: {e}. Falling back to CSV.")
            
    # Fallback to CSV
    if items_df.empty:
        items_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_items_freeform.csv")
        if not os.path.exists(items_path):
            items_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_items.csv")
            
        if os.path.exists(items_path):
            items_df = load_ga4_csv(items_path)
            
    # Process Items if loaded
    if not items_df.empty:
        items_df['Item ID'] = items_df['Item ID'].astype(str)
        def get_clean_id(id_val):
            return str(id_val).split('-')[0].split('.')[0]
        items_df['Clean ID'] = items_df['Item ID'].apply(get_clean_id)
        
        # Ensure 'id' column exists in df even if empty
        if 'id' not in df.columns: df['id'] = pd.NA
        df['id'] = df['id'].astype(str)
        
        items_agg = items_df.groupby('Clean ID').agg({
            'Items viewed': 'sum',
            'Items purchased': 'sum',
            'Item revenue': 'sum'
        }).reset_index()
        
        df = pd.merge(df, items_agg, left_on='id', right_on='Clean ID', how='left')
        print(f"Enriched with GA4 Items ({items_source}, Match: {df['Clean ID'].notna().sum()})")


    # 4. Enrich with Landing Pages (Session Depth - Hybrid API/CSV)
    lp_df = pd.DataFrame()
    ga4_source = "CSV"
    
    # Try API if Property ID exists
    prop_id = config.get('ga4_property_id')
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try:
            print(f"Fetching GA4 Data via API (Property: {prop_id})...")
            # Limit 100k rows to cover Koszulkowy case
            lp_df = fetch_ga4_data(GA4_CREDS_PATH, prop_id, limit=100000)
            if not lp_df.empty:
                ga4_source = "API"
        except Exception as e:
            print(f"API Fetch Failed: {e}. Falling back to CSV.")
            
    # Fallback to CSV if API failed or not configured
    if lp_df.empty:
        lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp_freeform.csv")
        if not os.path.exists(lp_path):
            lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp.csv")
            
        if os.path.exists(lp_path):
            print(f"Loading GA4 LP from CSV: {lp_path}")
            lp_df = load_ga4_csv(lp_path)
            
    # Process if data loaded
    if not lp_df.empty:
        lp_col = next((c for c in ['Landing page', 'Landing page + query string', 'landingPage'] if c in lp_df.columns), None)
        
        if lp_col:
            lp_df['path_key'] = lp_df[lp_col].apply(bl.extract_path)
            # Ensure numeric columns for aggregation
            # 'Purchase revenue' comes from API (renamed from Item revenue in client) or CSV
            cols_to_sum = ['Sessions', 'Purchases', 'First time purchasers', 'Purchase revenue']
            
            # Normalization for CSV/API differences
            if 'Purchase revenue' not in lp_df.columns:
                # Try finding similar columns
                rev_col = next((c for c in lp_df.columns if 'revenue' in c.lower() and 'purchase' in c.lower()), None)
                if rev_col:
                    lp_df.rename(columns={rev_col: 'Purchase revenue'}, inplace=True)
                else:
                    lp_df['Purchase revenue'] = 0
            
            for c in cols_to_sum:
                if c not in lp_df.columns:
                    lp_df[c] = 0
                else:
                    lp_df[c] = pd.to_numeric(lp_df[c], errors='coerce').fillna(0)
                    
            lp_agg = lp_df.groupby('path_key')[cols_to_sum].sum().reset_index()
            
            df = pd.merge(df, lp_agg, on='path_key', how='left')
            print(f"Enriched with GA4 Sessions ({ga4_source}, Match: {df['Sessions'].notna().sum()})")
    else:
        print("Warning: No GA4 Data loaded (API or CSV).")

    # 5. Join Meta Ads (OUTER JOIN to Capture Category Ads)
    meta_path = os.path.join(input_dir, brand, f"{brand_l}_meta_ads.csv")
    if os.path.exists(meta_path):
        meta_df = pd.read_csv(meta_path)
        meta_df['norm_url'] = meta_df['Link (ad settings)'].apply(bl.normalize_url)
        
        # Safe aggregation of potential missing columns
        agg_dict = {
            'Amount spent (PLN)': 'sum',
            'Purchases': 'sum',
            'Purchases conversion value': 'sum'
        }
        
        # Only aggregate existing cols
        agg_dict = {k:v for k,v in agg_dict.items() if k in meta_df.columns}

        meta_agg = meta_df.groupby('norm_url').agg(agg_dict).reset_index()
        # Rename strictly
        rename_map = {
            'Amount spent (PLN)': 'meta_spend',
            'Purchases': 'meta_purchases',
            'Purchases conversion value': 'meta_revenue'
        }
        meta_agg.rename(columns=rename_map, inplace=True)
        
        # Use OUTER JOIN to include Ads that don't match Feed (Category/General)
        df = pd.merge(df, meta_agg, on='norm_url', how='outer')
        print(f"Enriched with Meta Ads (Outer Join - Total Rows: {len(df)})")
        
        # --- SYNTHETIC PRODCUT CREATION FOR UNMATCHED ADS ---
        # Rows with meta_spend > 0 but no 'id' (Product ID)
        if 'meta_spend' in df.columns:
            mask_synthetic = (df['id'].isna()) & (df['meta_spend'] > 0)
            
            if mask_synthetic.sum() > 0:
                print(f"Creating {mask_synthetic.sum()} Synthetic Products for Unmatched Ads (Category Pages)")
                
                # Derive Title from URL
                def derive_title(url):
                    if pd.isna(url): return "Unknown Ad"
                    path = url.split('/')[-1]
                    path = path.replace('-', ' ').replace('.html', '').replace('_', ' ')
                    return f"Ad: {path.title()[:50]}"
                
                df.loc[mask_synthetic, 'title'] = df.loc[mask_synthetic, 'norm_url'].apply(derive_title)
                df.loc[mask_synthetic, 'category'] = 'General / Category'
                df.loc[mask_synthetic, 'id'] = df.loc[mask_synthetic, 'norm_url'].apply(lambda x: f"SYN-{hash(x) % 10000}")
                df.loc[mask_synthetic, 'price'] = '0 PLN' # Set safe defaults
                df.loc[mask_synthetic, 'brand'] = brand
            
    # 6. CALCULATIONS & CLASSIFICATION
    if 'meta_spend' not in df.columns: df['meta_spend'] = 0
    if 'meta_revenue' not in df.columns: df['meta_revenue'] = 0
    
    vat = config.get('vat_rate', 0.23)
    margin_cfg = config.get('margin_config', {})
    default_margin = margin_cfg.get('default_rate', 0.1) 
    category_overrides = margin_cfg.get('category_overrides', [])
    
    # Calculate Frequency 
    if 'Purchases' not in df.columns: df['Purchases'] = 0
    if 'First time purchasers' not in df.columns: df['First time purchasers'] = 0
    
    df['calc_frequency'] = df['Purchases'].fillna(0) / df['First time purchasers'].replace(0, 1)
    
    # Apply Margin Mapping
    df['gross_margin'] = df.apply(lambda row: bl.calculate_gross_margin(row, default_margin, category_overrides), axis=1)
    
    # PRICE CLUSTERING
    df['price_numeric'] = pd.to_numeric(df['price'].astype(str).str.replace(' PLN', '').str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0)
    
    # Apply per Margin Group
    df['price_cluster'] = "Other"
    for margin in df['gross_margin'].unique():
        mask = df['gross_margin'] == margin
        if mask.sum() > 0:
            clusters = bl.assign_price_cluster(df.loc[mask])
            df.loc[mask, 'price_cluster'] = clusters

    # CP Calculation
    df['contribution_profit'] = bl.calculate_contribution_profit(
        df['meta_revenue'].fillna(0),
        vat,
        df['gross_margin'],
        df['calc_frequency'],
        df['meta_spend'].fillna(0)
    )
    
    # Meta Ads Classification
    df['meta_class'] = df.apply(lambda row: bl.classify_meta_ads(row['contribution_profit'], row['meta_spend']), axis=1)
    
    # ARPU
    rev_source = 'Purchase revenue' if 'Purchase revenue' in df.columns else 'Item revenue'
    user_col = 'Users' if 'Users' in df.columns else 'Sessions'
    if rev_source not in df.columns: df[rev_source] = 0
    if user_col not in df.columns: df[user_col] = 1
    
    df['arpu'] = df[rev_source].fillna(0) / df[user_col].replace(0, pd.NA)
    df['arpu'] = df['arpu'].fillna(0)
    
    # GA4 Classification
    sess_col = 'Sessions'
    if sess_col not in df.columns: df[sess_col] = 0
    
    # Calculate thresholds
    # We need to replicate non_zero_quantile logic or exposing it in BL
    # For now, let's keep it here but using quantile
    def non_zero_quantile(series, q=0.75):
        valid = series[series > 0]
        if valid.empty: return 0
        return valid.quantile(q)
        
    trans_col = 'Purchases'
    arpu_col = 'arpu'
    
    trans_75 = non_zero_quantile(df[trans_col], 0.75)
    arpu_75 = non_zero_quantile(df[arpu_col], 0.75)
    
    thresholds = {
        'min_activity': df[sess_col].quantile(0.25) if not df.empty else 0,
        'trans_75': trans_75,
        'arpu_75': arpu_75
    }
    
    print(f"Classification Thresholds (Active Products P75): Trans≥{trans_75:.0f}, ARPU≥{arpu_75:.2f}")
    
    df['ga4_class'] = df.apply(lambda row: bl.classify_ga4_product(
        row.get(sess_col, 0),
        row.get(trans_col, 0),
        row.get(arpu_col, 0),
        thresholds
    ), axis=1)

    # Priority Assignment
    df['priority'] = df.apply(lambda row: bl.determine_priority(row['ga4_class'], row['meta_class']), axis=1)
    
    # =================
    # NEW METRICS (v2.0)
    # =================
    
    # IsProduct Flag
    df['is_product'] = df.apply(lambda row: bl.is_product_page(row.get('link', ''), row.get('id', None)), axis=1)
    
    # Bid Cap & Cost Cap
    df['bid_cap'] = df.apply(lambda row: bl.calculate_bid_cap(row['price_numeric'], vat, row['gross_margin']), axis=1)
    df['cost_cap'] = df['bid_cap'].apply(lambda bc: bl.calculate_cost_cap(bc))
    
    # ROAS Metrics
    df['critical_roas'] = df['bid_cap'].apply(lambda bc: bl.calculate_critical_roas(bc))
    df['scaling_roas'] = df.apply(
        lambda row: bl.calculate_scaling_roas(vat, row['gross_margin'], row['calc_frequency'] if row['calc_frequency'] > 0 else 1),
        axis=1
    )
    
    # ARPIV (if items data available)
    if 'Items viewed' in df.columns and 'Item revenue' in df.columns:
        df['arpiv'] = df.apply(lambda row: bl.calculate_arpiv(row['Item revenue'], row['Items viewed']), axis=1)
    else:
        df['arpiv'] = 0.0
    
    # Ensure Users column exists for output
    if 'Users' not in df.columns:
        df['Users'] = df.get('Sessions', 0)
    
    # Save Results
    out_dir = os.path.join(output_dir, brand)
    os.makedirs(out_dir, exist_ok=True)
    
    # Remove technical columns
    cols_to_drop = ['path_key', 'norm_url', 'Clean ID', 'price_numeric', 'temp_cluster_id']
    df_final = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    
    # Order columns nicely if possible for readability
    cols = list(df_final.columns)
    prio_cols = ['id', 'title', 'brand', 'category', 'price', 
                 'meta_class', 'ga4_class', 'priority', 'contribution_profit', 
                 'meta_spend', 'meta_revenue', 'meta_purchases',
                 'gross_margin', 'calc_frequency']
    
    # Sort columns: Prio first, then rest
    sorted_cols = [c for c in prio_cols if c in cols] + [c for c in cols if c not in prio_cols]
    df_final = df_final[sorted_cols]
    
    df_final.to_csv(os.path.join(out_dir, f"{brand}_Landing_Page_Final.csv"), index=False)
    
    skipped = df[df['priority'] == 'P8']
    skipped.to_csv(os.path.join(out_dir, f"{brand}_Produkty_Pominięte.csv"), index=False)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        brand_arg = sys.argv[1]
        
        # Load Config
        with open("business_logic.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            
        run_pipeline(brand_arg, "Input", "Output", config)
    else:
        print("Usage: python complete_pipeline.py <BrandName>")
