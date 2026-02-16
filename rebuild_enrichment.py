"""
Rebuild Enrichment Pipeline v2 — HTTP Request based (n8n server has no AI community nodes).
Proper escaping via Python json.dumps.
"""
import json
import os

# ── CODE SNIPPETS ──

DISCOVER_BRANDS_CODE = """const fs = require('fs');
const path = require('path');

const projectRoot = process.env.PROJECT_ROOT || 'c:/Users/Paweł/Documents/GitHub/Money Printing Machine';
const outputDir = path.join(projectRoot, 'Output');

const brands = [];
const dirs = fs.readdirSync(outputDir, { withFileTypes: true });
for (const dir of dirs) {
  if (!dir.isDirectory()) continue;
  const brandName = dir.name;
  const csvPath = path.join(outputDir, brandName, brandName + '_Growth_Opportunities.csv');
  if (fs.existsSync(csvPath)) {
    brands.push({ json: { brand: brandName } });
  }
}

if (brands.length === 0) {
  throw new Error('No brands found. Run MSC-ALGO first.');
}

return brands;"""

EXTRACT_BRAND_CODE = """const body = $input.first().json.body || $input.first().json;
const brand = body.brand || body.Brand;

if (!brand) {
  throw new Error('Webhook must POST {brand: "Name"}');
}

return [{ json: { brand } }];"""

LOAD_CONFIG_CODE = """const fs = require('fs');
const path = require('path');

const brand = $input.first().json.brand;
if (!brand) throw new Error('No brand specified');

const projectRoot = process.env.PROJECT_ROOT || 'c:/Users/Paweł/Documents/GitHub/Money Printing Machine';
const csvPath = path.join(projectRoot, 'Output', brand, brand + '_Growth_Opportunities.csv');
const cacheDir = path.join(projectRoot, 'cache', 'enrichment', brand.toLowerCase());
const configPath = path.join(projectRoot, 'business_logic.json');

if (!fs.existsSync(csvPath)) {
  throw new Error('CSV not found: ' + csvPath);
}

let config = {};
try { config = JSON.parse(fs.readFileSync(configPath, 'utf-8')); } catch (e) {}

if (!fs.existsSync(cacheDir)) {
  fs.mkdirSync(cacheDir, { recursive: true });
}

return [{
  json: {
    brand,
    projectRoot,
    csvPath,
    cacheDir,
    config: config[brand] || config[brand.toLowerCase()] || {},
    timestamp: new Date().toISOString()
  }
}];"""

READ_CSV_CODE = """const fs = require('fs');
const config = $input.first().json;

const raw = fs.readFileSync(config.csvPath, 'utf-8');
const lines = raw.split('\\n').filter(l => l.trim());
const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));

const items = [];
for (let i = 1; i < lines.length; i++) {
  const values = [];
  let current = '';
  let inQuotes = false;
  for (const ch of lines[i]) {
    if (ch === '"') { inQuotes = !inQuotes; }
    else if (ch === ',' && !inQuotes) { values.push(current.trim()); current = ''; }
    else { current += ch; }
  }
  values.push(current.trim());

  const row = {};
  headers.forEach((h, idx) => { row[h] = values[idx] || ''; });
  row._brand = config.brand;
  row._projectRoot = config.projectRoot;
  row._cacheDir = config.cacheDir;
  items.push({ json: row });
}

return items;"""

CACHE_CHECK_CODE = """const fs = require('fs');
const crypto = require('crypto');

const items = $input.all();
const results = [];

for (const item of items) {
  const d = item.json;
  const raw = (d.feed_id || '') + '|' + (parseFloat(d.feed_price_numeric) || 0).toFixed(2) + '|' + (d.feed_category || '');
  const key = crypto.createHash('sha256').update(raw).digest('hex').substring(0, 16);
  const cachePath = d._cacheDir + '/' + key + '.json';

  let cacheHit = false;
  let cachedData = null;

  try {
    if (fs.existsSync(cachePath)) {
      const entry = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));
      const age = (Date.now() - new Date(entry.harvest_date).getTime()) / (1000 * 60 * 60 * 24);
      if (age < 7) { cacheHit = true; cachedData = entry.data; }
    }
  } catch (e) {}

  results.push({
    json: { ...d, _cacheKey: key, _cachePath: cachePath, _cacheHit: cacheHit, ...(cachedData || {}) }
  });
}

return results;"""

COLLECT_CACHED_CODE = """const items = $input.all();
return items.map(item => ({ json: { ...item.json, _source: 'cache' } }));"""

