import pandas as pd
import os
import xml.etree.ElementTree as ET
from io import StringIO
import requests
import business_logic_layer as bl

def parse_product_feed_xml_from_url(url: str) -> pd.DataFrame:
    """Download and parse Product Feed from a URL."""
    try:
        print(f"[DATA LOADER] Downloading feed from {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse from string
        tree = ET.ElementTree(ET.fromstring(response.content))
        return _parse_feed_tree(tree)
    except Exception as e:
        print(f"[DATA LOADER] Error downloading/parsing feed: {e}")
        return pd.DataFrame()

def _parse_feed_tree(tree: ET.ElementTree) -> pd.DataFrame:
    """Internal helper to parse feed elements to DataFrame."""

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
    """Parse Product Feed and use strict 'feed_' prefixes."""
    if not os.path.exists(filepath):
        print(f"Feed not found: {filepath}")
        return pd.DataFrame()
        
    tree = ET.parse(filepath)
    return _parse_feed_tree(tree)

def _parse_feed_tree(tree: ET.ElementTree) -> pd.DataFrame:
    """Internal helper to parse feed elements to DataFrame."""
    root = tree.getroot()
    ns = {'g': 'http://base.google.com/ns/1.0'}
    
    products = []
    for item in root.findall('.//item'):
        # Category Cleaning
        cat_raw = item.findtext('g:google_product_category', namespaces=ns)
        # Handle known obscur codes if needed, or keep raw
        cat_clean = 'Monitors' if cat_raw == '305' else cat_raw

        link = item.findtext('g:link', namespaces=ns) or item.findtext('link')
        
        p = {
            'feed_id': item.findtext('g:id', namespaces=ns),
            'feed_title': item.findtext('g:title', namespaces=ns) or item.findtext('title'),
            'feed_link': link,
            'feed_category': cat_clean,
            'feed_product_type': item.findtext('g:product_type', namespaces=ns),
            'feed_price_str': item.findtext('g:price', namespaces=ns),
            'feed_brand': item.findtext('g:brand', namespaces=ns),
            'feed_image_link': item.findtext('g:image_link', namespaces=ns),
        }
        # Technical joins
        p['norm_url'] = bl.normalize_url(p['feed_link'])
        p['path_key'] = bl.extract_path(p['feed_link'])
        products.append(p)
        
    return pd.DataFrame(products)
