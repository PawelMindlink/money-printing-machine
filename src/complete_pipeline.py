import pandas as pd
import os
import re
import xml.etree.ElementTree as ET
from io import StringIO
import sys
import json
from pathlib import Path
from ga4_api_client import fetch_ga4_data, fetch_ga4_items

# HARDCODED PATH TO CREDENTIALS (for n8n/local execution) - Overridable via Env Var
GA4_CREDS_PATH = os.environ.get("GA4_CREDS_PATH", r"c:\Users\Paweł\Documents\GitHub\ICP Research\Core\Configs\ga4_credentials.json")

# ============================================================================
# UTILS
# ============================================================================

def normalize_url(url):
    """Normalize URL for matching"""
    if pd.isna(url) or url == '':
        return ''
    url = str(url).lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    if '?' in url:
        url = url.split('?')[0]
    return url.rstrip('/')

def extract_path(url):
    """Extract path from URL for relative matching"""
    if pd.isna(url) or url == '':
        return ''
    url = str(url).lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    if '?' in url:
        url = url.split('?')[0]
    
    if '/' in url:
        if not url.startswith('/'):
            path = url[url.find('/'):]
        else:
            path = url
    else:
        path = '/' + url
        
    path = path.rstrip('/')
    if not path.startswith('/'):
        path = '/' + path
        
    # Standardize HTML extensions
    path = path.replace('.facebookads.html', '.html')
    path = path.replace('.facebook.html', '.html')
    return path

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
    """Parse Facebook/Google Product Feed XML"""
    if not os.path.exists(filepath):
        return pd.DataFrame()
        
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {'g': 'http://base.google.com/ns/1.0'}
    
    products = []
    for item in root.findall('.//item'):
        p = {
            'id': item.findtext('g:id', namespaces=ns),
            'title': item.findtext('g:title', namespaces=ns) or item.findtext('title'),
            'link': item.findtext('g:link', namespaces=ns) or item.findtext('link'),
            'category': item.findtext('g:google_product_category', namespaces=ns),
            'price': item.findtext('g:price', namespaces=ns)
        }
        p['norm_url'] = normalize_url(p['link'])
        p['path_key'] = extract_path(p['link'])
        products.append(p)
        
    return pd.DataFrame(products)

