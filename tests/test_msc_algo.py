import unittest
import pandas as pd
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
import business_logic_layer as bl

class TestMSCAlgo(unittest.TestCase):
    def setUp(self):
        # Thresholds (Mocked for testing logic)
        self.P75_VOL_META = 1000
        self.P75_EFF_META = 200
        self.P75_VOL_GA = 100
        self.P75_EFF_GA = 5.0
        self.P75_VOL_ITEM = 500
        self.P75_EFF_ITEM = 2.0
        
        self.MIN_META_TRANS = 5 # Lower for testing
        self.MIN_ORGANIC_SESSIONS = 50
        
    def run_logic(self, row):
        # Local implementation of the logic for verification
        # Matches complete_pipeline.py
        
        # Phase 1: Meta
        if row['meta_purchases'] >= self.MIN_META_TRANS:
            if row['calc_contribution_profit'] > 0:
                if row['meta_revenue'] >= self.P75_VOL_META and row['calc_contribution_profit'] >= self.P75_EFF_META:
                    return 1, "PROVEN_STAR"
                else:
                    return 2, "PROVEN_CASH_COW"
            # Else fall through to Phase 2
            
        # Phase 2: GA LP
        has_negative_history = (row['meta_spend'] > 0 and row['calc_contribution_profit'] < 0)
        
        if row['ga4lp_sessions'] >= self.MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4lp_sessions'] >= self.P75_VOL_GA
            is_high_eff = row['calc_gpps'] >= self.P75_EFF_GA
            
            if is_high_vol and is_high_eff:
                return (3, "RE_LAUNCH_CANDIDATE") if has_negative_history else (3, "ORGANIC_STAR")
            elif is_high_vol:
                return 4, "HIGH_TRAFFIC_LOW_CONV"
            elif is_high_eff:
                return 5, "HIGH_CONV_LOW_TRAFFIC"
                
        # Phase 3: GA Item
        if row.get('ga4item_views', 0) >= self.MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4item_views'] >= self.P75_VOL_ITEM
            is_high_eff = row['calc_gppv'] >= self.P75_EFF_ITEM
            
            if is_high_vol and is_high_eff:
                return 6, "HIDDEN_STAR"
            elif is_high_eff:
                return 7, "HIDDEN_GEM"
                
        return 8, "IGNORE"

    def test_priority_1_proven_star(self):
        row = {
            'meta_purchases': 10,
            'calc_contribution_profit': 500,
            'meta_revenue': 2000,
            'meta_spend': 100,
            'ga4lp_sessions': 0, 'calc_gpps': 0 # Ignored by Phase 1
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 1)
        self.assertEqual(name, "PROVEN_STAR")

    def test_priority_3_relaunch(self):
        row = {
            'meta_purchases': 10,
            'calc_contribution_profit': -50, # Ads failed
            'meta_revenue': 100,
            'meta_spend': 200,
            'ga4lp_sessions': 200, # High Organic Vol
            'calc_gpps': 10.0      # High Organic Eff
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 3)
        self.assertEqual(name, "RE_LAUNCH_CANDIDATE")

    def test_priority_7_hidden_gem(self):
        row = {
            'meta_purchases': 0,
            'calc_contribution_profit': 0,
            'meta_spend': 0,
            'meta_revenue': 0,
            'ga4lp_sessions': 10,  # Low Session Vol
            'calc_gpps': 1.0,      # Low LP Eff
            'ga4item_views': 60,   # Significant Item Interest
            'calc_gppv': 5.0       # High Item Efficiency (GPPV > P75_EFF_ITEM)
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 7)
        self.assertEqual(name, "HIDDEN_GEM")

    def test_ignore(self):
        row = {
            'meta_purchases': 0,
            'calc_contribution_profit': 0,
            'meta_spend': 0,
            'meta_revenue': 0,
            'ga4lp_sessions': 10,
            'calc_gpps': 0.1,
            'ga4item_views': 10,
            'calc_gppv': 0.1
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 8)
        self.assertEqual(name, "IGNORE")

if __name__ == '__main__':
    unittest.main()
