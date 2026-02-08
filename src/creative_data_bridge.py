#!/usr/bin/env python3
"""
Creative Data Bridge - ETL Pipeline
Transforms transactional data into creative fuel by enriching with VOC insights.

Usage: python src/creative_data_bridge.py [brand]
"""

import os
import re
import json
import pandas as pd
from pathlib import Path

# === CONFIGURATION ===

# Tech Translator: Technical specs -> Consumer benefits
TECH_MAP = {
    r'\b165\s*Hz\b': 'Płynność',
    r'\b144\s*Hz\b': 'Płynność',
    r'\b100\s*Hz\b': 'Płynność',
    r'\b240\s*Hz\b': 'Ultra płynność',
    r'\b4K\b': 'Ostrość detali',
    r'\bUHD\b': 'Ostrość detali',
    r'\bWQHD\b': 'Wysoka rozdzielczość',
    r'\b1440p\b': 'Wysoka rozdzielczość',
    r'\bIPS\b': 'Szerokie kąty widzenia',
    r'\bVA\b': 'Głęboka czerń',
    r'\bOLED\b': 'Perfekcyjna czerń',
    r'\bUSB-C\b': 'Jeden kabel',
    r'\bKVM\b': 'Przełączanie PC',
    r'\b1000R\b': 'Immersja',
    r'\b1500R\b': 'Immersja',
    r'\bFlicker-Free\b': 'Ochrona oczu',
    r'\bHDR\b': 'Dynamiczny obraz',
    r'\bG-Sync|FreeSync\b': 'Bez rwania',
    r'\bPivot\b': 'Tryb portretowy',
    r'\bDaisy Chain\b': 'Łączenie monitorów',
    r'\b24/7\b': 'Ciągła praca',
    r'\bVESA\b': 'Montaż na ścianie',
}

# Visual Archetypes by vertical
VISUAL_MAP = {
    'v_gaming': 'Cyberpunk | RGB Aesthetic | Immersive Gaming | Dark Room',
    'v_office': 'Minimal | Clean Desk | Professional | Bright Office',
    'v_prographics': 'Studio | Color Accurate | Creative Workflow | Neutral',
    'v_digital_signage': 'Commercial | Bold Typography | Corporate | High Visibility',
}

# Persona mapping by vertical
PERSONA_MAP = {
    'v_gaming': 'Gracz Kompetytywny | Gracz Casualowy | Streamer | Sim Racer',
    'v_office': 'IT Admin | Remote Worker | Menedżer | Księgowa',
    'v_prographics': 'Grafik | Fotograf | Video Editor | Architekt',
    'v_digital_signage': 'Marketing Manager | AV Integrator | Szkoła | Retail',
}


def load_harvest_data(input_dir: str, brand: str) -> dict:
    """Load all RAW_HARVEST_DATA_*.json files into a dictionary."""
    harvest = {}
    brand_dir = os.path.join(input_dir, brand)
    
    for f in Path(brand_dir).glob('RAW_HARVEST_DATA_*.json'):
        vertical_name = f.stem.replace('RAW_HARVEST_DATA_', '')
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
            harvest[vertical_name] = data
    
    return harvest


def extract_insights_by_basket(harvest_data: dict, basket_type: str, max_items: int = 10) -> list:
    """Extract insights of a specific basket type (PAIN, DREAM, TRUST, etc.)."""
    insights = []
    
    if 'deep_harvest_insights' not in harvest_data:
        return insights
    
    for phase_name, phase_insights in harvest_data['deep_harvest_insights'].items():
        for insight in phase_insights:
            if insight.get('basket') == basket_type:
                raw_quote = insight.get('raw_quote', '')
                if raw_quote and len(raw_quote) > 10:
                    # Truncate long quotes
                    if len(raw_quote) > 80:
                        raw_quote = raw_quote[:77] + '...'
                    insights.append(raw_quote)
    
    return insights[:max_items]


def extract_slang(harvest_data: dict) -> list:
    """Extract tribal slang from harvest data."""
    slang = set()
    
    # From individual insights
    if 'deep_harvest_insights' in harvest_data:
        for phase_name, phase_insights in harvest_data['deep_harvest_insights'].items():
            for insight in phase_insights:
                for s in insight.get('slang_detected', []):
                    if s and len(s) > 2:
                        slang.add(s)
    
    # From tribal_language_dictionary
    if 'tribal_language_dictionary' in harvest_data:
        tld = harvest_data['tribal_language_dictionary']
        
        # Polish slang
        if 'polish_slang' in tld:
            for category, terms in tld['polish_slang'].items():
                if isinstance(terms, list):
                    slang.update(terms)
        
        # Technical terms (sample 10)
        if 'technical_terms' in tld:
            for category, terms in tld['technical_terms'].items():
                if isinstance(terms, list):
                    slang.update(terms[:5])
    
    return list(slang)[:15]


def extract_competitors(harvest_data: dict) -> list:
    """Extract competitor references."""
    competitors = set()
    
    if 'key_findings' in harvest_data:
        kf = harvest_data['key_findings']
        if 'competitor_context' in kf:
            for comp_name in kf['competitor_context'].keys():
                competitors.add(comp_name)
    
    if 'competitor_context' in harvest_data:
        for comp_name in harvest_data['competitor_context'].keys():
            competitors.add(comp_name)
    
    return list(competitors)


