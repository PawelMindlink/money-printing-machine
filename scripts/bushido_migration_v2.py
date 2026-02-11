import pandas as pd
import xml.etree.ElementTree as ET
import os
import json
import re

# --- CONFIGURATION ---
INPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Input/Bushido"
OUTPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Output/Bushido"
BUSINESS_LOGIC_PATH = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/business_logic.json"
PLN_TO_EUR = 4.30

# File Paths
FEED_PATH = os.path.join(INPUT_DIR, "Bushido Feed DE.txt")
GA4_LP_PATH = os.path.join(INPUT_DIR, "bushido_ga4_lp.csv")
GA4_ITEMS_PATH = os.path.join(INPUT_DIR, "bushido_ga4_items.csv")
META_ADS_PATH = os.path.join(INPUT_DIR, "bushido_meta_ads.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- UTILS ---
def normalize_url(url):
    if not isinstance(url, str): return ""
    url = url.split("?")[0].replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
    if url.startswith("/"): url = "bushido-sport.pl" + url # Default domain for relative URLs from GA4
    return url

def extract_id_from_url(url):
    """Extracts numeric product ID from Polish or German Bushido URLs."""
    if not isinstance(url, str): return None
    
    # EXCLUSIONS: Skip known Category/Blog patterns
    if '_m_' in url or '/blog/' in url: return None

    # Pattern: product-pol-123-... or /product-pol-123...
    match = re.search(r'product-(?:pol|ger|eng|uni)-(\d+)', url)
    if match: return match.group(1)
    
    # Simple ID at end of path (ensure it's not a long FB/Google ID)
    match = re.search(r'[/-](\d+)$', url)
    if match and len(match.group(1)) <= 6: return match.group(1)

    # Convert query params id=123
    match = re.search(r'[?&]id=(\d+)', url)
    if match and len(match.group(1)) <= 6: return match.group(1)
    
    # Fallback for IDs that might just be numeric in the path segment
    match = re.search(r'/(\d+)-', url)
    if match and len(match.group(1)) <= 6: return match.group(1)
    
    # Bushido specific: /pr/123/
    match = re.search(r'/pr/(\d+)/', url)
    if match: return match.group(1)

    return None

def clean_id(val):
    """Standardizes product IDs to stripped numeric strings, handling float formats like '123.0'."""
    try:
        if pd.isna(val): return None
        # Handle '123.0' case
        return str(int(float(val)))
    except:
        return str(val).strip() if val else None

def get_url_category_margin(url):
    """
    Parses URL to assign margin based on Category Keywords (PL/DE).
    Returns: (margin, category_name)
    """
    if not isinstance(url, str): return 0.40, "General Landing Page"
    url_lower = url.lower()
    
    # 1. Social / Info / Policy (0.40)
    if any(x in url_lower for x in ['fb.com', 'facebook', 'instagram', 'policy', 'about', 'regulamin', 'zwroty']):
        return 0.40, "Social/Canvas Ad"
        
    # 2. Heavy Equipment (0.23)
    # PL: worki, worek, obciazenia, kamizelki, manekiny, gruszki, refleksowe
    # DE: sack, dummy, bob, weight, standing
    heavy_keywords = ['worki', 'worek', 'obciazenia', 'kamizelki', 'manekiny', 'gruszki', 'refleksowe',
                      'sack', 'dummy', 'bob', 'weight', 'standing']
    if any(kw in url_lower for kw in heavy_keywords):
        return 0.23, "Category: Heavy Equipment"
        
    # 3. High Margin Gear (0.58)
    # PL: rekawice, ochraniacze, odziez, buty, kask, szczeka, akcesoria, ekspandery, gumy
    high_margin_keywords = ['rekawice', 'ochraniacze', 'odziez', 'buty', 'kask', 'szczeka', 'akcesoria', 'ekspandery', 'gumy']
    if any(kw in url_lower for kw in high_margin_keywords):
        return 0.58, "Category: Fight Gear"
        
    # 4. Default
    return 0.40, "General Landing Page"

def get_margin(title, category_overrides, default_rate):
    title_lower = str(title).lower()
    # GOLD STANDARD KEYWORDS (German)
    # ['sack', 'boxsack', 'sandsack', 'wurfsack', 'dummy', 'bob']
    low_margin_keywords = ['sack', 'boxsack', 'sandsack', 'wurfsack', 'dummy', 'bob']
    for kw in low_margin_keywords:
        if kw in title_lower:
            return 0.23
            
    # Default high margin for everything else (Standard/Gear)
    return 0.58

# --- LOAD BUSINESS LOGIC ---
with open(BUSINESS_LOGIC_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

bushido_config = next(c for c in config['clients'] if c['name'] == 'Bushido')
# GOLD STANDARD FIX: Force German VAT 19%
VAT_RATE = 0.19 
MARGIN_DEFAULTS = bushido_config['margin_config']
TIER_RULES = config['tier_rules']['ga4']

# --- 1. PARSE FEED ---
print(">>> Parsing German Feed...")
feed_items = []
context = ET.iterparse(FEED_PATH, events=('end',))
for event, elem in context:
    if elem.tag.endswith('item'):
        item = {}
        for child in elem:
            tag = child.tag.split('}')[-1]
            if tag == 'id': item['feed_id'] = child.text
            elif tag == 'title': item['feed_title'] = child.text
            elif tag == 'brand': item['feed_brand'] = child.text
            elif tag == 'product_type': item['feed_category'] = child.text
            elif tag == 'link': item['feed_link'] = child.text
            elif tag == 'price':
                try:
                    # Expecting "164.99 EUR"
                    item['calc_gross_price'] = float(child.text.split()[0])
                except:
                    item['calc_gross_price'] = 0.0
        
        if 'feed_id' in item:
            item['is_product'] = True
            item['is_price_inferred'] = False
            item['norm_url'] = normalize_url(item.get('feed_link', ''))
            feed_items.append(item)
        elem.clear()

df_feed = pd.DataFrame(feed_items)
print(f"DEBUG: Feed rows parsed: {len(df_feed)}")
if 'feed_id' not in df_feed.columns:
    print("WARNING: No 'feed_id' found in feed items. Initializing empty columns.")
    for col in ['feed_id', 'feed_title', 'feed_brand', 'feed_category', 'feed_link', 'calc_gross_price', 'norm_url']:
        if col not in df_feed.columns: df_feed[col] = None
else:
    df_feed['feed_id'] = df_feed['feed_id'].astype(str).str.strip()
    # Deduplicate Feed: Keep the one with the highest price as the representative
    df_feed = df_feed.sort_values('calc_gross_price', ascending=False).drop_duplicates(subset=['feed_id'])

# --- 2. PARSE GA4 ITEMS ---
print(">>> Parsing GA4 Items (PLN)...")
# Use index_col=False to prevent shift from the total row which has an empty 1st column
df_ga4_items = pd.read_csv(GA4_ITEMS_PATH, skiprows=6, index_col=False)

# Drop "Grand total" row: it's the first data row and usually has NaN in col 0
if not df_ga4_items.empty and pd.isna(df_ga4_items.iloc[0, 0]):
    df_ga4_items = df_ga4_items.iloc[1:]

df_ga4_items = df_ga4_items.rename(columns={
    'Item ID': 'feed_id_raw',
    'Items viewed': 'ga4item_views',
    'Item revenue': 'ga4item_revenue'
})
# Standardize feed_id
df_ga4_items['feed_id'] = df_ga4_items['feed_id_raw'].apply(clean_id)
# Convert to EUR and ensures numeric
df_ga4_items['ga4item_revenue'] = pd.to_numeric(df_ga4_items['ga4item_revenue'], errors='coerce').fillna(0) / PLN_TO_EUR
df_ga4_items['ga4item_views'] = pd.to_numeric(df_ga4_items['ga4item_views'], errors='coerce').fillna(0)

# AGGREGATE GA4 ITEMS to avoid duplication in join
df_ga4_items_agg = df_ga4_items.dropna(subset=['feed_id']).groupby('feed_id').agg({
    'ga4item_views': 'sum',
    'ga4item_revenue': 'sum'
}).reset_index()

# --- 3. PARSE GA4 LANDING PAGE ---
print(">>> Parsing GA4 Landing Pages (PLN)...")
# Use index_col=False to prevent shift
df_ga4_lp = pd.read_csv(GA4_LP_PATH, skiprows=6, index_col=False)

# Drop "Grand total" row: it's the first data row and usually has NaN in col 0
if not df_ga4_lp.empty and pd.isna(df_ga4_lp.iloc[0, 0]):
    df_ga4_lp = df_ga4_lp.iloc[1:]

# Rename columns (GA4 LP usually has: Landing page, purchasers, revenue, purchases, sessions, arpu)
df_ga4_lp = df_ga4_lp.iloc[:, :6]
df_ga4_lp.columns = ['ga4_url', 'ga4lp_first_time_purchasers', 'ga4lp_revenue', 'ga4lp_purchases', 'ga4lp_sessions', 'arpu']

# Filter to product URLs (must contain '/' or 'product')
df_ga4_lp['ga4_url'] = df_ga4_lp['ga4_url'].astype(str)
df_ga4_lp = df_ga4_lp[df_ga4_lp['ga4_url'].str.contains('/', na=False)]

# Extract ID for joining
df_ga4_lp['ext_id'] = df_ga4_lp['ga4_url'].apply(extract_id_from_url)

# Convert to numeric safely
df_ga4_lp['ga4lp_revenue'] = pd.to_numeric(df_ga4_lp['ga4lp_revenue'], errors='coerce').fillna(0) / PLN_TO_EUR
df_ga4_lp['ga4lp_sessions'] = pd.to_numeric(df_ga4_lp['ga4lp_sessions'], errors='coerce').fillna(0)
df_ga4_lp['ga4lp_purchases'] = pd.to_numeric(df_ga4_lp['ga4lp_purchases'], errors='coerce').fillna(0)
df_ga4_lp['ga4lp_first_time_purchasers'] = pd.to_numeric(df_ga4_lp['ga4lp_first_time_purchasers'], errors='coerce').fillna(0)

# Aggregate by extracted ID
df_ga4_lp_agg = df_ga4_lp.dropna(subset=['ext_id']).groupby('ext_id').agg({
    'ga4lp_sessions': 'sum',
    'ga4lp_revenue': 'sum',
    'ga4lp_purchases': 'sum',
    'ga4lp_first_time_purchasers': 'sum'
}).reset_index().rename(columns={'ext_id': 'feed_id'})

# NEW: Aggregate GA4 LP by URL for synthetic rows (unmapped spend)
df_ga4_lp['norm_url'] = df_ga4_lp['ga4_url'].apply(normalize_url)
df_ga4_lp_url_agg = df_ga4_lp.groupby('norm_url').agg({
    'ga4lp_sessions': 'sum',
    'ga4lp_revenue': 'sum',
    'ga4lp_purchases': 'sum',
    'ga4lp_first_time_purchasers': 'sum'
}).reset_index()

# --- 4. PARSE META ADS ---
print(">>> Parsing Meta Ads (PLN)...")
df_meta = pd.read_csv(META_ADS_PATH)
# Standardize columns
df_meta = df_meta.rename(columns={
    'Amount spent (PLN)': 'meta_spend',
    'Purchases conversion value': 'meta_revenue',
    'Purchases': 'meta_purchases',
    'Link (ad settings)': 'meta_url'
})
# Extract ID
df_meta['ext_id'] = df_meta['meta_url'].apply(extract_id_from_url)
# Convert to EUR
df_meta['meta_spend'] = df_meta['meta_spend'] / PLN_TO_EUR
df_meta['meta_revenue'] = df_meta['meta_revenue'] / PLN_TO_EUR

# Aggregate by extracted ID
df_meta_agg = df_meta.dropna(subset=['ext_id']).groupby('ext_id').agg({
    'meta_spend': 'sum',
    'meta_revenue': 'sum',
    'meta_purchases': 'sum'
}).reset_index().rename(columns={'ext_id': 'feed_id'})

# NEW: Aggregate Unmapped Meta Spend by URL
df_meta['norm_url'] = df_meta['meta_url'].apply(normalize_url)
df_meta_unmapped = df_meta[df_meta['ext_id'].isna()].groupby('norm_url').agg({
    'meta_spend': 'sum',
    'meta_revenue': 'sum',
    'meta_purchases': 'sum'
}).reset_index()

# --- SPEND AUDIT & LEAKAGE CHECK ---
raw_spend_pln = df_meta['meta_spend'].sum() * PLN_TO_EUR # Convert back to PLN (since we divided by PLN_TO_EUR earlier)
# Actually, df_meta['meta_spend'] is already EUR in line 178: df_meta['meta_spend'] = ... / PLN_TO_EUR
# So let's re-calculate from source to be safe or use the DF sum.
# Let's use the DF sum which is in EUR now.
total_meta_spend_eur = df_meta['meta_spend'].sum()
mapped_spend_eur = df_meta_agg['meta_spend'].sum()

print("-" * 30)
print("DEBUG: META ADS SPEND AUDIT")
print(f"Total Spend in CSV: {total_meta_spend_eur:.2f} EUR")
print(f"Mapped to Product IDs: {mapped_spend_eur:.2f} EUR")
print(f"Leakage: {total_meta_spend_eur - mapped_spend_eur:.2f} EUR ({((total_meta_spend_eur - mapped_spend_eur)/total_meta_spend_eur)*100:.1f}%)")

# Top Unmapped
print("\nDEBUG: TOP UNMAPPED SPEND URLS:")
unmapped_meta = df_meta[df_meta['ext_id'].isna()].sort_values('meta_spend', ascending=False).head(5)
for _, row in unmapped_meta.iterrows():
    print(f"{row['meta_spend']:.2f} EUR - {row['meta_url']}")

# Ghost Matches (IDs in Meta but NOT in Feed)
meta_ids = set(df_meta_agg['feed_id'])
feed_ids = set(df_feed['feed_id'])
common_ids = meta_ids.intersection(feed_ids)
ghost_ids = meta_ids - feed_ids
print(f"\nDEBUG: GHOST MATCHES")
print(f"IDs in Meta: {len(meta_ids)}. IDs in Feed: {len(feed_ids)}")
print(f"Intersection: {len(common_ids)}")
print(f"IDs in Meta but NOT in Feed: {len(ghost_ids)}")
if len(ghost_ids) > 0:
    print(f"Sample Ghost IDs: {list(ghost_ids)[:5]}")
print("-" * 30)

# --- 5. JOIN DATASETS ---
print(">>> Match Analysis:")
df_feed['ga4_match'] = df_feed['feed_id'].isin(df_ga4_items['feed_id'])
df_lp_match = df_feed['feed_id'].isin(df_ga4_lp_agg['feed_id'])
df_meta_match = df_feed['feed_id'].isin(df_meta_agg['feed_id'])

print(f"Feed Items: {len(df_feed)}")
print(f"GA4 Items matched: {df_feed['ga4_match'].sum()}")
print(f"GA4 LP matched: {df_lp_match.sum()}")
print(f"Meta Ads matched: {df_meta_match.sum()}")

print(">>> Joining datasets...")
# Start with Feed as Master
df_master = df_feed.copy()
df_master = df_master.merge(df_ga4_items_agg, on='feed_id', how='left')
df_master = df_master.merge(df_ga4_lp_agg, on='feed_id', how='left')
df_master = df_master.merge(df_meta_agg, on='feed_id', how='left')

# --- NEW: ADD SYNTHETIC LP ROWS (Non-Product) ---
print(">>> Generating Synthetic LP Rows...")
# Filter unmapped Meta spend > 10 EUR
df_lp_rows_base = df_meta_unmapped[df_meta_unmapped['meta_spend'] > 10].copy()

# Join with GA4 data by URL
df_lp_rows_base = df_lp_rows_base.merge(df_ga4_lp_url_agg, on='norm_url', how='left')

synthetic_rows = []
for _, row in df_lp_rows_base.iterrows():
    # Generate ID from URL slug
    slug = row['norm_url'].split('/')[-1].replace('.html', '').replace('.php', '') or 'home'
    lp_id = f"LP_{slug}"
    
    # Generate title
    lp_title = f"LP: {row['norm_url']}"
    
    # Calculate AOV for Price synthetic
    meta_rev = row.get('meta_revenue', 0)
    meta_purch = row.get('meta_purchases', 0)
    aov = (meta_rev / meta_purch) if meta_purch > 0 else 50.0
    
    # URL Router for Margin & Title
    lp_margin, lp_cat_name = get_url_category_margin(row['norm_url'])
    
    # Update title for better readability
    if lp_cat_name == "Social/Canvas Ad":
        lp_title = f"LP: Social Media / Canvas"
    else:
        # Keep URL but prepend category hint if specific
        lp_title = f"LP: {row['norm_url']}"

    synthetic_rows.append({
        'feed_id': lp_id,
        'feed_title': lp_title,
        'feed_brand': 'Bushido (Non-Product)',
        'feed_category': lp_cat_name,
        'calc_gross_price': aov,
        'is_product': False,
        'is_price_inferred': True,
        'norm_url': row['norm_url'],
        'meta_spend': row['meta_spend'],
        'meta_revenue': row['meta_revenue'],
        'meta_purchases': row['meta_purchases'],
        'ga4lp_sessions': row.get('ga4lp_sessions', 0),
        'ga4lp_revenue': row.get('ga4lp_revenue', 0),
        'ga4lp_purchases': row.get('ga4lp_purchases', 0),
        'ga4lp_first_time_purchasers': row.get('ga4lp_first_time_purchasers', 0),
        'ga4item_views': 0,
        'ga4item_revenue': 0,
        'base_gross_margin': lp_margin
    })

if synthetic_rows:
    df_synthetic = pd.DataFrame(synthetic_rows)
    df_master = pd.concat([df_master, df_synthetic], ignore_index=True)
    print(f"Added {len(df_synthetic)} Synthetic LP rows.")

# Fill NaNs correctly
cols_to_zero = ['ga4item_views', 'ga4item_revenue', 'ga4lp_sessions', 'ga4lp_revenue', 'ga4lp_purchases', 'ga4lp_first_time_purchasers', 'meta_spend', 'meta_revenue', 'meta_purchases']
df_master[cols_to_zero] = df_master[cols_to_zero].fillna(0)

# --- 6. CALCULATIONS ---
print(">>> Performing economic transformations...")
# Only apply margin get_margin for products, otherwise use the synthetic margin
df_master['base_gross_margin'] = df_master.apply(
    lambda x: get_margin(x['feed_title'], [], 0.58) 
    if x['is_product'] else x.get('base_gross_margin', 0.40), 
    axis=1
)

df_master['calc_net_price'] = df_master['calc_gross_price'] / (1 + VAT_RATE)

# Robust revenue
df_master['best_ga4_revenue'] = df_master['ga4lp_revenue'].where(df_master['ga4lp_revenue'] > 0, df_master['ga4item_revenue'])

df_master['calc_contribution_profit'] = (df_master['best_ga4_revenue'] * df_master['base_gross_margin']) - df_master['meta_spend']

# Metrics
df_master['arpu'] = df_master['best_ga4_revenue'] / df_master['ga4lp_sessions'].replace(0, 1)
df_master['ga4lp_revenue'] = df_master['best_ga4_revenue']
df_master['calc_cr'] = df_master['ga4lp_purchases'] / df_master['ga4lp_sessions'].replace(0, 1)
df_master['calc_frequency'] = df_master['ga4lp_purchases'] / df_master['ga4lp_first_time_purchasers'].replace(0, 1)
df_master['calc_roas'] = df_master['meta_revenue'] / df_master['meta_spend'].replace(0, 1)

# MSC-ALGO v3: Efficiency Metrics
# GPPS = Gross Profit Per Session
df_master['calc_gpps'] = df_master['calc_contribution_profit'] / df_master['ga4lp_sessions'].replace(0, 1)
# GPPV = Gross Profit Per View (Item View) - for organic potential
df_master['calc_gppv'] = df_master['calc_contribution_profit'] / df_master['ga4item_views'].replace(0, 1)

# Bid Cap Calculation
# Formula: (AOV * Margin) * 0.30
df_master['calc_bid_cap'] = (df_master['calc_gross_price'] * df_master['base_gross_margin']) * 0.30
df_master['calc_cost_cap'] = df_master['calc_bid_cap'] * 0.80 # Default cost cap at 80% of bid cap

# Calculate Break Even ROAS for Segmentation
df_master['calc_break_even_roas'] = 1 / df_master['base_gross_margin'].replace(0, 0.01)

# --- ISOLATED CLUSTERING (Margin Silos) ---
print(">>> Performing Isolated Clustering...")

def get_clusters_for_subset(df_subset, prefix):
    # Leader / 1.5 logic
    df_sorted = df_subset.sort_values('calc_gross_price', ascending=True).copy()
    clusters = []
    
    while not df_sorted.empty:
        # Pick leader (lowest price in remaining)
        leader = df_sorted.iloc[0]
        leader_price = leader['calc_gross_price']
        upper_limit = leader_price * 1.5
        
        # Find all items in this cluster
        mask = df_sorted['calc_gross_price'] <= upper_limit
        cluster_items = df_sorted[mask]
        
        # Define Cluster Name (e.g. "BAGS TOP 150 EUR")
        # Round upper limit to nice number
        cluster_cap = int(upper_limit // 10 * 10 + 10) # e.g. 142 -> 150
        cluster_name = f"{prefix} TOP {cluster_cap} EUR"
        
        # Assign
        for idx in cluster_items.index:
            clusters.append({'feed_id': idx, 'calc_price_cluster': cluster_name})
            
        # Remove from pool
        df_sorted = df_sorted[~mask]
        
    return pd.DataFrame(clusters)

    return pd.DataFrame(clusters)

# --- SILO CLUSTERING (Gold Standard) ---
# Silo 3: LP (Landing Pages - Hybrid Margins)
df_lp_high = df_master[(df_master['base_gross_margin'] == 0.58) & (df_master['is_product'] == False)].set_index('feed_id')
df_lp_low  = df_master[(df_master['base_gross_margin'] == 0.23) & (df_master['is_product'] == False)].set_index('feed_id')
df_lp_mid  = df_master[(df_master['base_gross_margin'] == 0.40) & (df_master['is_product'] == False)].set_index('feed_id')

cluster_res = []

# Product Silos
# Note: df_gen includes products with 0.58 margin
# We need to exclude LPs from df_gen/df_bags to avoid double clustering if we want explicit LP prefixes
df_prod_bags = df_master[(df_master['base_gross_margin'] == 0.23) & (df_master['is_product'] == True)].set_index('feed_id')
df_prod_gen  = df_master[(df_master['base_gross_margin'] == 0.58) & (df_master['is_product'] == True)].set_index('feed_id')

if not df_prod_bags.empty:
    cluster_res.append(get_clusters_for_subset(df_prod_bags, "BAGS"))
if not df_prod_gen.empty:
    cluster_res.append(get_clusters_for_subset(df_prod_gen, "GEN"))

# LP Silos
if not df_lp_high.empty:
    cluster_res.append(get_clusters_for_subset(df_lp_high, "LP (HIGH)"))
if not df_lp_low.empty:
    cluster_res.append(get_clusters_for_subset(df_lp_low, "LP (LOW)"))
if not df_lp_mid.empty:
    cluster_res.append(get_clusters_for_subset(df_lp_mid, "LP (MID)"))

# Handle any other margins (e.g. if we had other overrides)
other_mask = ~df_master['base_gross_margin'].isin([0.23, 0.58, 0.40])
df_other = df_master[other_mask].set_index('feed_id')
if not df_other.empty:
    cluster_res.append(get_clusters_for_subset(df_other, "OTHER"))

if cluster_res:
    df_clusters = pd.concat(cluster_res)
    # Merge back
    df_master = df_master.merge(df_clusters, on='feed_id', how='left')
    df_master['calc_price_cluster'] = df_master['calc_price_cluster'].fillna("UNCATEGORIZED")
else:
    df_master['calc_price_cluster'] = "UNCATEGORIZED"
 
# --- 7. SEGMENTATION (MSC-ALGO v3 Full Waterfall) ---
print(">>> Calculating MSC-ALGO v3 Priorities...")

# Calculate Dynamic Thresholds (P75)
TH_REVENUE = df_master[df_master['ga4lp_revenue'] > 0]['ga4lp_revenue'].quantile(0.75)
TH_EFFICIENCY = df_master[df_master['calc_gpps'] > 0]['calc_gpps'].quantile(0.75)
if pd.isna(TH_EFFICIENCY) or TH_EFFICIENCY == 0:
    TH_EFFICIENCY = df_master[df_master['calc_gppv'] > 0]['calc_gppv'].quantile(0.75)

print(f"DEBUG: Thresholds -> Revenue (P75): {TH_REVENUE:.2f}, Efficiency (P75): {TH_EFFICIENCY:.4f}")

def segment_product_v3(row):
    # Prepare shortcuts
    roas = row['calc_roas']
    be_roas = row['calc_break_even_roas']
    spend = row['meta_spend']
    rev = row['ga4lp_revenue']
    views = row['ga4item_views']
    # Use GPPS if available (Sessions > 0), else GPPV
    eff = row['calc_gpps'] if row['ga4lp_sessions'] > 0 else row['calc_gppv']
    
    # 1. PROVEN STARS & COWS (Profitable Ads)
    if roas >= be_roas and spend > 0:
        if rev >= TH_REVENUE:
            return 1 # PROVEN_STAR
        else:
            return 2 # PROVEN_COW
            
    # 2. FIX LANDING PAGE (Unprofitable Ads)
    elif spend > 0:
        return 3 # FIX_LP (or GEM in some contexts, effectively needs fix)
        
    # 3. ORGANIC POTENTIAL (No Ad Spend)
    else:
        # High Traffic Validation
        if views >= 100:
            if eff >= TH_EFFICIENCY:
                return 6 # DIRECT_TO_PDP (High Traffic, High Efficiency)
            else:
                return 8 # IGNORE (High Traffic, Low Efficiency -> Waste)
        # Low Traffic (Testing Ground)
        else:
            if eff >= TH_EFFICIENCY:
                return 7 # FEED_DPA (Low Traffic, High Efficiency -> Scale it)
            else:
                return 5 # SCALE_UP (Low Traffic, Low Efficiency -> Test it / Slacker)

    # Fallback (Should be covered above, but for safety)
    return 4 # SLACKER

df_master['calc_priority'] = df_master.apply(segment_product_v3, axis=1)

# Map Priority Names for clarity
priority_map = {
    1: 'PROVEN_STAR',
    2: 'PROVEN_COW',
    3: 'FIX_LP',
    4: 'SLACKER',
    5: 'SCALE_UP',
    6: 'DIRECT_TO_PDP',
    7: 'FEED_DPA',
    8: 'IGNORE'
}
df_master['calc_segment_label'] = df_master['calc_priority'].map(priority_map)

# --- 8. FINAL SCHEMA ALIGNMENT (42 Columns) ---
# Map to Iiyama columns as best as possible
output_cols = [
    "feed_id","feed_title","feed_brand","feed_category","calc_gross_price","is_product","is_price_inferred",
    "feed_link","norm_url","calc_priority","calc_segment_label","calc_reason","calc_is_actionable","calc_action_type",
    "meta_class","ga4_class","base_gross_margin","calc_contribution_profit","calc_price_cluster","critical_roas",
    "scaling_roas","calc_break_even_roas","calc_gpps","calc_cr","calc_frequency","calc_gppv","arpu","arpiv",
    "meta_spend","meta_revenue","meta_purchases","calc_roas","ga4lp_sessions","ga4lp_revenue","ga4lp_purchases",
    "ga4lp_first_time_purchasers","ga4item_views","ga4item_revenue","calc_net_price","calc_bid_cap","calc_cost_cap",
    "cluster_avg_margin"
]

# Initialize missing columns with defaults
for col in output_cols:
    if col not in df_master.columns:
        df_master[col] = 0.0

df_master['calc_reason'] = "Automated Migration"
df_master['calc_is_actionable'] = df_master['calc_priority'] <= 2

# Select and order
df_final = df_master[output_cols]

# --- SAVE ---
print(f">>> Saving to {OUTPUT_DIR}/Bushido_DE_Growth_Opportunities.csv")
df_final.to_csv(os.path.join(OUTPUT_DIR, "Bushido_DE_Growth_Opportunities.csv"), index=False)

# --- FINAL QA CHECKS ---
print("-" * 30)
print("FINAL QA CHECKS")
bag_count = len(df_master[df_master['base_gross_margin'] == 0.23])
lp_count = len(df_master[df_master['is_product'] == False])
print(f"Bag Count (0.23): {bag_count} (Should be > 50)")
print(f"LP Count (is_product=False): {lp_count} (Should be > 0)")

# Cluster integrity check
# Check if "BAGS" cluster contains 0.58 items
bad_bags = df_master[(df_master['calc_price_cluster'].str.contains("BAGS")) & (df_master['base_gross_margin'] > 0.30)]
if not bad_bags.empty:
    print(f"WARNING: Found {len(bad_bags)} high-margin items in BAGS cluster!")
else:
    print("Cluster Integrity: OK")

# LP Margin Distribution
print("\nLP MARGIN DISTRIBUTION:")
print(df_master[df_master['is_product']==False]['base_gross_margin'].value_counts().sort_index().to_string())
if len(df_master[(df_master['is_product']==False) & (df_master['base_gross_margin']==0.58)]) > 0:
    print("SUCCESS: Found High-Margin (0.58) Landing Pages!")
else:
    print("WARNING: No High-Margin Landing Pages found (Check 'rekawice', 'ochraniacze', etc.)")

# Priority Distribution Check
print("\nMSC-ALGO v3 PRIORITY DISTRIBUTION:")
print(df_master['calc_priority'].value_counts().sort_index().to_string())

print("-" * 30)

print(f"\n>>> MIGRATION COMPLETE <<<")
print(f"Total Products: {len(df_final)}")
print(f"Mapped GA4 Revenue: {df_final['ga4lp_revenue'].sum():.2f} EUR")
print(f"Mapped Meta Spend: {df_final['meta_spend'].sum():.2f} EUR")