# ============================================================================
# PIPELINE - FEED-FIRST APPROACH
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
    
    tier_rules = full_config.get('tier_rules', {}).get('ga4', {})

    # 2. Load Feed
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    df = parse_product_feed_xml(feed_path)
    if df.empty:
        print(f"Error: Feed not found at {feed_path}")
        return None
    print(f"Loaded {len(df)} products from Feed")

    # 3. Enrich with Items (Metric Depth - Hybrid API/CSV)
    items_df = pd.DataFrame()
    items_source = "CSV"
    
    # Try API if Property ID exists
    prop_id = config.get('ga4_property_id')
    if prop_id and os.path.exists(GA4_CREDS_PATH):
        try:
            items_df = fetch_ga4_items(GA4_CREDS_PATH, prop_id, limit=100000)
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
            lp_df['path_key'] = lp_df[lp_col].apply(extract_path)
            # Ensure numeric columns for aggregation
            cols_to_sum = ['Sessions', 'Purchases', 'First time purchasers']
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

    # 5. Join Meta Ads
    meta_path = os.path.join(input_dir, brand, f"{brand_l}_meta_ads.csv")
    if os.path.exists(meta_path):
        meta_df = pd.read_csv(meta_path)
        meta_df['norm_url'] = meta_df['Link (ad settings)'].apply(normalize_url)
        meta_agg = meta_df.groupby('norm_url').agg({
            'Amount spent (PLN)': 'sum',
            'Purchases': 'sum',
            'Purchases conversion value': 'sum'
        }).reset_index()
        meta_agg.columns = ['norm_url', 'meta_spend', 'meta_purchases', 'meta_revenue']
        df = pd.merge(df, meta_agg, on='norm_url', how='left')
        print(f"Enriched with Meta Ads (Match: {df['meta_spend'].notna().sum()})")

    # 6. CALCULATIONS & CLASSIFICATION
    vat = config.get('vat_rate', 0.23)
    margin_cfg = config.get('margin_config', {})
    default_margin = margin_cfg.get('default_rate', 0.1) # Fallback to 10% if totally missing
    category_overrides = margin_cfg.get('category_overrides', [])
    
    # Calculate Frequency (Transactions / First time purchasers)
    # Using LP purchases as primary transaction source for frequency calculation
    df['calc_frequency'] = df['Purchases'].fillna(0) / df['First time purchasers'].replace(0, 1)
    
    # Apply Margin Mapping
    def get_margin(row):
        cat = str(row['category']).lower()
        for override in category_overrides:
            if override['category'].lower() in cat:
                return override['rate']
        return default_margin

    df['gross_margin'] = df.apply(get_margin, axis=1)
    
    # CP = (Purch_Conv_Val / (1 + VAT) * Margin * Frequency) - Ad_Spend
    df['contribution_profit'] = (
        (df['meta_revenue'].fillna(0) / (1+vat)) * df['gross_margin'] * df['calc_frequency']
    ) - df['meta_spend'].fillna(0)
    
    # Meta Ads Classification
    def get_meta_class(row):
        if pd.isna(row['meta_spend']) or row['meta_spend'] == 0: return 'No Ads'
        return 'Profitable' if row['contribution_profit'] > 0 else 'Unprofitable'
    
    df['meta_class'] = df.apply(get_meta_class, axis=1)
    
    # GA4 Classification (BCG)
    def get_ga4_class(row):
        revenue = row['Item revenue'] if not pd.isna(row['Item revenue']) else 0
        freq = row['calc_frequency']
        
        for tier, rules in tier_rules.items():
            r_min = rules.get('revenue_min', 0)
            r_max = rules.get('revenue_max', float('inf'))
            f_min = rules.get('frequency_min', 0)
            f_max = rules.get('frequency_max', float('inf'))
            
            if r_min <= revenue <= r_max and f_min <= freq <= f_max:
                return tier.replace('_', ' ').title()
        
        return 'Slacker' # Final fallback
        
    df['ga4_class'] = df.apply(get_ga4_class, axis=1)
    
    # Priority Assignment (P1-P8)
    def get_priority(row):
        ga4 = row['ga4_class']
        meta = row['meta_class']
        
        if ga4 == 'Star' and meta == 'Profitable': return 'P1'
        if ga4 == 'Cash Cow' and meta == 'Profitable': return 'P2'
        if ga4 == 'Hidden Gem' and meta == 'Profitable': return 'P3'
        if ga4 == 'Star' and meta in ['No Ads', 'Unprofitable']: return 'P4'
        if ga4 == 'Cash Cow' and meta in ['No Ads', 'Unprofitable']: return 'P5'
        if ga4 == 'Hidden Gem' and meta == 'No Ads': return 'P6'
        if ga4 in ['Ignore', 'Slacker'] and meta == 'Profitable': return 'P7'
        return 'P8'

    df['priority'] = df.apply(get_priority, axis=1)
    
    # Save Results
    out_dir = os.path.join(output_dir, brand)
    os.makedirs(out_dir, exist_ok=True)
    df.to_csv(os.path.join(out_dir, "Landing_Page_Final.csv"), index=False)
    
    skipped = df[df['priority'] == 'P8']
    skipped.to_csv(os.path.join(out_dir, "Produkty_Pominięte.csv"), index=False)
    
    return df

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python complete_pipeline.py <BrandName>")
        sys.exit(1)
        
    brand = sys.argv[1]
    config_path = 'business_logic.json'
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            full_cfg = json.load(f)
        run_pipeline(brand, "Input", "Output", full_cfg)
    else:
        print(f"Error: {config_path} not found!")
