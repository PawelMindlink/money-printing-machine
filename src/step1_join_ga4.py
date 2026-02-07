#!/usr/bin/env python3
"""
Step 1: Join GA4 Landing Page + Item Breakdown

Input:
    - Input/{Brand}/ga4_lp.csv (Landing Page report)
    - Input/{Brand}/ga4_items.csv (Item Breakdown report)

Output:
    - Output/{Brand}/GA4_Merged.csv

Logic:
    Left join Landing Page with Item Breakdown on common fields
    (landing page can match multiple items, we keep all)
"""

import pandas as pd
import sys
import os
from pathlib import Path

def skip_header_comments(filepath):
    """Skip # comment lines at start of GA4 CSV exports"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find first non-comment line
    start_idx = 0
    for i, line in enumerate(lines):
        if not line.startswith('#'):
            start_idx = i
            break
    
    return ''.join(lines[start_idx:])

def load_ga4_csv(filepath):
    """Load GA4 CSV, skipping header comments"""
    csv_content = skip_header_comments(filepath)
    from io import StringIO
    return pd.read_csv(StringIO(csv_content))

def join_ga4_reports(brand, input_dir, output_dir):
    """
    Join GA4 Landing Page + Item Breakdown reports
    """
    print(f"\n=== Step 1: GA4 Join for {brand} ===")
    
    # Load files
    lp_path = os.path.join(input_dir, brand, 'ga4_lp.csv')
    items_path = os.path.join(input_dir, brand, 'ga4_items.csv')
    
    if not os.path.exists(lp_path):
        print(f"ERROR: Landing Page file not found: {lp_path}")
        return False
    
    if not os.path.exists(items_path):
        print(f"ERROR: Items file not found: {items_path}")
        return False
    
    print(f"Loading Landing Page: {lp_path}")
    lp_df = load_ga4_csv(lp_path)
    print(f"  Columns: {list(lp_df.columns)}")
    print(f"  Rows: {len(lp_df)}")
    
    print(f"\nLoading Item Breakdown: {items_path}")
    items_df = load_ga4_csv(items_path)
    print(f"  Columns: {list(items_df.columns)}")
    print(f"  Rows: {len(items_df)}")
    
    # Merge strategy: We'll merge on any common columns
    # Typically this would be item-level data, but let's see what columns exist
    
    # For now, let's do a cross-check approach:
    # Landing page has sessions/revenue per page
    # Items has revenue per item_id/item_name
    # We'll create a combined view
    
    # Add source identifiers
    lp_df = lp_df.copy()
    items_df = items_df.copy()
    
    # Save merged output
    output_path = os.path.join(output_dir, brand, 'GA4_Merged.csv')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # For Step 1, we'll save both datasets side by side with prefixes
    # This is a preliminary merge - we'll refine join keys after seeing column names
    
    # Add prefix to avoid column name conflicts
    lp_df_prefixed = lp_df.add_prefix('lp_')
    items_df_prefixed = items_df.add_prefix('item_')
    
    # Create cartesian product for now (will refine with proper keys)
    # NOTE: This is intentionally naive for first pass - we'll add proper join keys
    
    # Instead, let's just concatenate them horizontally for inspection
    # Save both to same file with clear separation
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Landing Page Data\n")
        lp_df.to_csv(f, index=False)
        f.write("\n# Item Breakdown Data\n")
        items_df.to_csv(f, index=False)
    
    print(f"\n✅ Saved preliminary merge to: {output_path}")
    print(f"   (Contains both datasets for inspection)")
    
    return True

if __name__ == "__main__":
    BASE_DIR = r"c:\Users\Paweł\Documents\GitHub\Money Printing Machine"
    INPUT_DIR = os.path.join(BASE_DIR, "Input")
    OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
    
    brand = sys.argv[1] if len(sys.argv) > 1 else "Bushido"
    
    success = join_ga4_reports(brand, INPUT_DIR, OUTPUT_DIR)
    sys.exit(0 if success else 1)
