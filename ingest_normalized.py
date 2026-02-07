
import pandas as pd
import xml.etree.ElementTree as ET
import urllib.parse
import os
import shutil

# --- CONFIG ---
BASE_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine"
INPUT_DIR = os.path.join(BASE_DIR, "Input")
OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
BRANDS = ["Bushido", "Iiyama", "Koszulkowy"]

# --- UTILS ---
def normalize_url(url):
    """
    Standardizes URL to: domain.com/path
    Removes: protocol, www, query params, trailing slash
    """
    if not isinstance(url, str): return ""
    try:
        # Strip whitespace
        url = url.strip()
        # Parse
        parsed = urllib.parse.urlparse(url)
        
        # If no scheme, might be "domain.com/..."
        if not parsed.netloc:
             # Try adding https to see if it parses better, or just treat path as url
             if "/" in url:
                 parts = url.split("/")
                 # Heuristic: if first part has dot, it's domain
                 if "." in parts[0]: 
                     path = "/".join(parts[1:])
                     netloc = parts[0]
                 else:
                     return url # Fail safe
             else:
                 return url

        netloc = parsed.netloc.replace("www.", "")
        path = parsed.path.rstrip("/")
        
        return f"{netloc}{path}"
    except:
        return ""

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

# --- LOADERS ---
def load_feed(path):
    print(f"  > Loading Feed: {os.path.basename(path)}")
    try:
        context = ET.iterparse(path, events=('end',))
        items = []
        for event, elem in context:
            if elem.tag.endswith('item'):
                data = {'id': 'N/A', 'title': 'N/A', 'link': 'N/A', 'cat': 'N/A', 'price': 0.0}
                for child in elem:
                    tag = child.tag
                    # Strict tag matching to avoid partial matches like 'image_link'
                    if tag.endswith('}id') or tag == 'id': 
                        data['id'] = str(child.text).strip()
                    elif tag.endswith('}title') or tag == 'title': 
                        data['title'] = child.text
                    elif (tag.endswith('}link') or tag == 'link') and not tag.endswith('image_link'): 
                        # This ensures we get the main product link, not the image link
                        data['link'] = child.text
                    elif tag.endswith('product_type'): 
                        data['cat'] = child.text
                    elif tag.endswith('price'): 
                        data['price'] = clean_currency(child.text)
                
                data['norm_url'] = normalize_url(data['link'])
                items.append(data)
                elem.clear()
        
        return pd.DataFrame(items)
    except Exception as e:
        print(f"    Error: {e}")
        return pd.DataFrame()

def load_ga4_items(path):
    print(f"  > Loading GA4 Items: {os.path.basename(path)}")
    try:
        # Sniff header
        h_row = 0
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if "Item ID" in line: h_row = i; break
        
        df = pd.read_csv(path, skiprows=h_row)
        # Normalize columns
        df.columns = [c.strip() for c in df.columns]
        
        # Standardize ID
        if 'Item ID' in df.columns:
            df['Item ID'] = df['Item ID'].astype(str).str.strip()
        
        # Standardize Metrics
        if 'Item revenue' in df.columns:
            df['Item revenue'] = df['Item revenue'].astype(str).apply(clean_currency)
        
        return df
    except Exception as e:
        print(f"    Error: {e}")
        return pd.DataFrame()

def load_meta_ads(path):
    print(f"  > Loading Meta Ads: {os.path.basename(path)}")
    try:
        df = pd.read_csv(path)
        
        # Identify URL Check
        # Prioritize "Link (ad settings)" as it is the standard export column
        url_col = None
        if "Link (ad settings)" in df.columns:
            url_col = "Link (ad settings)"
        else:
             url_col = next((c for c in df.columns if "Link" in c or "Landing" in c or "URL" in c), None)
        
        if url_col:
            print(f"    URL Column detected: {url_col}")
            df['norm_url'] = df[url_col].apply(normalize_url)
            
            # Clean Metrics
            if 'Amount spent (PLN)' in df.columns:
                 df['Amount spent (PLN)'] = df['Amount spent (PLN)'].apply(clean_currency)
            
            # Aggregate by URL (One row per LP)
            agg_rules = {
                'Amount spent (PLN)': 'sum',
                'Purchases': 'sum',
                'Purchases conversion value': 'sum'
            }
            # Only aggregate existing cols
            agg_rules = {k: v for k, v in agg_rules.items() if k in df.columns}
            
            if agg_rules:
                df_agg = df.groupby('norm_url').agg(agg_rules).reset_index()
                return df_agg
            else:
                return df
        else:
            print("    WARNING: No URL column found. Skipping aggregation.")
            return df

    except Exception as e:
        print(f"    Error: {e}")
        return pd.DataFrame()

# --- MAIN ---
def ingest():
    for brand in BRANDS:
        print(f"\nPROCESSING BRAND: {brand}")
        
        # Paths
        in_path = os.path.join(INPUT_DIR, brand)
        out_path = os.path.join(OUTPUT_DIR, brand, "Normalized")
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        
        # 1. FEED
        feed_df = load_feed(os.path.join(in_path, "product_feed.xml"))
        if not feed_df.empty:
            feed_df.to_csv(os.path.join(out_path, "feed_clean.csv"), index=False)
            print("    Saved feed_clean.csv")

        # 2. GA4 ITEMS
        ga4_df = load_ga4_items(os.path.join(in_path, "ga4_items.csv"))
        if not ga4_df.empty:
            ga4_df.to_csv(os.path.join(out_path, "ga4_items_clean.csv"), index=False)
            print("    Saved ga4_items_clean.csv")

        # 3. META ADS
        meta_df = load_meta_ads(os.path.join(in_path, "meta_ads.csv"))
        if not meta_df.empty:
            meta_df.to_csv(os.path.join(out_path, "meta_ads_clean.csv"), index=False)
            print("    Saved meta_ads_clean.csv")

if __name__ == "__main__":
    ingest()
