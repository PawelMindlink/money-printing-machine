
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

def calculate_gross_margin(row, default_margin, category_overrides, min_margin=None, is_product=True):
    """
    Calculates gross margin based on product category/title.
    
    Args:
        row (dict/Series): Row containing 'product_type', 'category', 'title'
        default_margin (float): Default margin rate (e.g. 0.58)
        category_overrides (list): List of dicts {'category': 'str', 'rate': float}
        min_margin (float): Lowest possible margin for safe fallback (non-product pages)
        is_product (bool): True if entity is a product, False if category/home/other
    """
    cat_sources = [row.get('product_type'), row.get('category'), row.get('title')]
    cat_str = " ".join([str(c).lower() for c in cat_sources if pd.notna(c)])
    
    # 1. Check Specific Overrides (Category/Title match)
    for override in category_overrides:
        if override['category'].lower() in cat_str:
            return override['rate']
            
    # 2. Fallback Logic
    if is_product:
        return default_margin
    else:
        # For non-product pages (e.g. Home Page), use safest (lowest) margin if specific category not matched
        return min_margin if min_margin is not None else default_margin


def assign_price_cluster(df, price_col='price_numeric'):
    """
    Assigns price clusters to a DataFrame subset (usually passed per margin group).
    
    Logic:
    - Sort products by price DESC.
    - Start Cluster 1 with highest price Product A.
    - Add subsequent products as long as Leader Price <= 1.5 * Current Product Price.
      (Equivalent to: Current Product Price >= Leader / 1.5)
    - If condition fails, start new Cluster with current product as Leader.
    
    Args:
        df (pd.DataFrame): DataFrame with 'price_numeric' column.
        
    Returns:
        pd.Series: Series of cluster labels.
    """
    if df.empty:
        return pd.Series(dtype='object')
        
    # Sort by price desc
    # We use the index to return valid mapping
    sub_df = df.sort_values(price_col, ascending=False).copy()
    
    temp_clusters = []
    curr_id = 1
    curr_leader = None
    
    for price in sub_df[price_col]:
        if curr_leader is None:
            curr_leader = price
        
        # Condition: Leader Price must be > 1.5 * Product Price to BREAK cluster
        # So we KEEP in cluster if Leader <= 1.5 * Product
        # Which means: Product >= Leader / 1.5
        threshold = curr_leader / 1.5
        
        if price < threshold:
            curr_id += 1
            curr_leader = price
        
        temp_clusters.append(curr_id)
        
    sub_df['temp_cluster_id'] = temp_clusters
    
    # Create Labels
    id_to_label = {}
    for cid in sub_df['temp_cluster_id'].unique():
        cluster_items = sub_df[sub_df['temp_cluster_id'] == cid]
        max_p = cluster_items[price_col].max()
        min_p = cluster_items[price_col].min()
        # Label: TOP X PLN (Range: Y-X)
        if max_p == min_p:
            id_to_label[cid] = f"TOP {int(max_p)} PLN"
        else:
            id_to_label[cid] = f"TOP {int(max_p)} PLN"
        
    # Map back to original index
    return sub_df['temp_cluster_id'].map(id_to_label)


def calculate_contribution_profit(revenue, vat_rate, gross_margin, spend):
    """
    Calculates Contribution Profit (CP/CM).
    Matches MSC-ALGO v1.0 spec: (NET_REV * MARGIN_RATE) - Ad_Spend
    """
    net_revenue = revenue / (1 + vat_rate)
    gross_profit = net_revenue * gross_margin
    return gross_profit - spend


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


def calculate_critical_roas(vat_rate, gross_margin):
    """
    Calculate Critical ROAS (Break Even ROAS).
    Formula: (1 + VAT) / GrossMargin.
    
    Derivation:
    Profit = (Revenue / (1+VAT)) * Margin - Cost.
    At Break Even, Profit = 0.
    Cost = (Revenue / (1+VAT)) * Margin.
    ROAS = Revenue / Cost = Revenue / ((Revenue / (1+VAT)) * Margin) = (1+VAT) / Margin.
    """
    if gross_margin <= 0:
        return 0.0
    return (1 + vat_rate) / gross_margin


def calculate_scaling_roas(vat_rate, gross_margin):
    """
    Calculate Scaling ROAS (Target for profitable scaling).
    Formula: Critical ROAS * 1.2 (for 20% profit buffer).
    """
    critical_roas = calculate_critical_roas(vat_rate, gross_margin)
    return critical_roas * 1.2


def calculate_arpiv(item_revenue, items_viewed):
    """
    Calculate ARPIV (Average Revenue Per Item View).
    Formula: ItemRevenue / ItemsViewed
    
    Used for product-level analysis independent of landing page traffic.
    """
    if pd.isna(items_viewed) or items_viewed <= 0:
        return 0.0
    return item_revenue / items_viewed



def calculate_gross_profit(net_revenue, gross_margin):
    """
    Calculate Gross Profit.
    Formula: NetRevenue * GrossMargin
    """
    if pd.isna(net_revenue) or pd.isna(gross_margin):
        return 0.0
    return net_revenue * gross_margin


def calculate_gpps(gross_profit_lp, sessions):
    """
    Calculate GPPS (Gross Profit Per Session).
    Formula: GrossProfit(LP) / Sessions
    """
    if pd.isna(sessions) or sessions <= 0:
        return 0.0
    return gross_profit_lp / sessions



def calculate_cr(transactions, sessions):
    """
    Calculate Conversion Rate (CR).
    Formula: Transactions / Sessions
    """
    if pd.isna(sessions) or sessions <= 0:
        return 0.0
    return transactions / sessions

def calculate_gppv(gross_profit_item, item_views):
    """
    Calculate GPPV (Gross Profit Per View).
    Formula: GrossProfit(Item) / ItemViews
    """
    if pd.isna(item_views) or item_views <= 0:
        return 0.0
    return gross_profit_item / item_views


def calculate_frequency(purchases, first_time_purchasers):
    """
    Calculate Frequency (Total Purchases per First-time Purchaser).
    Formula: Total Purchases / First-time Purchasers
    """
    if pd.isna(first_time_purchasers) or first_time_purchasers <= 0:
        return 0.0
    return purchases / first_time_purchasers


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
