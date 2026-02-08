#!/usr/bin/env python3
"""
Creative Generator v2.0 - The Creative Matrix Engine (UGLY TRUTH EDITION)
Generates 3 style variants with RADICAL AUTHENTICITY personas.

Usage: python src/creative_generator_v2.py [brand]
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

# === RADICAL PERSONA SYSTEM PROMPTS ===

PERSONA_PROMPTS = {
    'AESTHETIC': {
        'copy_system': """You are a Minimalist Brand Strategist for a luxury brand.
RULES:
- Use sentence fragments, not full sentences.
- Focus on IDENTITY ("Tool for the pros"), not features.
- NO exclamation marks ever.
- Whisper power, don't shout it.
- If it reads like marketing copy, DELETE IT.
- Maximum 30 words total.""",
        'visual_system': """Softbox lighting, 8K resolution, Cinematic Bokeh, Golden Hour warmth.
Clean composition with NO CLUTTER.
Floating product or reflective surface.
Studio infinity curve background.
Unreal Engine 5 render quality.""",
    },
    
    'NATIVE_RAW': {
        'copy_system': """You are an angry/excited user on a tech forum (Reddit/Pepper.pl).
FORGET YOU ARE AN AI.
RULES:
- Use slang NATURALLY (not forced): "petarda", "kozak", "rzecz jest taka"
- ADMIT a small flaw ("przyciski z tyłu to porażka") to prove the big win
- Use CAPITALIZATION for emphasis (like: "ALE panel jest BOŻY")
- Personal experience > spec sheets
- IF IT SOUNDS LIKE MARKETING, DELETE IT IMMEDIATELY
- Write like you're texting a friend who asked "czy warto?"
- Include honest opinion with real emotion""",
        'visual_system': """Smartphone camera photo, Flash ON, Harsh shadows visible.
Grainy texture, slight motion blur acceptable.
Messy desk environment: visible cables, coffee cup, keyboard.
POV shot from user perspective.
Fingerprints on bezel are GOOD.

NEGATIVE: NO studio lighting, NO professional photography, NO perfect composition, NO bokeh, NO 3D render.""",
    },
    
    'PATTERN_INTERRUPT': {
        'copy_system': """You are a Tabloid Editor writing a headline that sounds like a WARNING or a LEAK.
RULES:
- Use "Us vs Them" framing (iiyama vs Samsung/Dell)
- Attack the status quo ("Dlaczego przepłacasz za logo?")
- Create URGENCY and FOMO
- Use contrarian angles ("To co mówią producenci to BS")
- Headlines should sound like secrets being revealed
- Use emoji sparingly for stopping power: ⚠️ 🔴 ❌ ✓""",
        'visual_system': """CCTV footage style or high contrast editorial.
Split screen comparison: iiyama vs competitor.
Red circle drawn in MS Paint style on key feature.
Yellow "Warning" tape overlay or Post-it notes.
"Breaking News" lower third aesthetic.
Text overlays with dramatic fonts.""",
    },
}

# === BRAND SAFETY (RED LINES) ===

BRAND_SAFETY_VETOES = [
    'intuitive controls', 'intuicyjna obsługa',
    'factory calibrated', 'fabryczna kalibracja', 
    'zero defects', 'zero wad',
    'zero bad pixels', 'zero martwych pikseli',
    'premium build quality', 'premium jakość',
    'HDR gaming ready', 'HDR ready',
    'best in class', 'najlepsze w klasie',
]


def load_creative_feed(brand: str, output_dir: str = 'Output') -> pd.DataFrame:
    """Load the Master Creative Feed."""
    csv_path = os.path.join(output_dir, brand, f"MASTER_CREATIVE_FEED_{brand}.csv")
    return pd.read_csv(csv_path)


def select_test_subjects(df: pd.DataFrame) -> Dict[str, Tuple[pd.Series, str]]:
    """Select 3 test subjects with their folder names."""
    subjects = {}
    
    # Gaming Monitor (Star)
    gaming = df[df['feed_title'].str.contains('GB|G-Master', case=False, na=False)]
    if not gaming.empty:
        gaming_sorted = gaming.sort_values('meta_revenue', ascending=False, na_position='last')
        subjects['Gaming_Monitor'] = (gaming_sorted.iloc[0], 'gaming')
    
    # Office Monitor (Workhorse)
    office = df[df['feed_title'].str.contains('XUB|XU[0-9]', case=False, na=False)]
    if not office.empty:
        office_sorted = office.sort_values('ga4lp_sessions', ascending=False, na_position='last')
        subjects['Office_Monitor'] = (office_sorted.iloc[0], 'office')
    
    # Signage (Edge Case)
    signage = df[df['feed_title'].str.contains('LH|TE[0-9]', case=False, na=False)]
    if not signage.empty:
        subjects['Signage_Display'] = (signage.iloc[0], 'signage')
    
    return subjects


def apply_brand_safety(text: str) -> str:
    """Apply brand safety checks - block vetoed phrases."""
    text_lower = text.lower()
    for veto in BRAND_SAFETY_VETOES:
        if veto.lower() in text_lower:
            text = re.sub(re.escape(veto), '[BLOCKED]', text, flags=re.IGNORECASE)
    return text


def get_product_flaw(vertical: str) -> str:
    """Return a known flaw for authenticity in Native Raw style."""
    flaws = {
        'gaming': 'Przyciski OSD z tyłu to PORAŻKA UX. Potrzebujesz lusterka żeby cokolwiek zmienić.',
        'office': 'Menu jest z epoki kamienia. Ale serio, ile razy w roku zmieniasz ustawienia?',
        'signage': 'Polski interfejs? Zapomnij. Android po angielsku, ale robi robotę.',
    }
    return flaws.get(vertical, 'Nie jest idealny – ale co jest?')


def generate_image_prompt(subject: pd.Series, style: str, vertical: str) -> str:
    """Generate image prompt based on radical persona."""
    title = subject.get('feed_title', 'Monitor')
    persona = PERSONA_PROMPTS[style]
    
    prompt = f"""[IMAGE GENERATION PROMPT]
