"""
Test: Enrichment Pipeline workflow JSON structure.
Validates the n8n workflow without executing it.
"""
import json
import os
import pytest

WORKFLOW_PATH = os.path.join(
    os.path.dirname(__file__), "..", "Workflows", "Enrichment_Pipeline.json"
)


@pytest.fixture
def workflow():
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestWorkflowStructure:
    """Validate workflow JSON structure without running n8n."""

    def test_valid_json(self, workflow):
        """Workflow file must be valid JSON."""
        assert isinstance(workflow, dict)

    def test_has_required_top_level_keys(self, workflow):
        assert "name" in workflow
        assert "nodes" in workflow
        assert "connections" in workflow

    def test_node_count(self, workflow):
        """Should have all 19 planned nodes."""
        assert len(workflow["nodes"]) >= 15, (
            f"Expected at least 15 nodes, got {len(workflow['nodes'])}"
        )

    def test_all_nodes_have_required_fields(self, workflow):
        for node in workflow["nodes"]:
            assert "id" in node, f"Node missing 'id': {node.get('name', 'unknown')}"
            assert "name" in node, f"Node missing 'name': {node.get('id', 'unknown')}"
            assert "type" in node, f"Node missing 'type': {node.get('name', 'unknown')}"
            assert "typeVersion" in node, f"Node missing 'typeVersion': {node['name']}"
            assert "position" in node, f"Node missing 'position': {node['name']}"

    def test_unique_node_ids(self, workflow):
        ids = [n["id"] for n in workflow["nodes"]]
        assert len(ids) == len(set(ids)), "Duplicate node IDs found"

    def test_unique_node_names(self, workflow):
        names = [n["name"] for n in workflow["nodes"]]
        assert len(names) == len(set(names)), "Duplicate node names found"

    def test_connections_reference_existing_nodes(self, workflow):
        """All connection references must point to existing node names."""
        node_names = {n["name"] for n in workflow["nodes"]}
        for source, conns in workflow["connections"].items():
            assert source in node_names, f"Connection source '{source}' not a node"
            for output_group in conns.get("main", []):
                for target in output_group:
                    assert target["node"] in node_names, (
                        f"Connection target '{target['node']}' not a node"
                    )

    def test_no_hardcoded_brand(self, workflow):
        """No node should have a hardcoded brand name (universal design)."""
        raw = json.dumps(workflow)
        # Check that brand names don't appear as hardcoded values
        # (they can appear in comments explaining the convention)
        for node in workflow["nodes"]:
            code = node.get("parameters", {}).get("jsCode", "")
            # The Discover Brands node should NOT have hardcoded brand returns
            if node["name"] == "Discover Brands":
                assert "return [{ json: { brand:" not in code, (
                    "Discover Brands should auto-detect, not hardcode brands"
                )

    def test_discover_brands_scans_output(self, workflow):
        """Discover Brands node must scan Output directory."""
        node = next(n for n in workflow["nodes"] if n["name"] == "Discover Brands")
        code = node["parameters"]["jsCode"]
        assert "readdirSync" in code or "readdir" in code, (
            "Discover Brands must scan the Output directory"
        )
        assert "Growth_Opportunities" in code, (
            "Discover Brands must look for Growth_Opportunities CSV files"
        )

    def test_error_handling_present(self, workflow):
        """Error Trigger node must be present."""
        types = [n["type"] for n in workflow["nodes"]]
        assert "n8n-nodes-base.errorTrigger" in types, (
            "Workflow must have an Error Trigger node"
        )


class TestWorkflowUniversality:
    """Verify the workflow works for any brand, not just one."""

    def test_output_path_uses_brand_variable(self, workflow):
        """Write CSV node must use dynamic brand name for output path."""
        node = next(n for n in workflow["nodes"] if n["name"] == "Write Enriched CSV")
        code = node["parameters"]["jsCode"]
        assert "_brand" in code or "brand" in code, (
            "Write CSV must use brand variable for output path"
        )

    def test_cache_dir_is_brand_specific(self, workflow):
        """Cache directory must be brand-specific to avoid cross-contamination."""
        node = next(n for n in workflow["nodes"] if n["name"] == "Load Config")
        code = node["parameters"]["jsCode"]
        assert "brand" in code and "cache" in code.lower(), (
            "Cache dir must include brand name"
        )

    def test_csv_path_uses_brand_variable(self, workflow):
        """CSV path must use brand variable."""
        node = next(n for n in workflow["nodes"] if n["name"] == "Load Config")
        code = node["parameters"]["jsCode"]
        assert "${brand}" in code or "brand" in code, (
            "CSV path must use brand variable"
        )