EXTRACT_HARVEST_CODE = """const items = $input.all();
const results = [];

for (const item of items) {
  const d = item.json;
  
  // Extract text from Perplexity response
  let reviews = '';
  let category = '';
  
  if (d._reviews_response) {
    try {
      const r = typeof d._reviews_response === 'string' ? JSON.parse(d._reviews_response) : d._reviews_response;
      reviews = r.choices?.[0]?.message?.content || '';
    } catch (e) { reviews = String(d._reviews_response); }
  }
  
  if (d._category_response) {
    try {
      const c = typeof d._category_response === 'string' ? JSON.parse(d._category_response) : d._category_response;
      category = c.choices?.[0]?.message?.content || '';
    } catch (e) { category = String(d._category_response); }
  }
  
  results.push({
    json: {
      ...d,
      _product_reviews: reviews.substring(0, 2000),
      _category_insights: category.substring(0, 2000)
    }
  });
}

return results;"""

PREPARE_CLAUDE_CODE = """const items = $input.all();
const results = [];

for (const item of items) {
  const d = item.json;
  const prompt = 'ACT AS Consumer Psychologist. Create psychographic profile for: ' + (d.feed_title || '') + ' (Category: ' + (d.feed_category || '') + ').\\n\\nREVIEWS:\\n' + (d._product_reviews || 'No data') + '\\n\\nCATEGORY INSIGHTS:\\n' + (d._category_insights || 'No data') + '\\n\\nReturn ONLY valid JSON with these 9 keys:\\n{"persona_name":"One-word persona label","persona_dream":"#1 dream outcome","persona_fear":"#1 fear/pain","persona_awareness":"unaware|problem_aware|solution_aware|product_aware","tech_translator":"Feature->Benefit pairs","social_proof_quote":"2-3 strongest quotes","competitive_edge":"What makes this product better","visual_hook_suggestion":"For Meta Ad: what to zoom/highlight","buying_objections":"Top 2-3 hesitations"}\\nPolish language. Emotional, copywriter-ready. NO HALLUCINATIONS.';
  
  results.push({
    json: {
      ...d,
      _claude_messages: JSON.stringify([{ role: 'user', content: prompt }])
    }
  });
}

return results;"""

PARSE_ANALYSIS_CODE = """const items = $input.all();
const results = [];

for (const item of items) {
  const d = item.json;
  
  let text = '';
  try {
    const resp = typeof d._claude_response === 'string' ? JSON.parse(d._claude_response) : d._claude_response;
    text = resp?.content?.[0]?.text || '';
  } catch (e) { text = String(d._claude_response || ''); }
  
  let analysis = {};
  try {
    text = text.replace(/```json/g, '').replace(/```/g, '').trim();
    analysis = JSON.parse(text);
  } catch (e) {
    try {
      const s = text.indexOf('{');
      const e2 = text.lastIndexOf('}');
      if (s !== -1 && e2 > s) analysis = JSON.parse(text.substring(s, e2 + 1));
    } catch (e3) {}
  }

  results.push({
    json: {
      ...d,
      persona_name: analysis.persona_name || '',
      persona_dream: analysis.persona_dream || '',
      persona_fear: analysis.persona_fear || '',
      persona_awareness: analysis.persona_awareness || '',
      tech_translator: analysis.tech_translator || '',
      social_proof_quote: analysis.social_proof_quote || '',
      competitive_edge: analysis.competitive_edge || '',
      visual_hook_suggestion: analysis.visual_hook_suggestion || '',
      buying_objections: analysis.buying_objections || '',
      harvest_date: new Date().toISOString().split('T')[0],
      _source: 'fresh'
    }
  });
}

return results;"""

UPDATE_CACHE_CODE = """const fs = require('fs');
const items = $input.all();

for (const item of items) {
  const d = item.json;
  if (d._cacheHit) continue;
  
  const entry = {
    product_id: d.feed_id,
    harvest_date: new Date().toISOString(),
    data: {
      persona_name: d.persona_name || '',
      persona_dream: d.persona_dream || '',
      persona_fear: d.persona_fear || '',
      persona_awareness: d.persona_awareness || '',
      tech_translator: d.tech_translator || '',
      social_proof_quote: d.social_proof_quote || '',
      competitive_edge: d.competitive_edge || '',
      visual_hook_suggestion: d.visual_hook_suggestion || '',
      buying_objections: d.buying_objections || '',
      harvest_date: d.harvest_date || ''
    }
  };
  
  try { fs.writeFileSync(d._cachePath, JSON.stringify(entry, null, 2), 'utf-8'); } catch (e) {}
}

return items;"""

