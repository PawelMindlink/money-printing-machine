"""
Test Suite: n8n Workflow JSON Structure Validation
Validates that MSC_ALGO_v5_Hybrid.json has all required structure.

Updated 2026-02-15: Aligned with current workflow state (21 nodes,
Clear Output Sheet removed, ecommercePurchases metric, limit 1000).
"""
import unittest
import json
import os

WORKFLOW_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "Workflows", "MSC_ALGO_v5_Hybrid.json"
)


class TestN8nWorkflowStructure(unittest.TestCase):
    """Validate n8n workflow JSON has correct structure."""

    @classmethod
    def setUpClass(cls):
        with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
            cls.wf = json.load(f)
        cls.nodes = {n["name"]: n for n in cls.wf["nodes"]}
        cls.connections = cls.wf["connections"]

    # ------------------------------------------------------------------
    # FIX 1: Fetch Meta Ads includes website_url
    # ------------------------------------------------------------------
    def test_meta_ads_has_website_url_field(self):
        node = self.nodes["Fetch Meta Ads"]
        fields_param = next(
            p for p in node["parameters"]["queryParameters"]["parameters"]
            if p["name"] == "fields"
        )
        self.assertIn("website_url", fields_param["value"],
                       "Fetch Meta Ads must request website_url field from Facebook API")

    # ------------------------------------------------------------------
    # FIX 2: Normalize Meta Ads maps website_url → meta_url
    # ------------------------------------------------------------------
    def test_normalize_meta_ads_maps_url(self):
        node = self.nodes["Normalize Meta Ads"]
        code = node["parameters"]["jsCode"]
        self.assertIn("meta_url", code,
                       "Normalize Meta Ads must output meta_url field")
        self.assertIn("website_url", code,
                       "Normalize Meta Ads must read ad.website_url")

    # ------------------------------------------------------------------
    # FIX 3: Fetch GA4 LP has 5 metrics (ecommercePurchases, not transactions)
    # ------------------------------------------------------------------
    def test_ga4_lp_has_five_metrics(self):
        node = self.nodes["Fetch GA4 Landing Page"]
        body = node["parameters"]["jsonBody"]
        for metric in ["sessions", "purchaseRevenue", "ecommercePurchases",
                       "totalUsers", "firstTimePurchasers"]:
            self.assertIn(metric, body,
                          f"GA4 LP must request metric '{metric}'")

    def test_ga4_lp_has_limit(self):
        """GA4 LP must have a limit to avoid excessive API calls."""
        node = self.nodes["Fetch GA4 Landing Page"]
        body = node["parameters"]["jsonBody"]
        self.assertIn("limit", body,
                       "GA4 LP must have a limit parameter")

    def test_ga4_lp_ordered_by_sessions(self):
        """GA4 LP should order by sessions DESC for deterministic results."""
        node = self.nodes["Fetch GA4 Landing Page"]
        body = node["parameters"]["jsonBody"]
        self.assertIn("orderBys", body,
                       "GA4 LP should have orderBys")

    # ------------------------------------------------------------------
    # FIX 4: Normalize GA4 LP maps 5 metrics
    # ------------------------------------------------------------------
    def test_normalize_ga4_lp_maps_five_metrics(self):
        node = self.nodes["Normalize GA4 LP"]
        code = node["parameters"]["jsCode"]
        for field in ["ga4_sessions", "ga4_revenue", "ga4_trans",
                      "ga4_users", "ga4_first_time_purchasers"]:
            self.assertIn(field, code,
                          f"Normalize GA4 LP must output '{field}'")

    def test_normalize_ga4_lp_reads_five_metric_values(self):
        node = self.nodes["Normalize GA4 LP"]
        code = node["parameters"]["jsCode"]
        for i in range(5):
            self.assertIn(f"metricValues[{i}]", code,
                          f"Normalize GA4 LP must read metricValues[{i}]")

    # ------------------------------------------------------------------
    # FIX 5: Connection chain (Parse → Output directly, no Clear node)
    # ------------------------------------------------------------------
    def test_connection_chain_parse_to_output(self):
        """Parse API Response connects directly to Output to Google Sheets."""
        parse_targets = [
            c["node"] for c in self.connections["Parse API Response"]["main"][0]
        ]
        self.assertIn("Output to Google Sheets", parse_targets,
                       "Parse API Response must connect to Output to Google Sheets")

    # ------------------------------------------------------------------
    # SANITY: Total nodes and connections
    # ------------------------------------------------------------------
    def test_total_nodes(self):
        self.assertEqual(len(self.wf["nodes"]), 21,
                         "Workflow should have 21 nodes")

    def test_python_bridge_has_four_inputs(self):
        """Python Bridge should receive from all 4 normalize nodes."""
        bridge_inputs = []
        for src_name, conns in self.connections.items():
            for output_group in conns.get("main", []):
                for conn in output_group:
                    if conn["node"] == "Python Bridge":
                        bridge_inputs.append(src_name)
        expected = {"Normalize Feed + Margins", "Normalize GA4 Items",
                    "Normalize GA4 LP", "Normalize Meta Ads"}
        self.assertEqual(set(bridge_inputs), expected,
                         "Python Bridge must receive from all 4 normalize nodes")


if __name__ == "__main__":
    unittest.main()
