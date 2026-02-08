
import pandas as pd
import re
import math

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

def clean_currency(val):
    """
    Converts '1 200,00 zł' -> 1200.00
    """
    if pd.isna(val): return 0.0
    if isinstance(val, (int, float)): return float(val)
    
    s = str(val).lower()
    s = s.replace("zł", "").replace("pln", "").replace(" ", "").replace(u"\u00A0", "") # non-breaking space
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

# ============================================================================
# CORE BUSINESS LOGIC
# ============================================================================

def calculate_gross_margin(row, default_margin, category_overrides):
    """
    Calculates gross margin based on product category/title.
    
    Args:
        row (dict/Series): Row containing 'product_type', 'category', 'title'
        default_margin (float): Default margin rate (e.g. 0.58)
        category_overrides (list): List of dicts {'category': 'str', 'rate': float}
    """
    cat_sources = [row.get('product_type'), row.get('category'), row.get('title')]
    cat_str = " ".join([str(c).lower() for c in cat_sources if pd.notna(c)])
    
    for override in category_overrides:
        if override['category'].lower() in cat_str:
            return override['rate']
    return default_margin


def assign_price_cluster(df, price_col='price_numeric', spread=0.5):
    """
    Assigns price clusters to a DataFrame subset (usually passed per margin group).
    
    Args:
        df (pd.DataFrame): DataFrame with 'price_numeric' column.
        spread (float): Percentage spread for clustering (default 0.5).
        
    Returns:
        pd.Series: Series of cluster labels.
    """
    if df.empty:
        return pd.Series(dtype='object')
        
    # Sort by price desc
    # We use the index to return valid mapping
    sub_df = df.sort_values(price_col, ascending=False).copy()
    
    temp_clusters = []
    curr_id = 0
    curr_leader = None
    
    for price in sub_df[price_col]:
        if curr_leader is None:
            curr_leader = price
            curr_id = 1
        
        threshold = curr_leader * (1 - spread)
        if price < threshold:
            curr_id += 1
            curr_leader = price
        
        temp_clusters.append(curr_id)
        
    sub_df['temp_cluster_id'] = temp_clusters
    
    # Create Labels
    id_to_label = {}
    for cid in sub_df['temp_cluster_id'].unique():
        max_p = sub_df[sub_df['temp_cluster_id'] == cid][price_col].max()
        id_to_label[cid] = f"TOP {int(max_p)} PLN"
        
    # Map back to original index
    return sub_df['temp_cluster_id'].map(id_to_label)


def calculate_contribution_profit(meta_revenue, vat_rate, gross_margin, frequency, meta_spend):
    """
    Calculates Contribution Profit (CP).
    Formula: ((MetaRevenue / (1+VAT)) * Margin * Frequency) - MetaSpend
    """
    net_revenue = meta_revenue / (1 + vat_rate)
    gross_profit = net_revenue * gross_margin * frequency
    return gross_profit - meta_spend


def classify_meta_ads(contribution_profit, meta_spend):
    """
    Classifies Meta Ads performance.
    """
    if pd.isna(meta_spend) or meta_spend == 0:
        return 'No Ads'
    return 'Profitable' if contribution_profit > 0 else 'Unprofitable'


def classify_ga4_product(sessions, transactions, arpu, thresholds):
    """
    Classifies product based on GA4 metrics.
    
    Args:
        sessions (int): Number of sessions
        transactions (int): Number of purchases
        arpu (float): Average Revenue Per User
        thresholds (dict): {'min_activity': float, 'trans_75': float, 'arpu_75': float}
    """
    # Logic Change: High Performance rescues "Slacker" status
    # If sessions are low, but we have significant transactions or revenue, it's a Hidden Gem (or Star)
    # "Slacker" is ONLY for low sessions AND low performance.

    is_high_trans = transactions >= thresholds['trans_75'] and transactions > 0
    is_high_arpu = arpu >= thresholds['arpu_75'] and arpu > 0
    
    # 1. Check for High Performance First (ignores session count)
    if is_high_trans:
        return 'Star' if is_high_arpu else 'Cash Cow'
        
    if is_high_arpu:
        return 'Hidden Gem'

    # 2. Everything else is a Slacker (Low Potential)
    # Includes low session items AND items with sessions but low conversion
    return 'Slacker'