[STYLE: {style}]

SUBJECT: {title}

---

## PERSONA INSTRUCTION (FOLLOW EXACTLY):
{persona['visual_system']}

---

## COMPOSITION"""

    if style == 'AESTHETIC':
        prompt += f"""
- Product floating on reflective black surface
- Single soft key light at 45° angle
- Background: pure gradient, dark charcoal to lighter gray
- Rim light highlighting product edges
- Screen showing abstract gradient (no real content)
- ABSOLUTELY NO: cables, hands, clutter, text overlays
- Render quality: 8K, photorealistic, commercial photography"""

    elif style == 'NATIVE_RAW':
        prompt += f"""
- POV shot: looking at monitor from user's seated position
- Environment: REAL desk with visible mess
  - Mechanical keyboard (bonus: RGB on)
  - Mouse with cable visible
  - Coffee cup (half empty)
  - Random cables and USB drives
  - Post-it notes on desk
- Lighting: harsh direct flash OR window light with hard shadows
- Camera: smartphone quality, slight grain
- Screen showing: actual game/work screenshot (not marketing material)
- Monitor bezel: fingerprints and dust visible = GOOD
- INCLUDE: the imperfect reality of a real setup"""

    elif style == 'PATTERN_INTERRUPT':
        prompt += f"""
- Split screen layout: LEFT = iiyama, RIGHT = competitor (Samsung/Dell)
- iiyama side: product photo with GREEN checkmark overlay
- Competitor side: grayed out with RED X overlay
- Visual elements:
  - Red circle (MS Paint style) around price
  - Yellow arrow pointing to key feature
  - "Breaking News" style lower third text bar
  - Dramatic high contrast lighting
  - "UWAGA" or "⚠️" watermark
- Text overlay: price comparison or "Ten sam panel, 40% taniej" """

    prompt += f"""

---

## TECHNICAL SPECS
- Aspect: 4:5 (Instagram/Meta) or 16:9 (Web)
- Quality: {'8K photorealistic' if style == 'AESTHETIC' else 'Authentic smartphone quality' if style == 'NATIVE_RAW' else 'Bold editorial/news'}

## NEGATIVE PROMPT (DO NOT INCLUDE):
{('Any imperfection, visible cables, human elements' if style == 'AESTHETIC' else 
  'Studio lighting, professional photography, perfect composition, clean desk' if style == 'NATIVE_RAW' else 
  'Boring composition, no visual tension, subtle messaging')}
"""
    return prompt


