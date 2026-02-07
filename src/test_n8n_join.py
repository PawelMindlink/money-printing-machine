import sys
import pandas as pd
import os
import json
from complete_pipeline import load_ga4_csv, parse_product_feed_xml, extract_path

def test_join(brand):
    input_dir = "Input"
    brand_l = brand.lower()
    
    # 1. Load GA4 LP (Base)
    lp_path = os.path.join(input_dir, brand, f"{brand_l}_ga4_lp.csv")
    if not os.path.exists(lp_path):
        return {"error": f"GA4 LP file not found: {lp_path}"}
        
    lp_df = load_ga4_csv(lp_path)
    # Find landing page column
    lp_col = next((c for c in ['Landing page', 'Landing page + query string', 'landingPage'] if c in lp_df.columns), None)
    
    if not lp_col:
        return {"error": f"Landing page column not found in GA4 CSV. Columns: {list(lp_df.columns)}"}
        
    # Extract paths
    lp_df['path_key'] = lp_df[lp_col].apply(extract_path)
    unique_ga4_paths = set(lp_df['path_key'].unique())
    
    # 2. Load Feed (Source of Truth for Products)
    feed_path = os.path.join(input_dir, brand, f"{brand_l}_product_feed.xml")
    if not os.path.exists(feed_path):
        return {"error": f"Product Feed file not found: {feed_path}"}
        
    feed_df = parse_product_feed_xml(feed_path)
    
    # 3. Calculate Match Rate (Feed -> GA4)
    # How many products from Feed exist in GA4 LP report?
    feed_df['in_ga4'] = feed_df['path_key'].isin(unique_ga4_paths)
    
    matched_count = feed_df['in_ga4'].sum()
    total_feed = len(feed_df)
    
    unmatched = feed_df[~feed_df['in_ga4']]
    unmatched_ex = unmatched['path_key'].head(1).values[0] if not unmatched.empty else None

    result = {
        "brand": brand,
        "ga4_total_rows": len(lp_df),
        "ga4_unique_paths": len(unique_ga4_paths),
        "feed_total_products": total_feed,
        "products_matched_in_ga4": int(matched_count),
        "match_rate_percent": round((matched_count / total_feed) * 100, 2) if total_feed > 0 else 0,
        "unmatched_example": unmatched_ex
    }
    
    print(json.dumps(result))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Brand argument missing"}))
    else:
        test_join(sys.argv[1])
