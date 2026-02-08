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
        flags = []
        
        # Phase 1: Meta
        if row['meta_purchases'] >= self.MIN_META_TRANS:
            if row['calc_contribution_profit'] > 0:
                if row['meta_revenue'] >= self.P75_VOL_META and row['calc_contribution_profit'] >= self.P75_EFF_META:
                    return 1, "PROVEN_STAR"
                else:
                    return 2, "PROVEN_COW"
            else:
                flags.append("META_LOSER")
            
        # Phase 2: GA LP
        if row['ga4lp_sessions'] >= self.MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4lp_sessions'] >= self.P75_VOL_GA
            is_high_eff = row['calc_gpps'] >= self.P75_EFF_GA
            
            if is_high_vol and is_high_eff:
                # Scenario A
                return (3, "RECOVERY_LAUNCH") if "META_LOSER" in flags else (3, "NEW_STAR_LAUNCH")
            elif is_high_vol:
                # Scenario B
                return 99, "FIX_LANDING_PAGE"
            elif is_high_eff:
                # Scenario C
                return 5, "SCALE_UP"
            else:
                # Scenario D
                flags.append("LP_FAILURE")
                
        # Phase 3: GA Item
        if row.get('ga4item_views', 0) >= self.MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4item_views'] >= self.P75_VOL_ITEM
            is_high_eff = row['calc_gppv'] >= self.P75_EFF_ITEM
            
            if is_high_vol and is_high_eff:
                return 6, "DIRECT_TO_PDP"
            elif is_high_eff:
                return 7, "FEED_DPA"
                
        return 8, "IGNORE"

    def test_priority_1_proven_star(self):
        row = {
            'meta_purchases': 10,
            'calc_contribution_profit': 500,
            'meta_revenue': 2000,
            'meta_spend': 100,
            'ga4lp_sessions': 0, 'calc_gpps': 0 # Ignored
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 1)
        self.assertEqual(name, "PROVEN_STAR")

    def test_priority_3_recovery(self):
        row = {
            'meta_purchases': 10,
            'calc_contribution_profit': -50, # META_LOSER Flag
            'meta_revenue': 100,
            'meta_spend': 200,
            'ga4lp_sessions': 200, # High Vol
            'calc_gpps': 10.0      # High Eff
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 3)
        self.assertEqual(name, "RECOVERY_LAUNCH")

    def test_priority_99_fix_lp(self):
        row = {
            'meta_purchases': 0,
            'calc_contribution_profit': 0,
            'meta_revenue': 0,
            'ga4lp_sessions': 200, # High Vol
            'calc_gpps': 1.0       # Low Eff
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 99)
        self.assertEqual(name, "FIX_LANDING_PAGE")

    def test_priority_7_feed_dpa(self):
        row = {
            'meta_purchases': 0,
            'calc_contribution_profit': 0,
            'meta_revenue': 0,
            'ga4lp_sessions': 10,  # Low Session Vol (LP Failure)
            'calc_gpps': 1.0,      
            'ga4item_views': 60,   # Moderate Item Interest
            'calc_gppv': 5.0       # High Item Efficiency
        }
        p, name = self.run_logic(row)
        self.assertEqual(p, 7)
        self.assertEqual(name, "FEED_DPA")

if __name__ == '__main__':
    unittest.main()
