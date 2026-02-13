"""
Test Suite: API Output Validation
Validates that main.py correctly maps n8n fields and filters to gold-standard columns.
"""
import unittest
import sys
import os

# Add project root and src to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import pandas as pd


class TestColumnConstants(unittest.TestCase):
    """Test that main.py constants are correctly defined."""

    def setUp(self):
        # Import main.py constants
        import main as m
        self.GOLD_STANDARD_COLS = m.GOLD_STANDARD_COLS
        self.FEED_REMAP = m.FEED_REMAP
        self.ITEMS_REMAP = m.ITEMS_REMAP
        self.LP_REMAP = m.LP_REMAP
        self.META_REMAP = m.META_REMAP
        self.filter_output = m._filter_output

    def test_gold_standard_has_43_columns(self):
        """Gold standard should have 43 columns (42 + calc_entity_type)."""
        self.assertEqual(len(self.GOLD_STANDARD_COLS), 43)

    def test_gold_standard_key_columns_present(self):
        """All critical columns must be in GOLD_STANDARD_COLS."""
        required = [
            "feed_id", "feed_title", "feed_brand", "feed_category",
            "calc_gross_price", "is_product", "is_price_inferred",
            "feed_link", "norm_url",
            "calc_priority", "calc_segment", "calc_reason",
            "calc_is_actionable", "calc_action_type",
            "meta_class", "ga4_class",
            "base_gross_margin", "calc_contribution_profit",
            "calc_price_cluster",
            "critical_roas", "scaling_roas", "calc_break_even_roas",
            "calc_bid_cap", "calc_cost_cap",
            "meta_spend", "meta_revenue", "meta_purchases",
            "ga4lp_sessions", "ga4lp_revenue", "ga4lp_purchases",
            "ga4item_views", "ga4item_revenue",
        ]
        for col in required:
            self.assertIn(col, self.GOLD_STANDARD_COLS,
                          f"Missing gold-standard column: {col}")

    def test_no_old_pipeline_columns(self):
        """Gold standard must NOT contain old pipeline columns."""
        old_cols = ["brand", "sku", "title", "price", "category", "margin",
                    "msc_class", "msc_reason", "_merge_source",
                    "_has_ga4_item", "_has_ga4_lp", "_has_meta"]
        for col in old_cols:
            self.assertNotIn(col, self.GOLD_STANDARD_COLS,
                             f"Old pipeline column should not be in gold standard: {col}")


class TestRemapMappings(unittest.TestCase):
    """Test that remap dictionaries contain required keys."""

    def setUp(self):
        import main as m
        self.LP_REMAP = m.LP_REMAP
        self.META_REMAP = m.META_REMAP

    def test_meta_remap_has_url(self):
        """META_REMAP must map meta_url to Link (ad settings)."""
        self.assertIn("meta_url", self.META_REMAP)
        self.assertEqual(self.META_REMAP["meta_url"], "Link (ad settings)")

    def test_meta_remap_has_backward_compat_url(self):
        """META_REMAP must also map meta_ad_url for backward compat."""
        self.assertIn("meta_ad_url", self.META_REMAP)
        self.assertEqual(self.META_REMAP["meta_ad_url"], "Link (ad settings)")

    def test_meta_remap_has_spend(self):
        self.assertIn("meta_spend", self.META_REMAP)

    def test_meta_remap_has_revenue(self):
        self.assertIn("meta_rev", self.META_REMAP)

    def test_lp_remap_has_users(self):
        """LP_REMAP must map ga4_users to Users."""
        self.assertIn("ga4_users", self.LP_REMAP)
        self.assertEqual(self.LP_REMAP["ga4_users"], "Users")

    def test_lp_remap_has_first_time_purchasers(self):
        """LP_REMAP must map ga4_first_time_purchasers."""
        self.assertIn("ga4_first_time_purchasers", self.LP_REMAP)
        self.assertEqual(
            self.LP_REMAP["ga4_first_time_purchasers"],
            "First time purchasers"
        )


