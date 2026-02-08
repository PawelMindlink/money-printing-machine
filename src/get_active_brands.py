import json
import os
import sys

def get_brands():
    """Returns JSON array of brands from business_logic.json for n8n"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'business_logic.json')
    
    if not os.path.exists(config_path):
        # Fallback/Error
        print(json.dumps([]))
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        brands = []
        for client in data.get('clients', []):
            brands.append({"brand": client['name']})
            
        # N8N expects a JSON array of objects
        print(json.dumps(brands))
    except Exception as e:
        # Return empty on error to not break n8n hard? Or print error?
        # N8N reads stdout
        print(json.dumps([]))

if __name__ == "__main__":
    get_brands()
