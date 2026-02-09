
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

def generate_friendly_name(url, is_product=False):
    """
    Generates a friendly name for a URL (e.g. for Landing Pages).
    Algorithm:
    1. Remove protocol, domain, www.
    2. Remove file extensions (.html, .php).
    3. Replace hyphens/underscores with spaces.
    4. Capitalize words.
    5. If is_product is True, return as is (or handle differently if needed).
    """
    if pd.isna(url) or url == '':
        return 'Unknown Page'
        
    # 1. Sanitize
    url = str(url).lower().strip()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    
    # Remove domain if present (simple heuristic: look for first slash)
    if '/' in url:
        path = url[url.find('/'):]
    else:
        path = url # Fallback if no slash found (unlikely for full URL)
        
    # Remove query params
    if '?' in path:
        path = path.split('?')[0]
        
    # 2. Remove extensions
    path = re.sub(r'\.html$', '', path)
    path = re.sub(r'\.php$', '', path)
    path = re.sub(r'\.aspx$', '', path)
    
    # 3. Format
    # Remove leading slash
    path = path.lstrip('/')
    
    # Replace separators
    name = path.replace('-', ' ').replace('_', ' ').replace('/', ' > ')
    
    # 4. Capitalize
    # title() is simple but effective for this context
    return name.title()

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
    # Map back to original index
    return sub_df['temp_cluster_id'].map(id_to_label)


def calculate_cluster_stats(df, price_col='calc_gross_price', margin_rate_col='base_gross_margin', vat_rate=0.23):
    """
    Calculates stats for a cluster to determine bidding caps.
    
    Args:
        df (pd.DataFrame): Dataframe containing ONLY items for ONE cluster.
        price_col (str): Column name for gross price.
        margin_rate_col (str): Column name for margin rate (float).
        vat_rate (float): VAT rate (e.g. 0.23).
        
    Returns:
        dict: {
            'cluster_avg_margin': float,  # Average Contribution Unit Margin
            'bid_cap': float,             # Cluster Limit
            'cost_cap': float             # Efficiency Target
        }
    """
    if df.empty:
        return {'cluster_avg_margin': 0.0, 'bid_cap': 0.0, 'cost_cap': 0.0}
        
    # Calculate Unit Contribution for each member
    # Unit Contrib = (Price / (1+VAT)) * MarginRate
    
    # Ensure numeric
    prices = pd.to_numeric(df[price_col], errors='coerce').fillna(0)
    margins = pd.to_numeric(df[margin_rate_col], errors='coerce').fillna(0)
    
    net_prices = prices / (1 + vat_rate)
    unit_contributions = net_prices * margins
    
    # Cluster Average Margin (Avg Unit Contribution)
    avg_margin = unit_contributions.mean()
    
    # Bidding Strategy (From User Prompt)
    # Bid Cap: Cluster_Avg_Margin * Target_CPA_% (e.g. 30%)
    # Cost Cap: Cluster_Avg_Margin * Break_Even_Ratio (e.g. 100%) - usually the "Don't exceed this" limit
    
    # NOTE: User naming seems swapped from standard Meta usage, but we follow the FORMULA.
    # Standard: Bid Cap is HARD LIMIT (Prevent loss), Cost Cap is SOFT TARGET (Efficiency).
    # Prompt: "Bid Cap = Margin * 30%" -> This is very low, looks like a Target CPA.
    # Prompt: "Cost Cap = Margin * BreakEven" -> This is the limit.
    
    target_cpa_ratio = 0.3    # 30% of Margin
    break_even_ratio = 1.0    # 100% of Margin
    
    bid_cap = avg_margin * target_cpa_ratio     # The "Efficiency" Target
    cost_cap = avg_margin * break_even_ratio    # The "Breakeven" Limit
    
    return {
        'cluster_avg_margin': avg_margin,
        'bid_cap': bid_cap,
        'cost_cap': cost_cap
    }


def calculate_conservative_price(feed_price, meta_aov, ga4_aov, is_product=False):
    """
    Calculates the 'Conservative Price' for estimation.
    Logic:
    - If Product: Return Feed Price.
    - If Non-Product: Return MIN of available (non-zero) signals:
        - Feed Price (Manual)
        - Meta AOV
        - GA4 AOV
    - If all are 0/Null -> Return 0.0 (Review Required)
    """
    if is_product:
        return float(feed_price) if pd.notna(feed_price) else 0.0
        
    candidates = []
    
    # helper to check validity
    def is_valid(val):
        return pd.notna(val) and val > 0
        
    # Feed Price
    if is_valid(feed_price):
        candidates.append(float(feed_price))
        
    # Meta AOV
    if is_valid(meta_aov):
        candidates.append(float(meta_aov))
        
    # GA4 AOV
    if is_valid(ga4_aov):
        candidates.append(float(ga4_aov))
        
    if not candidates:
        return 0.0
        
    return min(candidates)


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