class TestFilterOutput(unittest.TestCase):
    """Test that _filter_output correctly filters to gold-standard columns."""

    def setUp(self):
        import main as m
        self.filter_output = m._filter_output
        self.GOLD_STANDARD_COLS = m.GOLD_STANDARD_COLS

    def test_filter_removes_extra_columns(self):
        """Extra columns not in gold standard should be removed."""
        # Create a DataFrame with gold-standard + extra columns
        data = {col: [0] for col in self.GOLD_STANDARD_COLS}
        data["brand"] = ["test"]
        data["sku"] = ["123"]
        data["msc_class"] = ["A"]
        data["_merge_source"] = ["test"]
        df = pd.DataFrame(data)

        result = self.filter_output(df)
        self.assertEqual(len(result.columns), len(self.GOLD_STANDARD_COLS))
        self.assertNotIn("brand", result.columns)
        self.assertNotIn("sku", result.columns)
        self.assertNotIn("msc_class", result.columns)

    def test_filter_preserves_gold_columns(self):
        """All gold-standard columns that exist should be preserved."""
        data = {col: [0] for col in self.GOLD_STANDARD_COLS}
        df = pd.DataFrame(data)

        result = self.filter_output(df)
        self.assertEqual(list(result.columns), list(self.GOLD_STANDARD_COLS))

    def test_filter_handles_missing_columns_gracefully(self):
        """If some gold-standard columns are missing, filter should not crash."""
        data = {"feed_id": ["1"], "feed_title": ["test"]}
        df = pd.DataFrame(data)

        result = self.filter_output(df)
        self.assertEqual(len(result.columns), 2)
        self.assertIn("feed_id", result.columns)
        self.assertIn("feed_title", result.columns)


class TestHealthEndpoint(unittest.TestCase):
    """Test that /health returns version information."""

    def test_health_returns_version(self):
        import main as m
        from fastapi.testclient import TestClient
        client = TestClient(m.app)
        resp = client.get("/health")
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)
        self.assertIn("gold_standard_cols", data)
        self.assertEqual(data["gold_standard_cols"], 43)


class TestMetaPrepare(unittest.TestCase):
    """Test that _prepare_meta correctly handles meta_url from n8n."""

    def setUp(self):
        import main as m
        self.prepare_meta = m._prepare_meta

    def test_meta_url_remapped_to_link(self):
        """meta_url from n8n should become 'Link (ad settings)' for SmartMatcher."""
        df = pd.DataFrame([{
            "meta_url": "https://iiyama.pl/product/123",
            "meta_spend": 100.0,
            "meta_purch": 5,
            "meta_rev": 500.0
        }])
        result = self.prepare_meta(df)
        self.assertIn("Link (ad settings)", result.columns)
        self.assertEqual(result["Link (ad settings)"].iloc[0],
                         "https://iiyama.pl/product/123")

    def test_meta_without_url_gets_empty(self):
        """If no URL field exists, column should be created as empty."""
        df = pd.DataFrame([{
            "meta_spend": 100.0,
            "meta_purch": 5,
            "meta_rev": 500.0
        }])
        result = self.prepare_meta(df)
        self.assertIn("Link (ad settings)", result.columns)
        self.assertEqual(result["Link (ad settings)"].iloc[0], "")


class TestLPPrepare(unittest.TestCase):
    """Test that _prepare_lp correctly maps all GA4 LP fields from n8n."""

    def setUp(self):
        import main as m
        self.prepare_lp = m._prepare_lp

    def test_lp_users_mapped(self):
        """ga4_users from n8n should become 'Users'."""
        df = pd.DataFrame([{
            "ga4_lp_url": "/product/123",
            "ga4_sessions": 100,
            "ga4_revenue": 5000.0,
            "ga4_trans": 10,
            "ga4_users": 80,
            "ga4_first_time_purchasers": 60
        }])
        result = self.prepare_lp(df)
        self.assertIn("Users", result.columns)
        self.assertEqual(result["Users"].iloc[0], 80)
        self.assertIn("First time purchasers", result.columns)
        self.assertEqual(result["First time purchasers"].iloc[0], 60)


if __name__ == "__main__":
    unittest.main()
