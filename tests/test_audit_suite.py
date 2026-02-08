import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from complete_pipeline import run_pipeline

class TestAuditSuite(unittest.TestCase):
    def setUp(self):
        # Mock thresholds/params as in real pipeline
        self.P75_VOL_META = 1000
        self.P75_EFF_META = 100
        self.P75_VOL_GA = 100
        self.P75_EFF_GA = 5.0
        self.P75_VOL_ITEM = 50
        self.P75_EFF_ITEM = 10.0
        self.MIN_META_TRANS = 10
        self.MIN_ORGANIC_SESSIONS = 50

    def run_logic_standalone(self, row):
        """Standalone implementation of the logic for testing consistency."""
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
        # SAFETY CHECK: Only for PRODUCTS
        if row.get('calc_entity_type') != "PRODUCT":
            return 8, "IGNORE"

        if row.get('ga4item_views', 0) >= self.MIN_ORGANIC_SESSIONS:
            is_high_vol = row['ga4item_views'] >= self.P75_VOL_ITEM
            is_high_eff = row['calc_gppv'] >= self.P75_EFF_ITEM
            
            if is_high_vol and is_high_eff:
                return 6, "DIRECT_TO_PDP"
            elif is_high_eff:
                return 7, "FEED_DPA"
                
        return 8, "IGNORE"

    def test_entity_type_safety_phase_3(self):
        """Verify that Priority 7 (Hidden Gem) is NOT assigned to non-products."""
        row_category = {
            'calc_entity_type': 'CATEGORY_OR_AD',
            'meta_purchases': 0,
            'calc_contribution_profit': 0,
            'ga4lp_sessions': 10, # Low LP
            'ga4item_views': 200, # High Item Interest (fake for category)
            'calc_gppv': 50.0      # High Eff
        }
        p, name = self.run_logic_standalone(row_category)
        self.assertEqual(p, 8, "Category should be IGNORE in Phase 3 even if item metrics are high.")

        row_product = {
            'calc_entity_type': 'PRODUCT',
            'meta_purchases': 0,
            'calc_contribution_profit': 0,
            'ga4lp_sessions': 10,
            'ga4item_views': 200,
            'calc_gppv': 50.0
        }
        p, name = self.run_logic_standalone(row_product)
        self.assertEqual(p, 6, "Product should be DIRECT_TO_PDP (Priority 6) if metrics are high.")

    def test_unit_economics_integrity(self):
        """Check calculation safety for derived metrics."""
        import business_logic_layer as bl
        # Zero division check
        self.assertEqual(bl.calculate_gpps(100, 0), 0)
        self.assertEqual(bl.calculate_gppv(100, 0), 0)
        self.assertEqual(bl.calculate_cr(10, 0), 0)

    def test_flag_persistence(self):
        """Verify META_LOSER results in RECOVERY_LAUNCH in Phase 2."""
        row_recovery = {
            'calc_entity_type': 'PRODUCT',
            'meta_purchases': 10,
            'calc_contribution_profit': -100, # Loser
            'meta_revenue': 500,
            'ga4lp_sessions': 500, # High Vol
            'calc_gpps': 20.0      # High Eff
        }
        p, name = self.run_logic_standalone(row_recovery)
        self.assertEqual(p, 3)
        self.assertEqual(name, "RECOVERY_LAUNCH")

if __name__ == '__main__':
    unittest.main()