# ============================================================================
# SMART MATCHER (ANTI-FRAGILE DATA MATCHING)
# ============================================================================

class SmartMatcher:
    """
    Implements a Matching Cascade for robust data linking.
    
    The Cascade:
    1. Silver Bullet: Match by Content ID / Product ID (exact).
    2. ID Extractor: Extract numeric ID (4+ digits) from URL and match.
    3. Semantic Tokenizer: Fuzzy match via Jaccard similarity on URL tokens.
    """
    
    def __init__(self, feed_df, id_col='feed_id', url_col='norm_url'):
        """
        Initialize the SmartMatcher with the Feed DataFrame.
        
        Args:
            feed_df (pd.DataFrame): The product feed DataFrame.
            id_col (str): Column name for product ID.
            url_col (str): Column name for normalized URL.
        """
        self.feed_df = feed_df.copy()
        self.id_col = id_col
        self.url_col = url_col
        
        # Pre-compute: Extract IDs from all feed URLs
        self.feed_df['_extracted_id'] = self.feed_df[url_col].apply(self.extract_id_from_url)
        
        # Pre-compute: Tokenize all feed URLs
        self.feed_df['_url_tokens'] = self.feed_df[url_col].apply(self.tokenize_url)
        
        # Build lookup dictionaries for fast matching
        self._build_lookups()
        
    def _build_lookups(self):
        """Build fast lookup dictionaries."""
        # ID -> Index
        self.id_to_idx = {}
        for idx, row in self.feed_df.iterrows():
            feed_id = str(row[self.id_col]).strip()
            if feed_id and feed_id != 'nan':
                self.id_to_idx[feed_id] = idx
                
        # Extracted ID -> Index (only if valid)
        self.extracted_id_to_idx = {}
        for idx, row in self.feed_df.iterrows():
            ext_id = row['_extracted_id']
            if ext_id:
                # Store first occurrence (priority to feed order)
                if ext_id not in self.extracted_id_to_idx:
                    self.extracted_id_to_idx[ext_id] = idx
                    
    @staticmethod
    def extract_id_from_url(url):
        """
        Extract the first sequence of 4+ digits from a URL path.
        
        Examples:
            '/35946-produkt.html' -> '35946'
            '/p/12345' -> '12345'
            '/kubek-super-tata' -> None
        """
        if pd.isna(url) or url == '':
            return None
        url = str(url)
        # Look for 4+ digit sequences
        match = re.search(r'/(\d{4,})(?:[/-]|\.html|$)', url)
        if match:
            return match.group(1)
        # Also try at the start of the path
        match = re.search(r'^/?(\d{4,})(?:[/-]|\.html|$)', url.split('/')[-1] if '/' in url else url)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def tokenize_url(url):
        """
        Tokenize a URL into a set of meaningful words.
        Removes protocol, domain, extensions, and splits on separators.
        """
        if pd.isna(url) or url == '':
            return set()
        url = str(url).lower()
        # Remove protocol and domain
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^[^/]+/', '/', url)  # Remove domain
        # Remove extensions
        url = re.sub(r'\.(html|php|aspx)$', '', url)
        # Remove query params
        if '?' in url:
            url = url.split('?')[0]
        # Split on separators
        tokens = re.split(r'[-_/]', url)
        # Filter: keep tokens > 2 chars and not purely numeric
        tokens = {t.strip() for t in tokens if len(t) > 2 and not t.isdigit()}
        return tokens
    
    @staticmethod
    def jaccard_similarity(set_a, set_b):
        """Calculate Jaccard similarity between two sets."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def subset_inclusion(short_set, long_set):
        """
        Calculate what percentage of short_set tokens are in long_set.
        Rule: If >80% of short tokens exist in long, it's a match.
        """
        if not short_set:
            return 0.0
        if not long_set:
            return 0.0
        matches = len(short_set & long_set)
        return matches / len(short_set)
    
    def find_best_match(self, row, content_id_col=None, url_col='norm_url'):
        """
        Find the best matching Feed row for a given Meta/GA4 row.
        
        Returns:
            (match_idx, match_method) or (None, None) if no match.
        """
        # --- Step 1: Silver Bullet (Content ID) ---
        if content_id_col and content_id_col in row.index:
            content_id = str(row[content_id_col]).strip()
            if content_id and content_id != 'nan' and content_id in self.id_to_idx:
                return self.id_to_idx[content_id], 'CONTENT_ID'
        
        # --- Step 2: ID Extractor (Numeric Regex) ---
        url = row.get(url_col, '')
        extracted_id = self.extract_id_from_url(url)
        if extracted_id:
            # Direct match
            if extracted_id in self.id_to_idx:
                return self.id_to_idx[extracted_id], 'EXTRACTED_ID_DIRECT'
            # Match against extracted IDs from feed
            if extracted_id in self.extracted_id_to_idx:
                return self.extracted_id_to_idx[extracted_id], 'EXTRACTED_ID_URL'
        
        # --- Step 3: Semantic Tokenizer (Fuzzy Match) ---
        url_tokens = self.tokenize_url(url)
        if url_tokens:
            best_match_idx = None
            best_score = 0.0
            
            for idx, feed_tokens in self.feed_df['_url_tokens'].items():
                if not feed_tokens:
                    continue
                    
                # Use subset inclusion (shorter into longer)
                if len(url_tokens) <= len(feed_tokens):
                    score = self.subset_inclusion(url_tokens, feed_tokens)
                else:
                    score = self.subset_inclusion(feed_tokens, url_tokens)
                
                if score > best_score and score >= 0.8:
                    best_score = score
                    best_match_idx = idx
                    
            if best_match_idx is not None:
                return best_match_idx, f'FUZZY_{best_score:.2f}'
        
        # No match found
        return None, None
    
    def enrich_dataframe(self, source_df, content_id_col=None, url_col='norm_url'):
        """
        Enrich a source DataFrame with Feed data using the Matching Cascade.
        
        Args:
            source_df (pd.DataFrame): DataFrame to enrich (e.g., Meta Ads).
            content_id_col (str): Column name for Content/Product ID (optional).
            url_col (str): Column name for URL.
            
        Returns:
            pd.DataFrame: Enriched DataFrame with Feed columns added.
        """
        match_results = []
        
        for idx, row in source_df.iterrows():
            match_idx, method = self.find_best_match(row, content_id_col, url_col)
            match_results.append({'_source_idx': idx, '_feed_match_idx': match_idx, '_match_method': method})
        
        # Create match DataFrame
        match_df = pd.DataFrame(match_results).set_index('_source_idx')
        
        # Join results
        result = source_df.copy()
        result['_feed_match_idx'] = match_df['_feed_match_idx']
        result['_match_method'] = match_df['_match_method']
        
        # Get Feed data for matched rows
        for col in self.feed_df.columns:
            if col.startswith('_'):  # Skip internal columns
                continue
            result[f'feed_{col}'] = result['_feed_match_idx'].apply(
                lambda x: self.feed_df.loc[x, col] if pd.notna(x) and x in self.feed_df.index else None
            )
        
        return result


def sanitize_ghost_prices(df, price_col='calc_gross_price', category_col='feed_category', 
                          is_product_col='is_product', threshold_multiplier=2.5):
    """
    Detect and sanitize "Ghost Products" with anomalous prices.
    
    A Ghost Product is one with is_product=True but no Feed match (or invalid price).
    If its price is > 2.5x the Category Average, we clamp it.
    
    Args:
        df (pd.DataFrame): The main DataFrame.
        price_col (str): Column with calculated price.
        category_col (str): Column with category for grouping.
        is_product_col (str): Column indicating if row is a product.
        threshold_multiplier (float): Multiplier for anomaly detection (default 2.5).
        
    Returns:
        pd.DataFrame: DataFrame with anomalies flagged and prices clamped.
    """
    df = df.copy()
    
    # Initialize flags
    df['_is_price_anomaly'] = False
    df['_original_price'] = df[price_col]
    
    # Calculate Category Average Price (from valid Feed matches only)
    valid_prices = df[(df[is_product_col]) & (df[price_col] > 0)]
    
    if valid_prices.empty:
        print("[SANITIZE] Warning: No valid prices to calculate averages.")
        return df
    
    # Group by category
    cat_avg = valid_prices.groupby(category_col)[price_col].mean().to_dict()
    global_avg = valid_prices[price_col].mean()
    
    # Identify Ghost Products (products without proper feed data or extreme prices)
    # Heuristic: If feed_id is missing but is_product=True, it's a ghost
    mask_ghost = (df[is_product_col]) & (df['feed_id'].isna() | (df['feed_id'] == ''))
    
    anomaly_count = 0
    
    for idx in df[mask_ghost].index:
        row_price = df.loc[idx, price_col]
        row_cat = df.loc[idx, category_col]
        
        # Get reference price (category avg or global avg)
        ref_price = cat_avg.get(row_cat, global_avg)
        
        if row_price > 0 and ref_price > 0:
            if row_price > ref_price * threshold_multiplier:
                # Anomaly detected
                df.loc[idx, '_is_price_anomaly'] = True
                df.loc[idx, price_col] = ref_price  # Clamp to average
                df.loc[idx, 'calc_is_actionable'] = False  # Flag as non-actionable
                
                anomaly_count += 1
                print(f"[SANITIZE] Price anomaly: '{df.loc[idx, 'feed_title'][:50]}...' clamped from {row_price:.2f} PLN to {ref_price:.2f} PLN")
    
    print(f"[SANITIZE] Total anomalies detected and clamped: {anomaly_count}")
    
    return df