def determine_priority(ga4_class, meta_class):
    """
    Determines priority based on GA4 and Meta classification.
    """
    if ga4_class == 'Star' and meta_class == 'Profitable': return 'P1'
    if ga4_class == 'Cash Cow' and meta_class == 'Profitable': return 'P2'
    if ga4_class == 'Hidden Gem' and meta_class == 'Profitable': return 'P3'
    
    # If Organic is weak (Slacker) but Meta is Profitable -> It's a WINNER (Treat as P3/Gem)
    if ga4_class == 'Slacker' and meta_class == 'Profitable': return 'P3'
    
    if ga4_class == 'Star' and meta_class in ['No Ads', 'Unprofitable']: return 'P4'
    if ga4_class == 'Cash Cow' and meta_class in ['No Ads', 'Unprofitable']: return 'P5'
    if ga4_class == 'Hidden Gem' and meta_class == 'No Ads': return 'P6'
    
    # Slacker + Unprofitable/No Ads -> Ignore
    return 'P8'


# ============================================================================
# BIDDING & ROAS METRICS
# ============================================================================

def calculate_bid_cap(price_numeric, vat_rate, gross_margin):
    """
    Calculate Bid Cap for Meta Ads.
    Formula: Price / (1+VAT) * GrossMargin
    
    This represents the maximum CPA (Cost Per Acquisition) that maintains profitability.
    """
    if pd.isna(price_numeric) or price_numeric <= 0:
        return 0.0
    net_price = price_numeric / (1 + vat_rate)
    return net_price * gross_margin


def calculate_cost_cap(bid_cap, safety_factor=0.7):
    """
    Calculate Cost Cap for Meta Ads.
    Formula: BidCap * SafetyFactor (default 0.7 = 30% buffer)
    
    This is a conservative CPA target.
    """
    return bid_cap * safety_factor


def calculate_critical_roas(bid_cap):
    """
    Calculate Critical ROAS (Minimum viable ROAS).
    Formula: 1 / BidCap (inverted)
    
    Below this ROAS, the campaign is unprofitable.
    """
    if bid_cap <= 0:
        return 0.0
    return 1 / bid_cap


def calculate_scaling_roas(vat_rate, gross_margin, frequency):
    """
    Calculate Scaling ROAS (Target for profitable scaling).
    Formula: 1 / ((1+VAT) * GrossMargin * Frequency)
    
    At this ROAS, we are in a healthy profitability zone for scaling.
    """
    if gross_margin <= 0 or frequency <= 0:
        return 0.0
    return 1 / ((1 + vat_rate) * gross_margin * frequency)


def calculate_arpiv(item_revenue, items_viewed):
    """
    Calculate ARPIV (Average Revenue Per Item View).
    Formula: ItemRevenue / ItemsViewed
    
    Used for product-level analysis independent of landing page traffic.
    """
    if pd.isna(items_viewed) or items_viewed <= 0:
        return 0.0
    return item_revenue / items_viewed


def is_product_page(url, product_id=None):
    """
    Determines if a URL is a product page (vs category, home, etc.).
    
    Strategy:
    1. If URL contains a product ID pattern (numeric), it's likely a product page.
    2. Home page ('/') is NOT a product page.
    3. Category pages (e.g., '/kategoria/...') are NOT product pages.
    """
    if pd.isna(url) or url == '':
        return False
    
    url = str(url).lower().strip()
    path = extract_path(url)
    
    # Home page check
    if path == '/' or path == '':
        return False
    
    # If we have a product_id, it's definitely a product
    if product_id is not None and not pd.isna(product_id) and str(product_id).strip() != '':
        return True
    
    # Heuristic: Product pages often have numeric IDs in the path
    # e.g., /12345-product-name.html
    if re.search(r'/\d+-[\w-]+\.html$', path):
        return True
    if re.search(r'/p/\d+', path):
        return True
    if re.search(r'/product/\d+', path):
        return True
    
    # Category page patterns (NOT product pages)
    category_patterns = ['/kategoria/', '/category/', '/c/', '/kolekcja/', '/collection/']
    for pattern in category_patterns:
        if pattern in path:
            return False
    
    return False
