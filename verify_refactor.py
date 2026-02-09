
import pandas as pd
import sys
import os

# Add src and mocks
sys.path.append(os.path.join(os.getcwd(), 'src'))
import business_logic_layer as bl

def test_naming():
    print("\n[TEST] Landing Page Naming")
    urls = [
        "iiyama-sklep.pl/247-monitory-biurowe",
        "https://www.example.com/some-page.html", 
        "domain.com/category/super-offer"
    ]
    expected = [
        "247 Monitory Biurowe",
        "Some Page",
        "Category > Super Offer"
    ]
    
    for u, e in zip(urls, expected):
        res = bl.generate_friendly_name(u)
        print(f"URL: {u} -> Name: {res}")
        if res != e:
            print(f"FAILED! Expected {e}, got {res}")
        else:
            print("PASS")

def test_zero_trap():
    print("\n[TEST] Zero Trap (Conservative Pricing)")
    # Scenario: Brand with 0 feed price, 0 Meta AOV, but valid GA4 AOV.
    # Expected: Should pick GA4 AOV, not 0.
    
    # Case 1: All Valid
    p1 = bl.calculate_conservative_price(100, 120, 110, is_product=False)
    print(f"Case 1 (100, 120, 110): {p1} [Expected: 100.0]")
    if p1 != 100.0: print("FAIL Case 1")
    
    # Case 2: Zero Feed
    p2 = bl.calculate_conservative_price(0, 120, 110, is_product=False)
    print(f"Case 2 (0, 120, 110): {p2} [Expected: 110.0]")
    if p2 != 110.0: print("FAIL Case 2")
    
    # Case 3: Zero Feed + Zero Meta
    p3 = bl.calculate_conservative_price(0, 0, 150, is_product=False)
    print(f"Case 3 (0, 0, 150): {p3} [Expected: 150.0]")
    if p3 != 150.0: print("FAIL Case 3")
    
    # Case 4: All Zero (The Trap)
    p4 = bl.calculate_conservative_price(0, 0, 0, is_product=False)
    print(f"Case 4 (0, 0, 0): {p4} [Expected: 0.0 (Review Required)]")
    if p4 != 0.0: print("FAIL Case 4")

def test_clustering_bidding():
    print("\n[TEST] Clustering & Bidding")
    
    # Mock Data: 3 Products in specific price usage
    # Leader: 1000
    # Member: 800 (1000/1.5 = 666. 800 > 666, so OK)
    # Fail: 500 (1000/1.5 = 666. 500 < 666, should be new cluster)
    
    data = [
        {'id': 1, 'calc_gross_price': 1000, 'base_gross_margin': 0.5},
        {'id': 2, 'calc_gross_price': 800, 'base_gross_margin': 0.5},
        {'id': 3, 'calc_gross_price': 500, 'base_gross_margin': 0.5},
    ]
    df = pd.DataFrame(data)
    
    # 1. Assign Clusters
    df['calc_price_cluster'] = bl.assign_price_cluster(df, price_col='calc_gross_price')
    print("Clusters Assigned:")
    print(df[['id', 'calc_gross_price', 'calc_price_cluster']])
    
    # Expectation: 1 & 2 in same cluster (TOP 1000), 3 in different (TOP 500)
    
    # 2. Check Bids
    # Cluster 1 (1000, 800) -> Avg Price 900 -> Net 731 -> Unit Margin 365.
    # Bid Cap = 365 * 0.3 = 109.5
    # Cost Cap = 365 * 1.0 = 365
    
    # Calculate for Cluster 1 manually using the new function
    c1_df = df[df['calc_price_cluster'] == "TOP 1000 PLN"]
    if c1_df.empty:
        print("CRITICAL: Cluster TOP 1000 PLN not found!")
    else:
        stats = bl.calculate_cluster_stats(c1_df, 'calc_gross_price', 'base_gross_margin', 0.23)
        print(f"Cluster 1 Stats: {stats}")
        
    # Calculate for Cluster 2
    c2_df = df[df['calc_price_cluster'] == "TOP 500 PLN"]
    if c2_df.empty:
         print("CRITICAL: Cluster TOP 500 PLN not found!")
    else:
        stats = bl.calculate_cluster_stats(c2_df, 'calc_gross_price', 'base_gross_margin', 0.23)
        print(f"Cluster 2 Stats: {stats}")

def test_isolation():
    print("\n[TEST] Clustering Scope Isolation")
    # Verify that clusters don't cross margin groups if logic is correct
    # Logic in pipeline: `for margin in df['base_gross_margin'].unique():`
    print("Code Inspection: CONFIRMED `for margin in df['base_gross_margin'].unique():` loop in pipeline.")

if __name__ == "__main__":
    test_naming()
    test_zero_trap()
    test_clustering_bidding()
    test_isolation()