WRITE_CSV_CODE = """const fs = require('fs');
const path = require('path');

const items = $input.all();
if (items.length === 0) return [{ json: { status: 'no_items' } }];

const skip = ['_brand','_projectRoot','_cacheDir','_cacheKey','_cachePath','_cacheHit','_source','_product_reviews','_category_insights','_reviews_response','_category_response','_claude_messages','_claude_response','_quality_ok','_quality_filled'];
const keys = Object.keys(items[0].json).filter(k => !skip.includes(k));

const header = keys.join(',');
const rows = items.map(item =>
  keys.map(k => '"' + String(item.json[k] || '').replace(/"/g, '""') + '"').join(',')
);

const csv = [header, ...rows].join('\\n');
const brand = items[0].json._brand || 'Unknown';
const root = items[0].json._projectRoot || '.';
const outPath = path.join(root, 'Output', brand, brand + '_Enriched_Products.csv');
fs.writeFileSync(outPath, csv, 'utf-8');

return [{ json: { status: 'success', outputPath: outPath, total: items.length, columns: keys.length } }];"""

ERROR_LOG_CODE = """const error = $input.first().json;
return [{
  json: {
    status: 'error',
    workflow: error.workflow?.name || 'Enrichment Pipeline',
    node: error.execution?.error?.node?.name || 'unknown',
    message: error.execution?.error?.message || 'Unknown error',
    timestamp: new Date().toISOString()
  }
}];"""

# ── PERPLEXITY CALL CODE (HTTP Request approach) ──
PERPLEXITY_REVIEWS_CODE = """const items = $input.all();
const results = [];

for (const item of items) {
  const d = item.json;
  const query = 'Znajdz opinie i recenzje uzytkow o produkcie: ' + (d.feed_title || '') + '. Szukam pozytywnych cytatow i doswiadczen.';
  
  results.push({
    json: {
      ...d,
      _perplexity_body_reviews: JSON.stringify({
        model: 'sonar',
        messages: [{ role: 'user', content: query }]
      })
    }
  });
}

return results;"""

PERPLEXITY_CATEGORY_CODE = """const items = $input.all();
const results = [];

for (const item of items) {
  const d = item.json;
  const query = 'Kategoria: ' + (d.feed_category || '') + '. Czego ludzie szukaja kupujac takie produkty? Jakie maja obawy? Co ich zaskakuje?';
  
  results.push({
    json: {
      ...d,
      _perplexity_body_category: JSON.stringify({
        model: 'sonar',
        messages: [{ role: 'user', content: query }]
      })
    }
  });
}

return results;"""


