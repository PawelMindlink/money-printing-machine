import pandas as pd
import json
import os
import sys

# Add src to path if needed to import ingest_normalized
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
try:
    from ingest_normalized import normalize_url
except ImportError:
    # Try parent directory if running from src
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from ingest_normalized import normalize_url

# --- CONFIG ---
BASE_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine"
OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
CONFIG_PATH = os.path.join(BASE_DIR, "business_logic.json")

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Transform list of clients into a dict for easy lookup
        if 'clients' in data:
            return {c['name']: c for c in data['clients']}
        return data.get('brands', {}) # Fallback

def run_landing_page_logic(brand, config):
    print(f"\nProcessing {brand}...")
    
    # 1. Load Data
    path = os.path.join(OUTPUT_DIR, brand, "Normalized")
    try:
        # Load available files
        meta_path = os.path.join(path, "meta_ads_clean.csv")
        if not os.path.exists(meta_path):
            print(f"Skipping {brand}, missing Meta Ads: {meta_path}")
            return
            
        meta = pd.read_csv(meta_path)
        
        feed_path = os.path.join(path, "feed_clean.csv")
        if os.path.exists(feed_path):
            feed = pd.read_csv(feed_path, dtype={'id': str})
        else:
            print(f"Warning: Feed not found for {brand}. Using without feed.")
            feed = pd.DataFrame(columns=['norm_url', 'cat', 'title', 'price'])

    except Exception as e:
        print(f"Error loading files for {brand}: {e}")
        return

    # Brand Config
    # Config is now a dict: {'Bushido': {...}, 'Iiyama': {...}}
    brand_conf = config.get(brand, {})
    
    vat_rate = brand_conf.get('vat_rate', 0.23)
    
    # Margin Config handling
    margin_conf = brand_conf.get('margin_config', {})
    default_margin = margin_conf.get('default_rate', 0.0)
    
    # Category overrides is a list of dicts: [{'category': 'X', 'rate': 0.Y}, ...]
    # Convert to dict for fast lookup
    cat_overrides_list = margin_conf.get('category_overrides', [])
    cat_overrides = {item['category']: item['rate'] for item in cat_overrides_list}
    
    # 2. Prepare Base (Unique URLs from Meta)
    # Meta Ads is the source of spend.
    # Group by URL
    lp_df = meta.groupby('norm_url').agg({
        'Amount spent (PLN)': 'sum',
        'Purchases': 'sum', 
        'Purchases conversion value': 'sum'
    }).reset_index()
    
    # 3. Enrich with Feed (Product Context)
    # Handle duplicate URLs in feed (take first)
    feed_dedup = feed.drop_duplicates(subset=['norm_url'])
    
    # Merge
    merged = pd.merge(lp_df, feed_dedup[['norm_url', 'cat', 'title', 'price']], on='norm_url', how='left')
    
    # 4. Logic & Metrics
    
    def get_margin_pct(row):
        if pd.isna(row['cat']): return default_margin 
        
        # Exact match match category
        if row['cat'] in cat_overrides:
            return cat_overrides[row['cat']]
        
        return default_margin
        
    merged['gross_margin_pct'] = merged.apply(get_margin_pct, axis=1)
    
    # Financials
    # Net Revenue = Gross / (1 + VAT)
    merged['net_revenue'] = merged['Purchases conversion value'] / (1 + vat_rate)
    
    # COGS = Net Revenue * (1 - Margin %)
    merged['cogs'] = merged['net_revenue'] * (1 - merged['gross_margin_pct'])
    
    # Contribution Profit 1 = Net Revenue - COGS - Ad Spend
    merged['contribution_profit'] = merged['net_revenue'] - merged['cogs'] - merged['Amount spent (PLN)']
    
    # ROAS
    merged['roas'] = merged['Purchases conversion value'] / merged['Amount spent (PLN)'].replace(0, 1)

    # 5. Save
    out_file = os.path.join(OUTPUT_DIR, brand, "Landing_Page_Report.csv")
    merged.to_csv(out_file, index=False)
    print(f"Saved: {out_file}")

if __name__ == "__main__":
    if not os.path.exists(CONFIG_PATH):
        print(f"CRITICAL: Config file not found at {CONFIG_PATH}")
    else:
        config = load_config()
        brands = ["Bushido", "Iiyama", "Koszulkowy"]
        for b in brands:
            run_landing_page_logic(b, config)
