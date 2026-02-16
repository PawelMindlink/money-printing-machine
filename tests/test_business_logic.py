
import unittest
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from business_logic_layer import (
    calculate_gross_margin,
    assign_price_cluster,
    calculate_contribution_profit,
    classify_meta_ads,
    classify_ga4_product,
    determine_priority,
    normalize_url,
    calculate_bid_cap,
    calculate_cost_cap,
    calculate_critical_roas,
    calculate_scaling_roas,
    is_product_page
)

class TestBusinessLogic(unittest.TestCase):

    def test_calculate_gross_margin(self):
        row = {'category': 'Monitors', 'title': 'Iiyama Monitor'}
        defaults = 0.1
        overrides = [{'category': 'Monitors', 'rate': 0.15}]
        
        # Test override match
        self.assertEqual(calculate_gross_margin(row, defaults, overrides), 0.15)
        
        # Test no match
        row_no_match = {'category': 'Mice', 'title': 'Mouse'}
        self.assertEqual(calculate_gross_margin(row_no_match, defaults, overrides), 0.1)

    def test_assign_price_cluster(self):
        df = pd.DataFrame({'price_numeric': [1000, 900, 400, 350, 100]})
        clusters = assign_price_cluster(df)
        
        # Cluster logic: Leader / 1.5 = threshold for cluster break
        # 1000 -> Group 1 (Leader 1000, Threshold 666.7)
        # 900 -> Group 1 (900 >= 666.7)
        # 400 -> Group 2 (400 < 666.7, new leader)
        # 350 -> Group 2 (350 >= 266.7)
        # 100 -> Group 3 (100 < 233.3, new leader)
        
        unique_labels = clusters.unique()
        self.assertGreaterEqual(len(unique_labels), 2)
        self.assertTrue('TOP 1000 PLN' in clusters.values)

    def test_calculate_contribution_profit(self):
        # Revenue 123, VAT 0.23 -> Net 100
        # Margin 0.5 -> GP 50
        # Spend 10 -> CP 40
        cp = calculate_contribution_profit(123, 0.23, 0.5, 10)
        self.assertAlmostEqual(cp, 40.0, places=2)

    def test_classify_meta_ads(self):
        self.assertEqual(classify_meta_ads(10, 50), 'Profitable')
        self.assertEqual(classify_meta_ads(-10, 50), 'Unprofitable')
        self.assertEqual(classify_meta_ads(0, 0), 'No Ads')

    def test_classify_ga4_product(self):
        thresholds = {'min_activity': 10, 'trans_75': 5, 'arpu_75': 100}
        
        # Slacker (low sessions, low perf)
        self.assertEqual(classify_ga4_product(5, 1, 10, thresholds), 'Slacker')
        
        # Star (High Trans, High ARPU) - Even with low sessions!
        self.assertEqual(classify_ga4_product(5, 10, 200, thresholds), 'Star')
        
        # Star (High Trans, High ARPU)
        self.assertEqual(classify_ga4_product(20, 10, 150, thresholds), 'Star')
        
        # Cash Cow (High Trans, Low ARPU)
        self.assertEqual(classify_ga4_product(20, 10, 50, thresholds), 'Cash Cow')
        
        # Hidden Gem (Low Trans, High ARPU)
        self.assertEqual(classify_ga4_product(20, 2, 150, thresholds), 'Hidden Gem')

    def test_determine_priority(self):
        self.assertEqual(determine_priority('Star', 'Profitable'), 'P1')
        # New logic: Slacker + Profitable = P3 (not P7!)
        self.assertEqual(determine_priority('Slacker', 'Profitable'), 'P3')
        self.assertEqual(determine_priority('Hidden Gem', 'No Ads'), 'P6')

    def test_normalize_url(self):
        self.assertEqual(normalize_url('https://example.com/foo?bar=1'), 'example.com/foo')

    # ============ BIDDING STRATEGY TESTS (v3.0 — Anchor-Based) ============
    
    def test_calculate_bid_cap(self):
        # Per-product bid cap = full GP
        # Price 123 PLN, VAT 23%, Margin 50%
        # Net Price = 123 / 1.23 = 100
        # Bid Cap = 100 * 0.5 = 50  (full GP on the product)
        self.assertAlmostEqual(calculate_bid_cap(123, 0.23, 0.5), 50.0, places=2)
        
        # Edge case: zero price
        self.assertEqual(calculate_bid_cap(0, 0.23, 0.5), 0.0)
        
        # Iiyama scenario: 3000 PLN, margin 0.10
        # Net = 3000 / 1.23 = 2439.02, GP = 243.90
        self.assertAlmostEqual(calculate_bid_cap(3000, 0.23, 0.10), 243.90, places=0)

    def test_calculate_cost_cap(self):
        # Cost Cap = 70% of Bid Cap
        self.assertAlmostEqual(calculate_cost_cap(100), 70.0, places=2)
        self.assertAlmostEqual(calculate_cost_cap(50), 35.0, places=2)
        # Custom safety factor
        self.assertAlmostEqual(calculate_cost_cap(100, 0.60), 60.0, places=2)

    def test_calculate_critical_roas(self):
        # Critical ROAS = break-even * 1.2 = ((1+VAT) / margin) * 1.2
        # margin 0.5: break_even = 1.23/0.5 = 2.46, critical = 2.46 * 1.2 = 2.952
        self.assertAlmostEqual(calculate_critical_roas(0.23, 0.5), 2.952, places=2)
        
        # margin 0.10: break_even = 12.3, critical = 14.76
        self.assertAlmostEqual(calculate_critical_roas(0.23, 0.10), 14.76, places=2)
        
        # Edge case: zero margin
        self.assertEqual(calculate_critical_roas(0.23, 0), 0.0)

    def test_calculate_scaling_roas(self):
        # Scaling ROAS = Critical ROAS * 1.4
        # margin 0.5: critical = 2.952, scaling = 2.952 * 1.4 = 4.1328
        self.assertAlmostEqual(calculate_scaling_roas(0.23, 0.5), 4.1328, places=2)
        
        # margin 0.10: critical = 14.76, scaling = 14.76 * 1.4 = 20.664
        self.assertAlmostEqual(calculate_scaling_roas(0.23, 0.10), 20.664, places=1)

    def test_calculate_cluster_stats_anchor_based(self):
        """Cluster bid/cost cap must use anchor price (max), not average."""
        from business_logic_layer import calculate_cluster_stats
        
        # Cluster with 3 products: 3000, 2500, 2200 PLN, all margin 0.10
        df = pd.DataFrame({
            'calc_gross_price': [3000, 2500, 2200],
            'base_gross_margin': [0.10, 0.10, 0.10]
        })
        
        stats = calculate_cluster_stats(df, vat_rate=0.23)
        
        # Bid Cap = anchor GP = 3000 / 1.23 * 0.10 = 243.90
        expected_bid = 3000 / 1.23 * 0.10
        self.assertAlmostEqual(stats['bid_cap'], expected_bid, places=1)
        
        # Cost Cap = 70% of Bid Cap
        self.assertAlmostEqual(stats['cost_cap'], expected_bid * 0.70, places=1)
        
        # Bid Cap > Cost Cap (ALWAYS)
        self.assertGreater(stats['bid_cap'], stats['cost_cap'])
        
        # Avg margin is reference only (should be average of individual GPs)
        avg_gp = sum([3000/1.23*0.10, 2500/1.23*0.10, 2200/1.23*0.10]) / 3
        self.assertAlmostEqual(stats['cluster_avg_margin'], avg_gp, places=1)

    def test_bidding_invariants(self):
        """Critical invariants that must ALWAYS hold regardless of parameters."""
        test_cases = [
            (0.23, 0.10),  # Iiyama low-margin
            (0.23, 0.15),  # Iiyama accessories
            (0.23, 0.58),  # Bushido high-margin
            (0.19, 0.30),  # German VAT, mid-margin
            (0.23, 0.05),  # Very low margin
            (0.23, 0.90),  # Very high margin
        ]
        
        for vat, margin in test_cases:
            with self.subTest(vat=vat, margin=margin):
                critical = calculate_critical_roas(vat, margin)
                scaling = calculate_scaling_roas(vat, margin)
                break_even = (1 + vat) / margin
                
                # Invariant 1: Critical ROAS > pure break-even (has buffer)
                self.assertGreater(critical, break_even,
                    f"Critical ROAS ({critical:.2f}) must be > break-even ({break_even:.2f})")
                
                # Invariant 2: Scaling ROAS > Critical ROAS (scale only when over-performing)
                self.assertGreater(scaling, critical,
                    f"Scaling ROAS ({scaling:.2f}) must be > Critical ({critical:.2f})")
                
                # Invariant 3: Critical = break_even * 1.2
                self.assertAlmostEqual(critical, break_even * 1.2, places=4)
                
                # Invariant 4: Scaling = Critical * 1.4
                self.assertAlmostEqual(scaling, critical * 1.4, places=4)
                
                # Invariant 5: Per-product bid_cap > cost_cap for any price
                for price in [100, 500, 1000, 5000]:
                    bid = calculate_bid_cap(price, vat, margin)
                    cost = calculate_cost_cap(bid)
                    self.assertGreater(bid, cost,
                        f"Bid ({bid:.2f}) must be > Cost ({cost:.2f}) for price={price}")

    def test_bidding_real_iiyama(self):
        """Regression test with real Iiyama parameters."""
        from business_logic_layer import calculate_cluster_stats
        
        # Cluster: TOP 3000 PLN, 4 products, margin 0.10, VAT 0.23
        df = pd.DataFrame({
            'calc_gross_price': [2999, 2800, 2500, 2200],
            'base_gross_margin': [0.10, 0.10, 0.10, 0.10]
        })
        
        stats = calculate_cluster_stats(df, vat_rate=0.23)
        
        # Bid Cap ≈ 2999/1.23*0.10 ≈ 243.8 PLN
        self.assertAlmostEqual(stats['bid_cap'], 2999/1.23*0.10, places=0)
        
        # Cost Cap ≈ 243.8 * 0.70 ≈ 170.7 PLN
        self.assertAlmostEqual(stats['cost_cap'], stats['bid_cap'] * 0.70, places=2)
        
        # Critical ROAS = 1.23/0.10 * 1.2 = 14.76
        critical = calculate_critical_roas(0.23, 0.10)
        self.assertAlmostEqual(critical, 14.76, places=2)
        
        # Scaling ROAS = 14.76 * 1.4 = 20.664
        scaling = calculate_scaling_roas(0.23, 0.10)
        self.assertAlmostEqual(scaling, 20.664, places=1)

    def test_is_product_page(self):
        # Product page patterns
        self.assertTrue(is_product_page('https://koszulkowy.pl/12345-some-product.html'))
        self.assertTrue(is_product_page('https://example.com/p/123'))
        
        # Non-product pages
        self.assertFalse(is_product_page('/'))
        self.assertFalse(is_product_page('https://example.com/kategoria/men'))
        
        # Product ID provided
        self.assertTrue(is_product_page('/some-page', product_id='12345'))

if __name__ == '__main__':
    unittest.main()

