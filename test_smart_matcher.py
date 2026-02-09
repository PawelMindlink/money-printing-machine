
"""
Test script for SmartMatcher Matching Cascade.
Verifies that the 377 PLN ghost product issue is resolved for Koszulkowy.
"""
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.getcwd(), 'src'))
import business_logic_layer as bl

def test_id_extraction():
    print("\n[TEST] ID Extraction from URLs")
    test_cases = [
        ('/35946-beze-mnie-ten-przybytek.html', '35946'),
        ('/p/12345-super-product', '12345'),
        ('/kubek-super-tata.html', None),
        ('/kategoria/123-short-id', None),  # Too short (3 digits)
        ('/product/99999-long-name-here.html', '99999'),
    ]
    
    for url, expected in test_cases:
        result = bl.SmartMatcher.extract_id_from_url(url)
        status = 'PASS' if result == expected else 'FAIL'
        print(f"  {status}: '{url}' -> '{result}' (expected: '{expected}')")

def test_tokenizer():
    print("\n[TEST] URL Tokenizer")
    urls = [
        '/35946-beze-mnie-ten-przybytek.html',
        '/kubek-super-tata-promocja'
    ]
    
    for url in urls:
        tokens = bl.SmartMatcher.tokenize_url(url)
        print(f"  URL: {url} -> Tokens: {tokens}")

def test_subset_inclusion():
    print("\n[TEST] Subset Inclusion")
    short = {'beze', 'mnie', 'ten'}
    long_match = {'beze', 'mnie', 'ten', 'przybytek', 'extra'}
    long_no_match = {'kubek', 'super', 'tata'}
    
    score1 = bl.SmartMatcher.subset_inclusion(short, long_match)
    score2 = bl.SmartMatcher.subset_inclusion(short, long_no_match)
    
    print(f"  Short in Long (match): {score1:.2f} (expected: 1.0)")
    print(f"  Short in Long (no match): {score2:.2f} (expected: 0.0)")

def test_smart_matcher_integration():
    print("\n[TEST] SmartMatcher Integration (Simulated Feed)")
    
    # Create a mock Feed DataFrame
    feed_data = [
        {'feed_id': '35946', 'feed_title': 'Beze Mnie Ten Przybytek', 'norm_url': '/35946-beze-mnie-ten-przybytek.html', 'feed_price': 69.90},
        {'feed_id': '10001', 'feed_title': 'Kubek Super Tata', 'norm_url': '/10001-kubek-super-tata.html', 'feed_price': 25.00},
        {'feed_id': '20002', 'feed_title': 'Koszulka Ranczo', 'norm_url': '/20002-koszulka-fanow-serialu-ranczo.html', 'feed_price': 89.00},
    ]
    feed_df = pd.DataFrame(feed_data)
    
    # Initialize SmartMatcher
    matcher = bl.SmartMatcher(feed_df, id_col='feed_id', url_col='norm_url')
    
    # Test Case: Meta Ads row with shortened URL (the Ghost problem)
    meta_rows = [
        # Case 1: ID in URL but different format
        {'meta_id': 'A1', 'norm_url': '/35946-beze-mnie.html', 'meta_revenue': 377.67},
        # Case 2: Full URL match
        {'meta_id': 'A2', 'norm_url': '/10001-kubek-super-tata.html', 'meta_revenue': 50.00},
        # Case 3: Completely unknown URL
        {'meta_id': 'A3', 'norm_url': '/unknown-product.html', 'meta_revenue': 100.00},
    ]
    meta_df = pd.DataFrame(meta_rows)
    
    for idx, row in meta_df.iterrows():
        match_idx, method = matcher.find_best_match(row)
        if match_idx is not None:
            matched_title = feed_df.loc[match_idx, 'feed_title']
            matched_price = feed_df.loc[match_idx, 'feed_price']
            print(f"  {row['meta_id']}: URL '{row['norm_url'][:40]}...' -> MATCH via {method}")
            print(f"       Matched: '{matched_title}' @ {matched_price} PLN")
        else:
            print(f"  {row['meta_id']}: URL '{row['norm_url'][:40]}...' -> NO MATCH")

def test_koszulkowy_real_data():
    print("\n[TEST] Koszulkowy Real Data Check")
    
    # Load the actual output
    output_path = os.path.join('Output', 'Koszulkowy', 'Koszulkowy_Growth_Opportunities.csv')
    
    if not os.path.exists(output_path):
        print(f"  [SKIP] Output file not found: {output_path}")
        return
        
    df = pd.read_csv(output_path)
    
    # Find the problematic row (377 PLN T-shirt)
    high_price_items = df[df['calc_gross_price'] > 300]
    koszulki = high_price_items[high_price_items['feed_title'].str.contains('Koszul', case=False, na=False)]
    
    if not koszulki.empty:
        print(f"  [WARNING] Found {len(koszulki)} high-priced T-shirts:")
        print(koszulki[['feed_title', 'calc_gross_price', 'feed_id']].head())
    else:
        print("  [PASS] No high-priced T-shirt anomalies found.")
    
    # Check for Ghost Products (is_product=True but no feed_id)
    ghosts = df[(df['is_product']) & (df['feed_id'].isna() | (df['feed_id'] == ''))]
    print(f"  Ghost Products (no feed_id): {len(ghosts)}")

if __name__ == "__main__":
    test_id_extraction()
    test_tokenizer()
    test_subset_inclusion()
    test_smart_matcher_integration()
    test_koszulkowy_real_data()
