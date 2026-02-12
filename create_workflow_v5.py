"""
Surgical V5 Edit: Replaces Merger+Classifier with Python Bridge + HTTP Request.
Reads working V4 JSON, applies minimal changes, saves as V5, optionally pushes.
Follows N8N Architect Rule: READ → MAP → PRESERVE IDs → SURGICAL EDIT.
"""
import json
import uuid
import copy


def create_v5():
    # 1. READ the working V4
    with open("Workflows/MSC_ALGO_v4_Pipeline.json", "r", encoding="utf-8") as f:
        v4 = json.load(f)
    
    v5 = copy.deepcopy(v4)
    v5["name"] = "MSC_ALGO_v5_Hybrid"
    
    # 2. MAP existing nodes
    node_map = {n["name"]: i for i, n in enumerate(v5["nodes"])}
    print(f"Mapped {len(node_map)} nodes")
    
    # 3. SURGICAL EDIT — Replace Merger Node code
    merger_idx = node_map["Merger Node"]
    v5["nodes"][merger_idx]["name"] = "Python Bridge"
    v5["nodes"][merger_idx]["notes"] = "Consolidates all 4 streams + config for Python API."
    v5["nodes"][merger_idx]["parameters"]["jsCode"] = """// ============================================================
// PYTHON BRIDGE — Consolidate all data for external Python API
// ============================================================

const safeGet = (nodeName) => {
  try { return $(nodeName).all().map(i => i.json); }
  catch (e) { return []; }
};

const feed = safeGet('Normalize Feed + Margins');
const meta = safeGet('Normalize Meta Ads');
const items = safeGet('Normalize GA4 Items');
const lp = safeGet('Normalize GA4 LP');

let config = {};
try { config = $('Margin Resolver').first().json; } catch(e) {}

// Return consolidated payload as single item
return [{ json: {
  feed: feed,
  meta_ads: meta,
  ga4_items: items,
  ga4_lp: lp,
  config: {
    brand: config.BRAND || '',
    vat_rate: config.VAT_RATE || 0.23,
    default_margin: config.DEFAULT_MARGIN || 0.10,
    margin_rules: config.MARGIN_RULES || []
  }
} }];"""
    
    # 4. SURGICAL EDIT — Replace MSC-ALGO Classifier with HTTP Request
    classifier_idx = node_map["MSC-ALGO Classifier"]
    v5["nodes"][classifier_idx] = {
        "parameters": {
            "method": "POST",
            "url": "={{ $getWorkflowStaticData('global').api_url || 'https://msc-algo-api.onrender.com' }}/process",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify($json) }}",
            "options": {
                "timeout": 120000
            }
        },
        "id": v5["nodes"][classifier_idx]["id"],  # PRESERVE ID
        "name": "Python Brain (API)",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": v5["nodes"][classifier_idx]["position"],  # PRESERVE position
        "notes": "Calls external Python API. 120s timeout for cold starts on free tier."
    }
    
    # 5. ADD Parse Response node (HTTP Request returns the JSON directly, 
    #    but we need to ensure items are properly formatted)
    # HTTP Request node with JSON response auto-parses into items.
    # If the API returns an array, n8n auto-creates one item per array element.
    # So we may NOT need a parse node at all if the response is clean.
    # But let's add a safety wrapper just in case.
    
    parse_node = {
        "parameters": {
            "jsCode": """// ============================================================
// PARSE API RESPONSE
// Ensures Python API response is properly formatted for Sheets
// ============================================================
const items = $input.all().map(i => i.json);

// Handle case where response is nested in 'data' or similar
if (items.length === 1 && Array.isArray(items[0])) {
  return items[0].map(item => ({ json: item }));
}

// Already properly formatted
return items.map(item => ({ json: item }));"""
        },
        "id": str(uuid.uuid4()),
        "name": "Parse API Response",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [
            v5["nodes"][classifier_idx]["position"][0] + 250,
            v5["nodes"][classifier_idx]["position"][1]
        ],
        "notes": "Safety wrapper for API response formatting."
    }
    v5["nodes"].append(parse_node)
    
    # Move Output to Google Sheets position to accommodate new node
    output_idx = node_map["Output to Google Sheets"]
    v5["nodes"][output_idx]["position"] = [
        parse_node["position"][0] + 250,
        parse_node["position"][1]
    ]
    
    # 6. FIX CONNECTIONS
    conns = v5["connections"]
    
    # Rename connection sources (Merger Node → Python Bridge)
    if "Merger Node" in conns:
        conns["Python Bridge"] = conns.pop("Merger Node")
    
    # Update Normalize → Python Bridge connections  
    for norm_name in ["Normalize Feed + Margins", "Normalize GA4 Items", 
                       "Normalize GA4 LP", "Normalize Meta Ads"]:
        if norm_name in conns:
            for output in conns[norm_name]["main"]:
                for conn in output:
                    if conn["node"] == "Merger Node":
                        conn["node"] = "Python Bridge"
    
    # Python Bridge → Python Brain (API)
    conns["Python Bridge"] = {
        "main": [[{"node": "Python Brain (API)", "type": "main", "index": 0}]]
    }
    
    # Python Brain (API) → Parse API Response
    # Remove old MSC-ALGO Classifier connection
    if "MSC-ALGO Classifier" in conns:
        del conns["MSC-ALGO Classifier"]
    
    conns["Python Brain (API)"] = {
        "main": [[{"node": "Parse API Response", "type": "main", "index": 0}]]
    }
    
    # Parse API Response → Output to Google Sheets
    conns["Parse API Response"] = {
        "main": [[{"node": "Output to Google Sheets", "type": "main", "index": 0}]]
    }
    
    # 7. SAVE
    out_path = "Workflows/MSC_ALGO_v5_Hybrid.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(v5, f, indent=4, ensure_ascii=False)
    
    print(f"\nSaved: {out_path}")
    print(f"Nodes: {[n['name'] for n in v5['nodes']]}")
    print(f"Connections: {list(conns.keys())}")
    

if __name__ == "__main__":
    create_v5()
