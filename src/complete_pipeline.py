#!/usr/bin/env python3
"""
Complete 5-Step Data Pipeline

Based on Zuzia conversation transcript, the true flow is:

Step 1: Load GA4 Landing Page (base layer - URL level data)
Step 2: Join Product Feed by normalized URL → adds item_id, item_name, category, price
Step 3: Enrich with GA4 Item Breakdown using item_id from feed → adds item-level metrics
Step 4: Join aggregated Meta Ads data by normalized URL → adds spend, revenue per URL
Step 5: Calculate metrics (CP, Frequency) and assign Priority P1-P8

This script runs the complete pipeline for one brand.
"""

import pandas as pd
import sys
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_url(url):
    """
    Normalize URL by:
    - Removing protocol (http/https)
    - Removing www.
    - Removing trailing slash
    - Removing UTM parameters
    - Converting to lowercase
    """
    if pd.isna(url) or url == '':
        return ''
    
    url = str(url).lower().strip()
    
    # Remove protocol
    url = re.sub(r'^https?://', '', url)
    
    # Remove www.
    url = re.sub(r'^www\.', '', url)
    
    # Parse and remove query parameters (UTMs)
    if '?' in url:
        url = url.split('?')[0]
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    return url

def extract_path(url):
    """
    Extract just the path portion from URL (without domain).
    Used for matching GA4 relative URLs with Feed absolute URLs.
    
    Examples:
    - 'bushido-sport.pl/product-pol-5-worek.html' -> '/product-pol-5-worek.html'
    - '/product-pol-5-worek.html' -> '/product-pol-5-worek.html'
    - 'https://example.com/path/to/page' -> '/path/to/page'
    """
    if pd.isna(url) or url == '':
        return ''
    
    url = str(url).lower().strip()
    
    # Remove protocol
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    
    # Remove query parameters
    if '?' in url:
        url = url.split('?')[0]
    
    # Extract path (everything after first /)
    if '/' in url:
        # Check if starts with domain (no leading /)
        if not url.startswith('/'):
            # Has domain, extract path after first /
            first_slash = url.find('/')
            path = url[first_slash:]
        else:
            # Already starts with /, keep as is
            path = url
    else:
        # No slash at all, return as /url
        path = '/' + url
    
    # Remove trailing slash
    path = path.rstrip('/')
    
    # Ensure starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    # Normalize HTML extensions (Feed uses .facebookads.html, LP uses .html)
    path = path.replace('.facebookads.html', '.html')
    path = path.replace('.facebook.html', '.html')
    
    return path

