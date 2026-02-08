
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
        clusters = assign_price_cluster(df, spread=0.5)
        
        # Expected:
        # 1000 -> Group 1 (Leader 1000, Threshold 500)
        # 900 -> Group 1
        # 400 -> Group 2 (Leader 400, Threshold 200)
        # 350 -> Group 2
        # 100 -> Group 3
        
        unique_labels = clusters.unique()
        self.assertEqual(len(unique_labels), 3)
        self.assertTrue('TOP 1000 PLN' in clusters.values)

    def test_calculate_contribution_profit(self):
        # Revenue 123, VAT 0.23 -> Net 100
        # Margin 0.5, Freq 1.0 -> GP 50
        # Spend 10 -> CP 40
        cp = calculate_contribution_profit(123, 0.23, 0.5, 1.0, 10)
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

    # ============ NEW TESTS FOR v2.0 METRICS ============
    
    def test_calculate_bid_cap(self):
        # Price 123 PLN, VAT 23%, Margin 50%
        # Net Price = 123 / 1.23 = 100
        # Bid Cap = 100 * 0.5 = 50
        self.assertAlmostEqual(calculate_bid_cap(123, 0.23, 0.5), 50.0, places=2)
        
        # Edge case: zero price
        self.assertEqual(calculate_bid_cap(0, 0.23, 0.5), 0.0)

    def test_calculate_cost_cap(self):
        # Bid Cap 50, Safety 0.7 -> Cost Cap 35
        self.assertAlmostEqual(calculate_cost_cap(50, 0.7), 35.0, places=2)

    def test_calculate_critical_roas(self):
        # Bid Cap 50 -> Critical ROAS = 1/50 = 0.02
        self.assertAlmostEqual(calculate_critical_roas(50), 0.02, places=4)
        
        # Edge case: zero bid cap
        self.assertEqual(calculate_critical_roas(0), 0.0)

    def test_calculate_scaling_roas(self):
        # VAT 0.23, Margin 0.5, Frequency 1.2
        # Scaling ROAS = 1 / (1.23 * 0.5 * 1.2) = 1 / 0.738 = 1.355
        self.assertAlmostEqual(calculate_scaling_roas(0.23, 0.5, 1.2), 1.355, places=2)

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