# ── BUILD WORKFLOW ──
workflow = {
    "name": "Enrichment Pipeline (Process 3)",
    "nodes": [
        # TRIGGERS
        {
            "id": "enrich-trigger", "name": "Manual Trigger",
            "type": "n8n-nodes-base.manualTrigger", "typeVersion": 1,
            "position": [250, 200],
            "notes": "Manual run: scans Output/ for all brands"
        },
        {
            "id": "enrich-webhook", "name": "MSC-ALGO Trigger",
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [250, 450],
            "webhookId": "enrichment-trigger",
            "parameters": {
                "path": "enrichment-trigger",
                "httpMethod": "POST",
                "responseMode": "onReceived",
                "options": {}
            },
            "notes": "POST {brand:'X'} from MSC-ALGO"
        },
        {
            "id": "enrich-extract-brand", "name": "Extract Brand from Webhook",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [450, 450],
            "parameters": {"jsCode": EXTRACT_BRAND_CODE}
        },
        # PHASE 1
        {
            "id": "enrich-discover", "name": "Discover Brands",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [450, 200],
            "parameters": {"jsCode": DISCOVER_BRANDS_CODE}
        },
        {
            "id": "enrich-config", "name": "Load Config",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [650, 300],
            "parameters": {"jsCode": LOAD_CONFIG_CODE}
        },
        {
            "id": "enrich-read-csv", "name": "Read Growth CSV",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [850, 300],
            "parameters": {"jsCode": READ_CSV_CODE}
        },
        {
            "id": "enrich-filter", "name": "Filter Actionable",
            "type": "n8n-nodes-base.if", "typeVersion": 2,
            "position": [1050, 300],
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": False, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "f1",
                        "leftValue": "={{ $json.calc_is_actionable }}",
                        "rightValue": "True",
                        "operator": {"type": "string", "operation": "equals"}
                    }],
                    "combinator": "and"
                }
            }
        },
        {
            "id": "enrich-batch", "name": "Split In Batches",
            "type": "n8n-nodes-base.splitInBatches", "typeVersion": 3,
            "position": [1250, 200],
            "parameters": {"batchSize": 5, "options": {}}
        },
        {
            "id": "enrich-cache-check", "name": "Check Cache",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [1450, 200],
            "parameters": {"jsCode": CACHE_CHECK_CODE}
        },
        {
            "id": "enrich-cache-router", "name": "Cache Router",
            "type": "n8n-nodes-base.if", "typeVersion": 2,
            "position": [1650, 200],
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "c1",
                        "leftValue": "={{ $json._cacheHit }}",
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true"}
                    }],
                    "combinator": "and"
                }
            }
        },
        {
            "id": "enrich-collect-cached", "name": "Collect Cached",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [1850, 100],
            "parameters": {"jsCode": COLLECT_CACHED_CODE}
        },
        # PHASE 2: Perplexity via HTTP Request
        {
            "id": "enrich-prep-reviews", "name": "Prep Perplexity Reviews",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [1850, 300],
            "parameters": {"jsCode": PERPLEXITY_REVIEWS_CODE}
        },
        {
            "id": "enrich-call-reviews", "name": "Call Perplexity: Reviews",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [2050, 300],
            "parameters": {
                "method": "POST",
                "url": "https://api.perplexity.ai/chat/completions",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Authorization", "value": "=Bearer {{ $env.PERPLEXITY_API_KEY }}"},
                        {"name": "Content-Type", "value": "application/json"}
                    ]
                },
                "sendBody": True,
                "specifyBody": "string",
                "body": "={{ $json._perplexity_body_reviews }}",
                "options": {"timeout": 30000}
            },
            "notes": "Phase 2: Perplexity API for product reviews"
        },
        {
            "id": "enrich-prep-category", "name": "Prep Perplexity Category",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [1850, 500],
            "parameters": {"jsCode": PERPLEXITY_CATEGORY_CODE}
        },
        {
            "id": "enrich-call-category", "name": "Call Perplexity: Category",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [2050, 500],
            "parameters": {
                "method": "POST",
                "url": "https://api.perplexity.ai/chat/completions",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "Authorization", "value": "=Bearer {{ $env.PERPLEXITY_API_KEY }}"},
                        {"name": "Content-Type", "value": "application/json"}
                    ]
                },
                "sendBody": True,
                "specifyBody": "string",
                "body": "={{ $json._perplexity_body_category }}",
                "options": {"timeout": 30000}
            },
            "notes": "Phase 2: Perplexity API for category insights"
        },
        # PHASE 2: Extract + Merge
        {
            "id": "enrich-extract-harvest", "name": "Extract Harvest Data",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [2250, 400],
            "parameters": {"jsCode": EXTRACT_HARVEST_CODE}
        },
        # PHASE 3: Claude
        {
            "id": "enrich-prep-claude", "name": "Prepare Claude Prompt",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [2450, 400],
            "parameters": {"jsCode": PREPARE_CLAUDE_CODE}
        },
        {
            "id": "enrich-call-claude", "name": "Claude: Analyze",
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [2650, 400],
            "parameters": {
                "method": "POST",
                "url": "https://api.anthropic.com/v1/messages",
                "sendHeaders": True,
                "headerParameters": {
                    "parameters": [
                        {"name": "x-api-key", "value": "={{ $env.ANTHROPIC_API_KEY }}"},
                        {"name": "anthropic-version", "value": "2023-06-01"},
                        {"name": "Content-Type", "value": "application/json"}
                    ]
                },
                "sendBody": True,
                "specifyBody": "string",
                "body": "={{ JSON.stringify({ model: 'claude-sonnet-4-5-20250514', max_tokens: 2048, messages: JSON.parse($json._claude_messages) }) }}",
                "options": {"timeout": 60000}
            },
            "notes": "Phase 3: Claude Sonnet analyzes harvested insights"
        },
        {
            "id": "enrich-parse", "name": "Parse Analysis",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [2850, 400],
            "parameters": {"jsCode": PARSE_ANALYSIS_CODE}
        },
        {
            "id": "enrich-update-cache", "name": "Update Cache",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [3050, 400],
            "parameters": {"jsCode": UPDATE_CACHE_CODE}
        },
        # PHASE 4: Output
        {
            "id": "enrich-merge-all", "name": "Merge All Results",
            "type": "n8n-nodes-base.merge", "typeVersion": 3,
            "position": [3250, 250],
            "parameters": {"mode": "append"}
        },
        {
            "id": "enrich-write-csv", "name": "Write Enriched CSV",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [3450, 250],
            "parameters": {"jsCode": WRITE_CSV_CODE}
        },
        # ERROR HANDLING
        {
            "id": "enrich-error-trigger", "name": "Error Trigger",
            "type": "n8n-nodes-base.errorTrigger", "typeVersion": 1,
            "position": [250, 650],
            "notes": "Only fires on real errors (shows example data when manually tested — this is normal n8n behavior)"
        },
        {
            "id": "enrich-error-log", "name": "Log Error",
            "type": "n8n-nodes-base.code", "typeVersion": 2,
            "position": [450, 650],
            "parameters": {"jsCode": ERROR_LOG_CODE}
        }
    ],
    "connections": {
        "Manual Trigger": {"main": [[{"node": "Discover Brands", "type": "main", "index": 0}]]},
        "MSC-ALGO Trigger": {"main": [[{"node": "Extract Brand from Webhook", "type": "main", "index": 0}]]},
        "Extract Brand from Webhook": {"main": [[{"node": "Load Config", "type": "main", "index": 0}]]},
        "Discover Brands": {"main": [[{"node": "Load Config", "type": "main", "index": 0}]]},
        "Load Config": {"main": [[{"node": "Read Growth CSV", "type": "main", "index": 0}]]},
        "Read Growth CSV": {"main": [[{"node": "Filter Actionable", "type": "main", "index": 0}]]},
        "Filter Actionable": {"main": [[{"node": "Split In Batches", "type": "main", "index": 0}], []]},
        "Split In Batches": {"main": [[{"node": "Check Cache", "type": "main", "index": 0}]]},
        "Check Cache": {"main": [[{"node": "Cache Router", "type": "main", "index": 0}]]},
        "Cache Router": {
            "main": [
                [{"node": "Collect Cached", "type": "main", "index": 0}],
                [
                    {"node": "Prep Perplexity Reviews", "type": "main", "index": 0},
                    {"node": "Prep Perplexity Category", "type": "main", "index": 0}
                ]
            ]
        },
        "Collect Cached": {"main": [[{"node": "Merge All Results", "type": "main", "index": 1}]]},
        "Prep Perplexity Reviews": {"main": [[{"node": "Call Perplexity: Reviews", "type": "main", "index": 0}]]},
        "Call Perplexity: Reviews": {"main": [[{"node": "Extract Harvest Data", "type": "main", "index": 0}]]},
        "Prep Perplexity Category": {"main": [[{"node": "Call Perplexity: Category", "type": "main", "index": 0}]]},
        "Call Perplexity: Category": {"main": [[{"node": "Extract Harvest Data", "type": "main", "index": 0}]]},
        "Extract Harvest Data": {"main": [[{"node": "Prepare Claude Prompt", "type": "main", "index": 0}]]},
        "Prepare Claude Prompt": {"main": [[{"node": "Claude: Analyze", "type": "main", "index": 0}]]},
        "Claude: Analyze": {"main": [[{"node": "Parse Analysis", "type": "main", "index": 0}]]},
        "Parse Analysis": {"main": [[{"node": "Update Cache", "type": "main", "index": 0}]]},
        "Update Cache": {"main": [[{"node": "Merge All Results", "type": "main", "index": 0}]]},
        "Merge All Results": {"main": [[{"node": "Write Enriched CSV", "type": "main", "index": 0}]]},
        "Error Trigger": {"main": [[{"node": "Log Error", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"}
}

# SAVE
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Workflows", "Enrichment_Pipeline.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(workflow, f, indent=4, ensure_ascii=False)

print(f"Rebuilt: {len(workflow['nodes'])} nodes, {len(workflow['connections'])} connections")

# Verify
for n in workflow['nodes']:
    code = n.get('parameters', {}).get('jsCode', '')
    if '\\\\n' in json.dumps(code):
        # This checks the JSON representation
        pass  # json.dumps correctly escapes \n to \\n in JSON
    if code and '\n' not in code and len(code) > 50:
        print(f"WARNING: Missing newlines in {n['name']}")

print("All node types: " + str(sorted(set(n['type'] for n in workflow['nodes']))))