def match_product_to_vertical(row, harvest_dict: dict) -> str:
    """Determine which vertical a product belongs to using product code patterns."""
    title = str(row.get('feed_title', '')).lower()
    category = str(row.get('feed_category', '')).lower()
    
    # Priority 1: Product code pattern matching (most reliable)
    # Gaming: GB*, G-Master, G24*, G27*, G32* (Red Eagle / Gold Phoenix series)
    if re.search(r'\bgb[0-9]', title) or re.search(r'\bg[0-9]{2,4}', title) or 'g-master' in title:
        return 'gaming'
    
    # Signage: LH* (commercial), TE* (interactive)
    if re.search(r'\blh[0-9]', title) or re.search(r'\bte[0-9]', title):
        return 'signage'
    
    # ProGraphics: XUB with 4K/UHD or specific color models
    if ('4k' in title or 'uhd' in title) and 'xub' in title:
        return 'prographics'
    
    # Office: XU*, XB* (ProLite business series)
    if re.search(r'\bxu[0-9b]', title) or re.search(r'\bxb[0-9]', title) or 'prolite' in title:
        return 'office'
    
    # Priority 2: Category-based fallback
    if 'gaming' in category or 'game' in category:
        return 'gaming'
    elif 'signage' in category or 'commercial' in category:
        return 'signage'
    
    # Default to office for monitors
    return 'office'


def apply_tech_translator(text: str) -> list:
    """Convert technical specs to consumer benefits."""
    benefits = []
    
    for pattern, benefit in TECH_MAP.items():
        if re.search(pattern, text, re.IGNORECASE):
            if benefit not in benefits:
                benefits.append(benefit)
    
    return benefits


def sanitize_for_csv(items: list) -> str:
    """Convert list to pipe-separated string, sanitizing special characters."""
    if not items:
        return "General"
    
    clean_items = []
    for item in items:
        if item and isinstance(item, str):
            # Remove problematic characters
            clean = item.replace('|', '-').replace('\n', ' ').replace('\r', ' ')
            clean = ' '.join(clean.split())  # Normalize whitespace
            clean_items.append(clean)
    
    return ' | '.join(clean_items[:10]) if clean_items else "General"


def run_creative_bridge(brand: str, input_dir: str = 'Input', output_dir: str = 'Output'):
    """Main ETL function."""
    print(f"\n>>> Creative Data Bridge for: {brand}")
    
    # 1. Load source CSV
    csv_path = os.path.join(output_dir, brand, f"{brand}_Growth_Opportunities.csv")
    if not os.path.exists(csv_path):
        print(f"[ERROR] Source CSV not found: {csv_path}")
        return None
    
    df = pd.read_csv(csv_path)
    print(f"[CSV] Loaded {len(df)} rows from {csv_path}")
    
    # 2. Load Harvest JSONs
    harvest = load_harvest_data(input_dir, brand)
    print(f"[JSON] Loaded {len(harvest)} harvest files: {list(harvest.keys())}")
    
    if not harvest:
        print("[WARNING] No harvest data found. Using fallback values.")
    
    # 3. Create synthetic description if missing
    if 'feed_description' not in df.columns:
        df['feed_description'] = df['feed_title'].fillna('') + ' - ' + df['feed_category'].fillna('')
    
    # 4. Enrich each row
    def enrich_row(row):
        # Determine vertical
        vertical = match_product_to_vertical(row, harvest)
        vertical_key = f'v_{vertical}' if not vertical.startswith('v_') else vertical
        
        # Get harvest data for this vertical
        harvest_data = harvest.get(vertical, harvest.get(list(harvest.keys())[0], {})) if harvest else {}
        
        # Marketing Personas
        personas = PERSONA_MAP.get(vertical_key, 'General Consumer')
        
        # Pain Points Pool
        pains = extract_insights_by_basket(harvest_data, 'PAIN')
        
        # Desire Outcomes Pool
        dreams = extract_insights_by_basket(harvest_data, 'DREAM')
        
        # Tribal Slang
        slang = extract_slang(harvest_data)
        
        # Tech Translator
        text_to_scan = str(row.get('feed_title', '')) + ' ' + str(row.get('feed_description', ''))
        tech_benefits = apply_tech_translator(text_to_scan)
        
        # Visual Archetypes
        visuals = VISUAL_MAP.get(vertical_key, 'Professional | Clean')
        
        # Competitor Anchors
        competitors = extract_competitors(harvest_data)
        
        return pd.Series({
            'marketing_personas': personas,
            'pain_points_pool': sanitize_for_csv(pains),
            'desire_outcomes_pool': sanitize_for_csv(dreams),
            'tribal_slang': sanitize_for_csv(slang),
            'tech_translator': sanitize_for_csv(tech_benefits),
            'visual_archetypes': visuals,
            'competitor_anchors': sanitize_for_csv(competitors) if competitors else 'Samsung | Dell | LG',
        })
    
    # Apply enrichment
    print("[ETL] Enriching rows with creative data...")
    enriched = df.apply(enrich_row, axis=1)
    df = pd.concat([df, enriched], axis=1)
    
    # 5. Save output
    out_path = os.path.join(output_dir, brand, f"MASTER_CREATIVE_FEED_{brand}.csv")
    df.to_csv(out_path, index=False)
    print(f"[OUTPUT] Saved: {out_path}")
    
    return df


if __name__ == '__main__':
    import sys
    
    brand = sys.argv[1] if len(sys.argv) > 1 else 'Iiyama'
    run_creative_bridge(brand)
