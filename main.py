"""
MSC-ALGO FastAPI Microservice (Root)
Wraps src/complete_pipeline.py logic as a REST API.
POST /process → accepts JSON payload → returns classified items.
"""
import sys
import os
import json
import traceback

# Add project root AND src/ to path so complete_pipeline.py's internal imports work
_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, 'src'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd

# Import logic from src
from src.complete_pipeline import run_pipeline_logic, join_and_enrich_data

app = FastAPI(
    title="MSC-ALGO API",
    description="Python SSOT for MSC-ALGO Waterfall Classification",
    version="1.0.1"
)


@app.get("/health")
def health():
    """Health check for monitoring."""
    return {"status": "ok", "service": "msc-algo-root"}


@app.post("/process")
def process(payload: dict):
    """
    Process n8n data through the Python pipeline.
    """
    try:
        # Handle both direct object and list wrapper
        data = payload
        if isinstance(data, list):
            if not data:
                return JSONResponse(content=[])
            data = data[0]

        # Extract inputs
        feed_data = data.get('feed', [])
        meta_data = data.get('meta_ads', [])
        ga4_items_data = data.get('ga4_items', [])
        ga4_lp_data = data.get('ga4_lp', [])

        # Convert to DataFrames
        feed_df = pd.DataFrame(feed_data) if feed_data else pd.DataFrame()
        meta_df = pd.DataFrame(meta_data) if meta_data else pd.DataFrame()
        items_df = pd.DataFrame(ga4_items_data) if ga4_items_data else pd.DataFrame()
        lp_df = pd.DataFrame(ga4_lp_data) if ga4_lp_data else pd.DataFrame()

        # Config
        config_in = data.get('config', {})
        params = {
            'brand': config_in.get('brand', 'N8N_Run'),
            'vat': float(config_in.get('vat_rate', 0.23)),
            'default_margin': float(config_in.get('default_margin', 0.5)),
            'min_margin': float(config_in.get('min_margin', 0.1)),
            'category_overrides': config_in.get('category_overrides', []),
            'margin_rules_df': None
        }

        # Validation
        if feed_df.empty and meta_df.empty:
            return JSONResponse(content=[])

        # Join & Enrich (SmartMatcher)
        df, threshold_params = join_and_enrich_data(feed_df, items_df, lp_df, meta_df, params)
        params.update(threshold_params)

        # Run Logic (Waterfall)
        result_df = run_pipeline_logic(df, params)

        # Output
        result = json.loads(result_df.to_json(orient='records', date_format='iso'))
        return JSONResponse(content=result)

    except Exception as e:
        error_response = {
            "error": str(e),
            "trace": traceback.format_exc()
        }
        # Print stack trace to logs
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_response)