def skip_header_comments(filepath):
    """Skip # comment lines at start of GA4 CSV exports"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start_idx = 0
    for i, line in enumerate(lines):
        if not line.startswith('#'):
            start_idx = i
            break
    
    return ''.join(lines[start_idx:])

def load_ga4_csv(filepath):
    """Load GA4 CSV, skipping header comments and Grand Total row"""
    from io import StringIO
    csv_content = skip_header_comments(filepath)
    
    # Remove Grand Total row BEFORE parsing by Pandas
    # This row has empty first column which shifts all data
    lines = csv_content.strip().split('\n')
    filtered_lines = []
    
    for i, line in enumerate(lines):
        # Keep header
        if i == 0:
            filtered_lines.append(line)
            continue
        
        # Skip if any cell contains "Grand total" (case insensitive)
        if 'grand total' not in line.lower():
            filtered_lines.append(line)
    
    # Parse with Pandas
    df = pd.read_csv(StringIO('\n'.join(filtered_lines)))
    
    # Additional cleanup - remove rows with empty first column value
    first_col = df.columns[0]
    df = df[df[first_col].notna()].copy()
    df = df[df[first_col].astype(str).str.strip() != ''].copy()
    
    return df

def parse_product_feed_xml(filepath):
    """Parse Facebook Product Feed XML"""
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    # Facebook feed uses RSS format with <item> entries
    products = []
    
    for item in root.findall('.//item'):
        product = {}
        
        # Extract fields (namespaced with g: for Google Shopping)
        ns = {'g': 'http://base.google.com/ns/1.0'}
        
        product['id'] = item.findtext('g:id', default='', namespaces=ns)
        product['title'] = item.findtext('g:title', default='', namespaces=ns) or item.findtext('title', default='')
        product['link'] = item.findtext('g:link', default='', namespaces=ns) or item.findtext('link', default='')
        product['description'] = item.findtext('g:description', default='', namespaces=ns)
        product['price'] = item.findtext('g:price', default='', namespaces=ns)
        product['image_link'] = item.findtext('g:image_link', default='', namespaces=ns)
        product['category'] = item.findtext('g:google_product_category', default='', namespaces=ns)
        
        # Normalize URL
        product['norm_url'] = normalize_url(product['link'])
        
        products.append(product)
    
    return pd.DataFrame(products)

# ============================================================================
# PIPELINE STEPS
# ============================================================================

def step1_load_landing_pages(brand, input_dir):
    """Step 1: Load GA4 Landing Page report (base layer)"""
    print(f"\n=== Step 1: Load Landing Page Report ===")
    
    lp_path = os.path.join(input_dir, brand, 'ga4_lp.csv')
    lp_df = load_ga4_csv(lp_path)
    
    print(f"Loaded {len(lp_df)} landing pages")
    print(f"Columns: {list(lp_df.columns)}")
    
    # Find landing page column (different GA4 exports have different names)
    lp_col_candidates = ['Landing page', 'Landing page + query string', 'landingPage']
    lp_col = None
    for col in lp_col_candidates:
        if col in lp_df.columns:
            lp_col = col
            break
    
    if lp_col is None:
        raise ValueError(f"No landing page column found. Available columns: {list(lp_df.columns)}")
    
    print(f"Using column: '{lp_col}'")
    
    # Extract path from landing page URLs (for matching with Feed)
    # GA4 uses relative URLs like '/product-pol-347-...'
    lp_df['path_key'] = lp_df[lp_col].apply(extract_path)
    
    # Also keep normalized URL for Meta Ads matching (which uses full URLs)
    lp_df['norm_url'] = lp_df[lp_col].apply(normalize_url)
    
    # Filter out non-ad pages (login, checkout, etc.)
    excluded_patterns = ['/login', '/checkout', '/payment', '/confirmation', 
                        '/search', '/cart', '/account', '/register',
                        '/orderdetails', '/basketedit', '/place-order']
    
    def is_ad_target(url):
        url_lower = str(url).lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
    
    lp_df['is_ad_target'] = lp_df['path_key'].apply(is_ad_target)
    lp_df = lp_df[lp_df['is_ad_target']].copy()
    
    print(f"After filtering non-ad pages: {len(lp_df)} pages")
    
    return lp_df

def step2_join_product_feed(lp_df, brand, input_dir):
    """Step 2: Join Product Feed by path (handles relative vs absolute URLs)"""
    print(f"\n=== Step 2: Join Product Feed ===")
    
    feed_path = os.path.join(input_dir, brand, 'product_feed.xml')
    feed_df = parse_product_feed_xml(feed_path)
    
    print(f"Loaded {len(feed_df)} products from feed")
    
    # Extract path from Feed URLs (Feed uses absolute URLs like 'bushido-sport.pl/...')
    feed_df['path_key'] = feed_df['link'].apply(extract_path)
    
    # Debug: show sample paths
    print(f"Sample LP paths: {lp_df['path_key'].head(3).tolist()}")
    print(f"Sample Feed paths: {feed_df['path_key'].head(3).tolist()}")
    
    # Join on path_key (extracted path without domain)
    merged = pd.merge(lp_df, feed_df[['path_key', 'id', 'title', 'price', 'category', 'image_link']], 
                      on='path_key', how='left', suffixes=('', '_feed'))
    
    # Mark which pages are product pages (have feed match)
    merged['is_product_page'] = ~merged['id'].isna()
    
    print(f"Product pages: {merged['is_product_page'].sum()} / {len(merged)}")
    
    return merged

def step3_enrich_with_items(merged_df, brand, input_dir):
    """Step 3: Enrich with GA4 Item Breakdown using item_id"""
    print(f"\n=== Step 3: Enrich with Item Breakdown ===")
    
    items_path = os.path.join(input_dir, brand, 'ga4_items.csv')
    items_df = load_ga4_csv(items_path)
    
    print(f"Loaded {len(items_df)} items")
    
    # Join on Item ID (from product feed)
    # Note: Item ID in feed might be string, in GA4 might be different format
    items_df['Item ID'] = items_df['Item ID'].astype(str)
    merged_df['id'] = merged_df['id'].astype(str)
    
    enriched = pd.merge(merged_df, items_df[['Item ID', 'Items viewed', 'Items purchased', 'Item revenue']],
                       left_on='id', right_on='Item ID', how='left')
    
    print(f"Enriched with item-level metrics")
    
    return enriched

def step4_join_meta_ads(enriched_df, brand, input_dir):
    """Step 4: Join aggregated Meta Ads data"""
    print(f"\n=== Step 4: Join Meta Ads (Aggregated) ===")
    
    meta_path = os.path.join(input_dir, brand, 'meta_ads.csv')
    meta_df = pd.read_csv(meta_path)
    
    # Normalize URLs in Meta Ads
    meta_df['norm_url'] = meta_df['Link (ad settings)'].apply(normalize_url)
    
    # Aggregate by landing page
    meta_agg = meta_df.groupby('norm_url').agg({
        'Amount spent (PLN)': 'sum',
        'Purchases': 'sum',
        'Purchases conversion value': 'sum'
    }).reset_index()
    
    meta_agg.columns = ['norm_url', 'meta_spend', 'meta_purchases', 'meta_revenue']
    
    print(f"Aggregated Meta Ads to {len(meta_agg)} landing pages")
    
    # Join with main data
    final = pd.merge(enriched_df, meta_agg, on='norm_url', how='left')
    
    # Mark Meta Ads status
    final['has_meta_ads'] = ~final['meta_spend'].isna()
    
    print(f"Pages with Meta Ads: {final['has_meta_ads'].sum()} / {len(final)}")
    
    return final

def step5_calculate_metrics(final_df, brand_config):
    """Step 5: Calculate metrics and assign priorities"""
    print(f"\n=== Step 5: Calculate Metrics & Priority ===")
    
    # Get brand-specific config
    vat_rate = brand_config.get('vat_rate', 0.23)
    default_margin = brand_config.get('default_margin', 0.30)
    
    # Calculate Frequency
    final_df['frequency'] = final_df['Purchases'] / final_df['First time purchasers'].replace(0, 1)
    
    # Get margin (from category or default)
    def get_margin(row):
        # TODO: Implement category-specific margins from business_logic.json
        return default_margin
    
    final_df['gross_margin'] = final_df.apply(lambda x: default_margin, axis=1)
    
    # Calculate Contribution Profit
    # CP = (Meta_Revenue / (1 + VAT) * Margin * Frequency) - Ad_Spend
    final_df['net_revenue'] = final_df['meta_revenue'] / (1 + vat_rate)
    final_df['contribution_profit'] = (
        final_df['net_revenue'] * final_df['gross_margin'] * final_df['frequency']
    ) - final_df['meta_spend']
    
    # Meta Ads Classification
    def meta_classification(row):
        if pd.isna(row['meta_spend']) or row['meta_spend'] == 0:
            return 'No Ads'
        elif row['contribution_profit'] > 0:
            return 'Profitable'
        else:
            return 'Unprofitable'
    
    final_df['meta_class'] = final_df.apply(meta_classification, axis=1)
    
    # GA4 Classification (simplified for now - needs full BCG logic)
    # TODO: Implement proper Star/Cash Cow/Hidden Gem/Slacker classification
    final_df['ga4_class'] = 'Star'  # Placeholder
    
    # Priority assignment (based on Priority Matrix)
    def assign_priority(row):
        ga4 = row['ga4_class']
        meta = row['meta_class']
        
        if ga4 == 'Star' and meta == 'Profitable':
            return 'P1'
        elif ga4 == 'Cash Cow' and meta == 'Profitable':
            return 'P2'
        elif ga4 == 'Hidden Gem' and meta == 'Profitable':
            return 'P3'
        elif ga4 == 'Star' and meta in ['No Ads', 'Unprofitable']:
            return 'P4'
        elif ga4 == 'Cash Cow' and meta in ['No Ads', 'Unprofitable']:
            return 'P5'
        elif ga4 == 'Hidden Gem' and meta == 'No Ads':
            return 'P6'
        elif ga4 in ['Ignore', 'Slacker'] and meta == 'Profitable':
            return 'P7'
        else:
            return 'P8'
    
    final_df['priority'] = final_df.apply(assign_priority, axis=1)
    
    print(f"\nPriority Distribution:")
    print(final_df['priority'].value_counts().sort_index())
    
    return final_df

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def run_complete_pipeline(brand, input_dir, output_dir, brand_config):
    """Run complete 5-step pipeline"""
    print(f"\n{'='*60}")
    print(f"COMPLETE PIPELINE FOR {brand}")
    print(f"{'='*60}")
    
    # Step 1: Load Landing Pages
    lp_df = step1_load_landing_pages(brand, input_dir)
    
    # Step 2: Join Product Feed
    merged_df = step2_join_product_feed(lp_df, brand, input_dir)
    
    # Step 3: Enrich with Items
    enriched_df = step3_enrich_with_items(merged_df, brand, input_dir)
    
    # Step 4: Join Meta Ads
    final_df = step4_join_meta_ads(enriched_df, brand, input_dir)
    
    # Step 5: Calculate Metrics
    final_df = step5_calculate_metrics(final_df, brand_config)
    
    # Save outputs
    output_path = os.path.join(output_dir, brand, 'Landing_Page_Final.csv')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Main output (P1-P7)
    main_output = final_df[final_df['priority'] != 'P8'].copy()
    main_output.to_csv(output_path, index=False)
    
    # P8 products (skipped)
    p8_output_path = os.path.join(output_dir, brand, 'Produkty_Pominięte.csv')
    p8_output = final_df[final_df['priority'] == 'P8'].copy()
    p8_output.to_csv(p8_output_path, index=False)
    
    print(f"\n[OK] PIPELINE COMPLETE")
    print(f"   Main output: {output_path} ({len(main_output)} products)")
    print(f"   Skipped (P8): {p8_output_path} ({len(p8_output)} products)")
    
    return final_df

if __name__ == "__main__":
    BASE_DIR = r"c:\Users\Paweł\Documents\GitHub\Money Printing Machine"
    INPUT_DIR = os.path.join(BASE_DIR, "Input")
    OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
    
    brand = sys.argv[1] if len(sys.argv) > 1 else "Bushido"
    
    # Load brand config
    import json
    config_path = os.path.join(BASE_DIR, "business_logic.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        brand_configs = {c['name']: c for c in config_data['clients']}
    
    brand_config = brand_configs.get(brand, {
        'vat_rate': 0.23,
        'default_margin': 0.30
    })
    
    result = run_complete_pipeline(brand, INPUT_DIR, OUTPUT_DIR, brand_config)
