import sys
import json
import pandas as pd
import os
import io

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from complete_pipeline import run_pipeline_logic, join_and_enrich_data

def _require_config(config, key, display_name):
    """Require a config key, raise clear error if missing."""
    value = config.get(key)
    if value is None:
        raise ValueError(
            f"[MSC-ALGO] FATAL: '{display_name}' not found in config. "
            f"This must be set in brand_config sheet of the Margin Rules Template. "
            f"Without it, all financial calculations will be wrong. "
            f"Example values: default_margin=0.10 (Iiyama), 0.58 (Bushido)."
        )
    return float(value)

def main():
    """
    N8N Adapter:
    1. Reads JSON from Stdin (Object with keys: feed, meta_ads, ga4_items, ga4_lp).
    2. Converts lists to DataFrames.
    3. Runs join_and_enrich_data (SmartMatcher included).
    4. Runs pipeline logic.
    5. Prints JSON to Stdout.
    """
    
    # 1. Read Input
    try:
        if sys.stdin.isatty():
            print(json.dumps({"error": "No input provided via pipe"}))
            return

        input_str = sys.stdin.read()
        if not input_str:
            print(json.dumps([]))
            return
            
        data = json.loads(input_str)
        
        # Support both formats: 
        # A) Direct object { "feed": [...], ... }
        # B) List from N8N [ { "feed": [...], ... } ] -> take first item
        
        if isinstance(data, list):
            if not data:
                print(json.dumps([]))
                return
            data = data[0]
            
        # Extract inputs
        feed_data = data.get('feed', [])
        meta_data = data.get('meta_ads', [])
        ga4_items_data = data.get('ga4_items', [])
        ga4_lp_data = data.get('ga4_lp', [])
        
        # Convert to DFs
        feed_df = pd.DataFrame(feed_data) if feed_data else pd.DataFrame()
        meta_df = pd.DataFrame(meta_data) if meta_data else pd.DataFrame()
        items_df = pd.DataFrame(ga4_items_data) if ga4_items_data else pd.DataFrame()
        lp_df = pd.DataFrame(ga4_lp_data) if ga4_lp_data else pd.DataFrame()
        
        # Config Params (from input or defaults)
        # We try to find config in 'config' key or defaults
        config_in = data.get('config', {})
        
        params = {
            'brand': config_in.get('brand', 'N8N_Run'),
            'vat': float(config_in.get('vat_rate', 0.23)),
            'default_margin': _require_config(config_in, 'default_margin', 'default_margin'),
            'min_margin': float(config_in.get('min_margin', 0.1)),
            'category_overrides': config_in.get('category_overrides', []),
        }
        
        # 3. Validation
        if feed_df.empty and meta_df.empty:
             # Just return empty or error?
             # Return empty list
             print(json.dumps([]))
             return

        # 4. Join & Enrich (Includes SmartMatcher)
        df, threshold_params = join_and_enrich_data(feed_df, items_df, lp_df, meta_df, params)
        
        # Merge thresholds into params for Logic Phase
        params.update(threshold_params)
        
        # 5. Run Logic (Waterfall)
        result_df = run_pipeline_logic(df, params)
        
        # 6. Output
        output_json = result_df.to_json(orient='records', date_format='iso')
        print(output_json)
        
    except Exception as e:
        # Wrap error
        import traceback
        error_response = {
            "error": str(e),
            "trace": traceback.format_exc()
        }
        print(json.dumps([error_response]))

if __name__ == "__main__":
    main()