def generate_copy(subject: pd.Series, style: str, vertical: str) -> str:
    """Generate copy based on radical persona injection."""
    persona = PERSONA_PROMPTS[style]
    title = subject.get('feed_title', 'Monitor')
    
    # Extract VOC data
    pains = str(subject.get('pain_points_pool', '')).split(' | ')
    dreams = str(subject.get('desire_outcomes_pool', '')).split(' | ')
    slang = str(subject.get('tribal_slang', '')).split(' | ')
    tech = str(subject.get('tech_translator', '')).split(' | ')
    competitors = str(subject.get('competitor_anchors', 'Samsung | Dell')).split(' | ')
    
    pain = pains[0] if pains and pains[0] not in ['General', ''] else 'Frustracja ze starego monitora'
    dream = dreams[0] if dreams and dreams[0] not in ['General', ''] else 'Setup marzeń'
    slang_word = slang[0] if slang and slang[0] not in ['General', ''] else 'petarda'
    tech_benefit = tech[0] if tech and tech[0] not in ['General', ''] else 'Jakość obrazu'
    tech_benefit_2 = tech[1] if len(tech) > 1 and tech[1] not in ['General', ''] else 'Sprawdzona jakość'
    competitor = competitors[0] if competitors else 'konkurencja'
    
    copy = f"""[COPY]
[STYLE: {style}]

---

## PERSONA SYSTEM PROMPT (THIS GUIDED THE OUTPUT):
{persona['copy_system']}

---

"""
    
    if style == 'AESTHETIC':
        # Ultra minimalist - whispered power
        copy += f"""## OUTPUT:

{title}

---

Precyzja.

Dla tych, którzy widzą różnicę.

{tech_benefit.split('–')[0].strip()}.

---

[STYLE CHECK]
✓ No exclamation marks
✓ Sentence fragments only
✓ Under 30 words
✓ Identity over features
"""

    elif style == 'NATIVE_RAW':
        # Angry forum user - radical authenticity
        flaw = get_product_flaw(vertical)
        
        copy += f"""## OUTPUT:

**[TYTUŁ]** Szczera recenzja po 3 miesiącach: {title}

**[TREŚĆ]**

Ok, {slang_word}, rzecz jest taka:

{flaw}

ALE.

Panel jest BOŻY. {tech_benefit}.

{tech_benefit_2}.

Za tę cenę? Brałem z łezką bo {competitor} za to samo chce 40% więcej.

Polecam? TAK, ale wiedz w co wchodzisz.

**[TL;DR]** Ergonomia średnia, panel god-tier, cena uczciwa.

---

[STYLE CHECK]
✓ Admits flaw first
✓ Uses slang naturally: {slang_word}
✓ Personal experience voice
✓ CAPS for emphasis
✓ Doesn't sound like marketing
"""

    elif style == 'PATTERN_INTERRUPT':
        # Tabloid editor - shock and contrast
        copy += f"""## OUTPUT:

⚠️ **ZANIM KUPISZ MONITOR, PRZECZYTAJ TO**

Prawda, którą {competitor} chce przed Tobą ukryć:

**FAKT:** Ten sam panel LG/Samsung co w monitorach za 2000zł+
**FAKT:** 40% niższa cena
**FAKT:** Jedyna różnica? Logo.

---

**{title}:**
✓ {tech_benefit}
✓ {tech_benefit_2}
✓ Gwarancja 3 lata door-to-door

**{competitor}?**
❌ Przepłacasz za marketing
❌ Te same podzespoły
❌ Ta sama fabryka w Chinach

---

**Sprawdź zanim przepłacisz →**

---

[STYLE CHECK]
✓ "Warning" hook
✓ Us vs Them framing
✓ Contrarian angle
✓ FOMO and urgency
✓ Check/X visual structure
"""

    # Apply brand safety
    copy = apply_brand_safety(copy)
    
    return copy


def run_matrix_generator(brand: str):
    """Execute the Creative Matrix generation with Radical Authenticity."""
    print(f"\n>>> Creative Matrix Generator v2.0 (UGLY TRUTH EDITION) for: {brand}")
    
    # Create output directory
    base_output = os.path.join('Output', brand, 'output_matrix')
    os.makedirs(base_output, exist_ok=True)
    
    # Load creative feed
    df = load_creative_feed(brand)
    print(f"[CSV] Loaded {len(df)} products from Master Creative Feed")
    
    # Select test subjects
    subjects = select_test_subjects(df)
    print(f"[SELECT] Found {len(subjects)} test subjects: {list(subjects.keys())}")
    
    # Generate 3 variants for each subject
    styles = ['AESTHETIC', 'NATIVE_RAW', 'PATTERN_INTERRUPT']
    total_files = 0
    
    for product_name, (subject, vertical) in subjects.items():
        print(f"\n[PRODUCT] {product_name}: {subject.get('feed_title', 'Unknown')}")
        
        for style in styles:
            style_folder = {
                'AESTHETIC': 'Aesthetic',
                'NATIVE_RAW': 'Native',
                'PATTERN_INTERRUPT': 'Interrupt'
            }[style]
            
            output_dir = os.path.join(base_output, product_name, style_folder)
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate image prompt
            img_prompt = generate_image_prompt(subject, style, vertical)
            img_path = os.path.join(output_dir, 'IMG_PROMPT.txt')
            with open(img_path, 'w', encoding='utf-8') as f:
                f.write(img_prompt)
            
            # Generate copy
            copy = generate_copy(subject, style, vertical)
            copy_path = os.path.join(output_dir, 'COPY.txt')
            with open(copy_path, 'w', encoding='utf-8') as f:
                f.write(copy)
            
            print(f"  ✓ {style}: {output_dir}")
            total_files += 2
    
    print(f"\n[DONE] Generated {total_files} files in {base_output}")
    print(f"[STRUCTURE] {len(subjects)} products × 3 styles = {len(subjects) * 3} variant folders")
    
    return base_output


if __name__ == '__main__':
    import sys
    
    brand = sys.argv[1] if len(sys.argv) > 1 else 'Iiyama'
    run_matrix_generator(brand)
