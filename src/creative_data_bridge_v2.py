#!/usr/bin/env python3
"""
Creative Data Bridge v2.0 - Enhanced ETL Pipeline
Merges: Transactional Data (CSV) + Market Voice (JSON) + Brand Constraints

Usage: python src/creative_data_bridge_v2.py [brand]
"""

import os
import re
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

# === CONFIGURATION ===

# Tech Translator: Feature -> "So What?" Deep Benefits
# NOT shallow translations - competitive advantages and life hacks
TECH_TRANSLATOR = {
    # Refresh Rate -> Competitive Advantage
    r'\b360\s*Hz\b': 'Widzisz wroga 5ms wcześniej niż on Ciebie (Pro League advantage)',
    r'\b240\s*Hz\b': 'Płynność, która daje nieucziwą przewagę w CS2 i Valorant',
    r'\b165\s*Hz\b': 'Widzisz wroga zanim on zobaczy Ciebie (Przewaga 165Hz)',
    r'\b144\s*Hz\b': 'Koniec ze smużeniem – każdy ruch widoczny jak w zwolnionym tempie',
    r'\b100\s*Hz\b': 'Koniec z bólem oczu przy scrollowaniu Excela przez 8 godzin',
    r'\b75\s*Hz\b': 'Płynniejsze od standardu – oczy Ci podziękują',
    
    # Resolution -> Productivity Reality
    r'\b4K\b': 'Każdy piksel widoczny – doskonałe do edycji zdjęć i CAD',
    r'\bUHD\b': 'Ostrość, która pozwala widzieć to, co inni tracą w kompresji',
    r'\bWQHD\b': 'Więcej miejsca na ekranie = mniej przełączania okien',
    r'\b1440p\b': 'Sweet spot między 1080p a 4K – GPU Ci podziękuje',
    r'\bUWQHD\b': 'Dwa okna obok siebie bez miniaturyzacji – multitasking na poważnie',
    r'\b5K\b': 'Rozdzielczość dla tych, którzy drukują billboardy',
    
    # Panel Type -> Usage Reality
    r'\bIPS\b': 'Kolory nie kłamią – idealne do druku i designu',
    r'\bVA\b': 'Czerń tak głęboka, że horrory straszą bardziej',
    r'\bOLED\b': 'Każdy piksel świeci sam – nieskończony kontrast bez backlight bleed',
    r'\bNano\s*IPS\b': 'DCI-P3 gamut dla tych, którzy widzą różnicę',
    r'\bFast\s*IPS\b': 'Szybkość TN, kolory IPS – koniec kompromisów dla graczy',
    
    # Connectivity -> Life Hacks
    r'\bUSB-C|USB C|Type-C\b': 'Jeden kabel: zasilanie + obraz + dane (Koniec kablagangi)',
    r'\bKVM\b': 'Steruj dwoma kompami jedną klawiaturą (Game Changer dla IT)',
    r'\bDaisy Chain\b': 'Jeden kabel z laptopa obsługuje 3 monitory (clean desk achieved)',
    r'\bThunderbolt\b': '40Gbps – zewnętrzna karta graficzna przez jeden port',
    r'\bRJ45|LAN|Ethernet\b': 'Kabel LAN wbudowany = latency niższe niż WiFi',
    
    # Gaming Features -> Competitive Edge
    r'\bG-Sync\b': 'Zero screen tearingu z kartami NVIDIA (Smooth jak masło)',
    r'\bFreeSync\b': 'Synchronizacja z AMD za darmo – bez premium tax',
    r'\bVRR\b': 'Obraz dostosowuje się do klatki – koniec z tearing i stuttering',
    r'\b1ms|0\.5ms\b': 'Input lag tak niski, że przegrywasz przez skill, nie sprzęt',
    r'\bMBR|ELMB\b': 'Redukcja smużenia – każdy pocisk widoczny nawet przy 180°',
    
    # Ergonomics -> Health & Comfort
    r'\bPivot\b': 'Tryb wertykalny idealny do kodowania i długich dokumentów',
    r'\bHeight\s*Adjust|HAS\b': 'Regulacja wysokości – kręgosłup Ci podziękuje za 10 lat',
    r'\bSwivel\b': 'Obrót, żeby pokazać komuś ekran bez ruszania biurka',
    r'\bTilt\b': 'Pochylenie pod twój kąt siedzenia – żadnych odbić',
    r'\bVESA\b': 'Montaż na ścianie = biurko wolne od nóżki',
    
    # Display Features -> Real Impact
    r'\bHDR\s*400\b': 'HDR podstawowy – lepsze niż SDR, ale nie oszukujmy się',
    r'\bHDR\s*600\b': 'HDR, który faktycznie robi różnicę w filmach',
    r'\bHDR\s*1000\b': 'HDR klasy kinowej – słońce w grze oślepia naprawdę',
    r'\bFlicker-Free|Flicker\\s*Free\b': 'Zero migotania = zero bólu głowy po 8h pracy',
    r'\bBlue\\s*Light|Low\\s*Blue\b': 'Filtr niebieskiego – zaśniesz szybciej po nocnej sesji',
    
    # Curvature -> Immersion
    r'\b1000R\b': 'Peripheral vision covered – nic nie umknie poza kadrem',
    r'\b1500R\b': 'Krzywizna dopasowana do oczu – mniej ruszania głową',
    r'\b1800R\b': 'Delikatna krzywizna dla tych, którzy nie lubią flat screens',
    
    # Size -> Practical Reality
    r'\b24[\s\"]?\s*(cale|inch)?\b': 'Kompaktowy 24" – cały ekran w polu widzenia bez ruszania głową',
    r'\b27[\s\"]?\s*(cale|inch)?\b': 'Sweet spot 27" – duży ale nie za duży',
    r'\b32[\s\"]?\s*(cale|inch)?\b': '32" to prawie jak mały TV na biurku – immersja max',
    r'\b34[\s\"]?\s*(cale|inch)?\b': 'Ultrawide 34" zastępuje dwa monitory (i wygląda lepiej)',
    r'\b49[\s\"]?\s*(cale|inch)?\b': '49" = trzy monitory w jednym – dla maniaków produktywności',
    
    # Commercial -> Business Reality
    r'\b24/7\b': 'Stworzony do pracy non-stop (nie jak domowe monitory po roku)',
    r'\bAndroid\b': 'Wbudowany Android = nie potrzebujesz media playera za 500zł',
    r'\bEDLA\b': 'Certyfikacja Google – Play Store działa bez tricków',
}

