"""
Add 'Trigger Enrichment' node to MSC-ALGO workflow.
Links MSC-ALGO output → Enrichment Pipeline webhook.
"""
import json

# Load MSC-ALGO
with open(r'Workflows/MSC_ALGO_v5_Hybrid.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

# Check if already added
existing = [n for n in wf['nodes'] if n['name'] == 'Trigger Enrichment']
if existing:
    print('Trigger Enrichment already exists, skipping.')
else:
    # Add Trigger Enrichment node
    new_node = {
        'parameters': {
            'method': 'POST',
            'url': 'https://mindlink-n8n.ironcode.io/webhook/enrichment-trigger',
            'sendBody': True,
            'specifyBody': 'json',
            'jsonBody': '={{ JSON.stringify({ brand: $node["Parse Form"].json.brand }) }}',
            'options': { 'timeout': 10000 }
        },
        'id': 'trigger-enrichment',
        'name': 'Trigger Enrichment',
        'type': 'n8n-nodes-base.httpRequest',
        'typeVersion': 4.2,
        'position': [3600, 512],
        'notes': 'AUTO-CHAIN: Calls Enrichment Pipeline webhook with brand name after MSC-ALGO completes'
    }
    wf['nodes'].append(new_node)
    print(f'Added Trigger Enrichment node. Total nodes: {len(wf["nodes"])}')

# Add connection: Output to Google Sheets -> Trigger Enrichment
wf['connections']['Output to Google Sheets'] = {
    'main': [[{
        'node': 'Trigger Enrichment',
        'type': 'main',
        'index': 0
    }]]
}
print('Connection: Output to Google Sheets -> Trigger Enrichment')

with open(r'Workflows/MSC_ALGO_v5_Hybrid.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=4, ensure_ascii=False)

print('MSC-ALGO workflow updated and saved.')
