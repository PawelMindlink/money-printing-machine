"""
MSC-ALGO FastAPI Microservice
Wraps n8n_adapter.py logic as a REST API.
POST /process → accepts JSON payload → returns classified items.
"""
import sys
import os
import json
import traceback

# Add src/ to path so we can import pipeline modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd

from complete_pipeline import run_pipeline_logic, join_and_enrich_data

app = FastAPI(
    title="MSC-ALGO API",
    description="Python SSOT for MSC-ALGO Waterfall Classification",
    version="1.0.0"
)


@app.get("/health")
def health():
    """Health check for monitoring."""
    return {"status": "ok", "service": "msc-algo"}


@app.post("/process")
def process(payload: dict):
    """
    Process n8n data through the Python pipeline.
    
    Expected payload:
    {
        "feed": [...],
        "meta_ads": [...],
        "ga4_items": [...],
        "ga4_lp": [...],
        "config": {
            "brand": "...",
            "vat_rate": 0.23,
            "default_margin": 0.10,
            "margin_rules": [...]
        }
    }
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
        raise HTTPException(status_code=500, detail=error_response)