# SKU Fallback Specs: Deep "So What?" benefits for priority products
# Used when regex-based TECH_TRANSLATOR returns empty
SKU_FALLBACK_SPECS = {
    # Gaming - G-Master series
    'GB2470HSU': [
        'Widzisz wroga zanim on zobaczy Ciebie (165Hz advantage)',
        'Input lag tak niski, że przegrywasz przez skill, nie sprzęt',
        'Synchronizacja z AMD za darmo – bez premium tax',
        'Kompaktowy 24" – cały ekran w polu widzenia'
    ],
    'GB2770HSU': [
        'Widzisz wroga zanim on zobaczy Ciebie',
        'Input lag poniżej percepcji ludzkiej',
        'Sweet spot 27" – duży ale nie za duży'
    ],
    'GB2770QSU': [
        'Więcej miejsca na ekranie = lepsza minimapa w CS2',
        'Szybkość TN, kolory IPS – koniec kompromisów',
        'Sweet spot 27" dla competitive gaming'
    ],
    'GB2790HSU': [
        'Płynność, która daje nieuczciwą przewagę w Valorant',
        'Input lag tak niski, że to prawie cheating',
        'Synchronizacja AMD za free'
    ],
    'G2470HSU': [
        'Widzisz wroga zanim on zobaczy Ciebie',
        'Input lag poniżej percepcji ludzkiej',
        'Kompaktowy 24" – pełne FoV bez ruszania głową'
    ],
    
    # Office - ProLite series
    'XUB2493HS': [
        'Kolory nie kłamią – idealne do druku i designu',
        'Zero migotania = zero bólu głowy po 8h pracy',
        'Kompaktowy 24" – cały ekran w polu widzenia'
    ],
    'XUB2792QSN': [
        'Więcej miejsca na ekranie = mniej przełączania okien',
        'Jeden kabel: zasilanie + obraz + dane',
        'Sweet spot 27" dla productivity'
    ],
    'XUB2797QSN': [
        'Steruj dwoma kompami jedną klawiaturą (Game Changer dla IT)',
        'Jeden kabel z laptopa obsługuje wszystko',
        'Więcej miejsca = mniej Alt+Tab'
    ],
    'XUB3293UHSN': [
        'Każdy piksel widoczny – doskonałe do CAD i excel sheets',
        '32" to prawie jak mały TV na biurku',
        'Jeden kabel: zasilanie + obraz + dane'
    ],
    
    # Digital Signage
    'LH4341UHS': [
        'Każdy piksel widoczny z 5 metrów',
        'Stworzony do pracy non-stop 24/7',
        'Wbudowany Android = nie potrzebujesz media playera za 500zł'
    ],
    'LH5541UHS': [
        'Każdy piksel widoczny z drugiego końca sali',
        'Stworzony do pracy non-stop bez przegrzewania',
        '55" immersji dla digital signage'
    ],
    'TE5512MIS': [
        'Wbudowany Android = gotowy out of the box',
        'Certyfikacja Google – Play Store działa bez tricków'
    ],
}

