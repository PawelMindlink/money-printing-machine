"""
Flask API Server for Money Printing Machine Pipeline
Run with: python src/api_server.py
n8n can call via HTTP Request node: POST http://localhost:5000/run_pipeline
"""
from flask import Flask, request, jsonify
import sys
import os

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from complete_pipeline import run_pipeline
import json

app = Flask(__name__)

# Load config once at startup
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'business_logic.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    FULL_CONFIG = json.load(f)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "mpm-pipeline"})

@app.route('/run_pipeline', methods=['POST'])
def api_run_pipeline():
    """
    Run pipeline for a brand.
    
    Request body:
    {
        "brand": "Bushido"  // or "Iiyama" or "Koszulkowy"
    }
    """
    data = request.get_json() or {}
    brand = data.get('brand', 'Bushido')
    
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Input')
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Output')
    
    try:
        result_df = run_pipeline(brand, input_dir, output_dir, FULL_CONFIG)
        
        if result_df is not None:
            # Return summary stats
            summary = {
                "brand": brand,
                "status": "success",
                "total_products": len(result_df),
                "priority_breakdown": result_df['priority'].value_counts().to_dict(),
                "ga4_class_breakdown": result_df['ga4_class'].value_counts().to_dict(),
                "output_file": f"Output/{brand}/Landing_Page_Final.csv"
            }
            return jsonify(summary)
        else:
            return jsonify({"status": "error", "message": "Pipeline returned None"}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test_join', methods=['POST'])
def api_test_join():
    """
    Test GA4 + Feed join for a brand.
    
    Request body:
    {
        "brand": "Bushido"
    }
    """
    data = request.get_json() or {}
    brand = data.get('brand', 'Bushido')
    
    # Import test function
    from test_n8n_join import test_join
    
    try:
        result = test_join(brand)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("Starting MPM Pipeline API Server...")
    print("Endpoints:")
    print("  GET  /health          - Health check")
    print("  POST /run_pipeline    - Run full pipeline")
    print("  POST /test_join       - Test GA4+Feed join")
    app.run(host='0.0.0.0', port=5000, debug=True)