# Visual Archetypes by Vertical
VISUAL_ARCHETYPES = {
    'gaming': 'Cyberpunk | RGB Glow | Immersive Gaming | Dark Room Setup | Neon Accents',
    'office': 'Minimal | Clean Desk | Scandinavian | Natural Light | Professional',
    'prographics': 'Studio Setup | Color Accurate | Creative Workspace | Neutral Tones | Artistic',
    'signage': 'Commercial Space | Bold Typography | Retail Environment | High Visibility | Corporate',
}

# Marketing Personas by Vertical
PERSONA_MAP = {
    'gaming': 'Gracz Kompetytywny | Gracz Casualowy | Streamer | Content Creator | Sim Racer',
    'office': 'IT Admin | Remote Worker | Menedżer | Programista | Księgowy | Home Office',
    'prographics': 'Grafik | Fotograf | Video Editor | Architekt | Ilustrator | UI Designer',
    'signage': 'Marketing Manager | AV Integrator | IT Szkolny | Retail Manager | Recepcjonista',
}


class CreativeDataBridge:
    """Enhanced ETL Pipeline for Creative Data."""
    
    def __init__(self, brand: str, input_dir: str = 'Input', output_dir: str = 'Output'):
        self.brand = brand
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.harvest_data: Dict = {}
        self.brand_constraints: Dict = {}
        self.conflicts: List[Dict] = []
    
    def load_harvest_data(self) -> Dict:
        """Load all RAW_HARVEST_DATA_*.json files."""
        brand_dir = os.path.join(self.input_dir, self.brand)
        
        for f in Path(brand_dir).glob('RAW_HARVEST_DATA_*.json'):
            vertical_name = f.stem.replace('RAW_HARVEST_DATA_', '')
            with open(f, 'r', encoding='utf-8') as fp:
                self.harvest_data[vertical_name] = json.load(fp)
        
        print(f"[JSON] Loaded {len(self.harvest_data)} harvest files: {list(self.harvest_data.keys())}")
        return self.harvest_data
    
    def match_product_to_vertical(self, row: pd.Series) -> str:
        """Determine vertical using product code pattern matching."""
        title = str(row.get('feed_title', '')).lower()
        category = str(row.get('feed_category', '')).lower()
        
        # Priority 1: Product code patterns
        if re.search(r'\bgb[0-9]', title) or re.search(r'\bg[0-9]{2,4}', title) or 'g-master' in title:
            return 'gaming'
        
        if re.search(r'\blh[0-9]', title) or re.search(r'\bte[0-9]', title):
            return 'signage'
        
        if ('4k' in title or 'uhd' in title) and 'xub' in title:
            return 'prographics'
        
        if re.search(r'\bxu[0-9b]', title) or re.search(r'\bxb[0-9]', title) or 'prolite' in title:
            return 'office'
        
        # Priority 2: Category fallback
        if 'gaming' in category or 'game' in category:
            return 'gaming'
        elif 'signage' in category or 'commercial' in category:
            return 'signage'
        
        return 'office'
    
    def extract_insights_by_basket(self, harvest_data: Dict, basket_type: str, max_items: int = 10) -> List[str]:
        """Extract insights by basket type (PAIN, DREAM, TRUST, TRIBAL)."""
        insights = []
        
        if 'deep_harvest_insights' not in harvest_data:
            return insights
        
        for phase_name, phase_insights in harvest_data['deep_harvest_insights'].items():
            for insight in phase_insights:
                if insight.get('basket') == basket_type:
                    raw_quote = insight.get('raw_quote', '')
                    if raw_quote and len(raw_quote) > 15:
                        # Truncate and clean
                        if len(raw_quote) > 100:
                            raw_quote = raw_quote[:97] + '...'
                        insights.append(raw_quote)
        
        return insights[:max_items]
    
    def extract_slang(self, harvest_data: Dict) -> List[str]:
        """Extract tribal slang from harvest data."""
        slang = set()
        
        # From individual insights
        if 'deep_harvest_insights' in harvest_data:
            for phase_insights in harvest_data['deep_harvest_insights'].values():
                for insight in phase_insights:
                    for s in insight.get('slang_detected', []):
                        if s and len(s) > 2:
                            slang.add(s)
        
        # From tribal_language_dictionary
        if 'tribal_language_dictionary' in harvest_data:
            tld = harvest_data['tribal_language_dictionary']
            for category, content in tld.items():
                if isinstance(content, dict):
                    for subcategory, terms in content.items():
                        if isinstance(terms, list):
                            slang.update([t for t in terms if len(t) > 2][:5])
                        elif isinstance(terms, str) and len(terms) > 2:
                            slang.add(subcategory)  # Use key as slang term
        
        return list(slang)[:15]
    
    def extract_competitors(self, harvest_data: Dict) -> List[str]:
        """Extract competitor references."""
        competitors = set()
        
        if 'key_findings' in harvest_data:
            if 'competitor_context' in harvest_data['key_findings']:
                competitors.update(harvest_data['key_findings']['competitor_context'].keys())
        
        if 'competitor_context' in harvest_data:
            competitors.update(harvest_data['competitor_context'].keys())
        
        # Clean up keys
        clean_competitors = []
        for c in competitors:
            name = c.replace('_', ' ').title()
            if name not in ['Market Position']:
                clean_competitors.append(name)
        
        return clean_competitors if clean_competitors else ['Samsung', 'Dell', 'LG']
    
    def apply_tech_translator(self, text: str, title: str = '') -> List[str]:
        """Convert technical specs to consumer benefits with SKU fallback."""
        benefits = []
        
        # Try regex-based extraction first
        for pattern, benefit in TECH_TRANSLATOR.items():
            if re.search(pattern, text, re.IGNORECASE):
                if benefit not in benefits:
                    benefits.append(benefit)
        
        # If regex fails, try SKU fallback lookup
        if not benefits and title:
            title_upper = title.upper()
            for sku, fallback_benefits in SKU_FALLBACK_SPECS.items():
                if sku.upper() in title_upper:
                    benefits = fallback_benefits.copy()
                    break
        
        return benefits
    
    def sanitize_for_csv(self, items: List) -> str:
        """Convert list to pipe-separated string."""
        if not items:
            return "General"
        
        clean_items = []
        for item in items:
            if item and isinstance(item, str):
                clean = item.replace('|', '-').replace('\n', ' ').replace('\r', ' ')
                clean = ' '.join(clean.split())
                if clean:
                    clean_items.append(clean)
        
        return ' | '.join(clean_items[:10]) if clean_items else "General"
    
    def enrich_row(self, row: pd.Series) -> pd.Series:
        """Enrich a single row with creative data."""
        # Determine vertical
        vertical = self.match_product_to_vertical(row)
        vertical_key = f'v_{vertical}'
        
        # Get harvest data for this vertical
        harvest_data = self.harvest_data.get(vertical, {})
        if not harvest_data and self.harvest_data:
            harvest_data = list(self.harvest_data.values())[0]
        
        # Create synthetic description
        title = str(row.get('feed_title', ''))
        category = str(row.get('feed_category', ''))
        description = f"{title} {category}"
        
        # Extract creative data
        pains = self.extract_insights_by_basket(harvest_data, 'PAIN')
        dreams = self.extract_insights_by_basket(harvest_data, 'DREAM')
        slang = self.extract_slang(harvest_data)
        tech_benefits = self.apply_tech_translator(description, title)
        competitors = self.extract_competitors(harvest_data)
        
        return pd.Series({
            'marketing_personas': PERSONA_MAP.get(vertical, 'General Consumer'),
            'pain_points_pool': self.sanitize_for_csv(pains),
            'desire_outcomes_pool': self.sanitize_for_csv(dreams),
            'tribal_slang': self.sanitize_for_csv(slang),
            'tech_translator': self.sanitize_for_csv(tech_benefits),
            'visual_archetypes': VISUAL_ARCHETYPES.get(vertical, 'Professional | Clean'),
            'competitor_anchors': self.sanitize_for_csv(competitors),
        })
    
    def run(self) -> pd.DataFrame:
        """Execute the full ETL pipeline."""
        print(f"\n>>> Creative Data Bridge v2.0 for: {self.brand}")
        
        # 1. Load source CSV
        csv_path = os.path.join(self.output_dir, self.brand, f"{self.brand}_Growth_Opportunities.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Source CSV not found: {csv_path}")
        
        df = pd.read_csv(csv_path)
        print(f"[CSV] Loaded {len(df)} rows from {csv_path}")
        
        # 2. Load Harvest JSONs
        self.load_harvest_data()
        
        # 3. Enrich each row
        print("[ETL] Enriching rows with creative data...")
        enriched = df.apply(self.enrich_row, axis=1)
        df = pd.concat([df, enriched], axis=1)
        
        # 4. Save output
        out_path = os.path.join(self.output_dir, self.brand, f"MASTER_CREATIVE_FEED_{self.brand}.csv")
        df.to_csv(out_path, index=False)
        print(f"[OUTPUT] Saved: {out_path}")
        
        return df


if __name__ == '__main__':
    import sys
    
    brand = sys.argv[1] if len(sys.argv) > 1 else 'Iiyama'
    bridge = CreativeDataBridge(brand)
    bridge.run()
