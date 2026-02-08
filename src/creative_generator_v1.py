#!/usr/bin/env python3
"""
Creative Generator v1.0 - Proof of Concept Asset Generation
Generates briefs, copy variants, and image prompts from the Master Creative Feed.

Usage: python src/creative_generator_v1.py [brand]
"""

import os
import pandas as pd
from pathlib import Path
from typing import Dict, List

# === BRAND CONSTRAINTS (Loaded from config) ===
HARD_CONSTRAINTS = {
    'never_claim': [
        'intuitive controls',
        'factory calibrated',
        'zero defects',
        'perfect quality control',
        'best in class colors',
        'zero bad pixels guarantee',
        'premium build quality',
        'HDR gaming ready',
    ],
    'qualify_claims': {
        'USB hub': 'May have bandwidth limits at 4K',
        'always connected': 'WiFi may require reconnection on boot',
        'ergonomic': 'Budget models may have pivot limitations',
    }
}

CONFLICT_MARKERS = {
    'premium_vs_budget': ('premium', 'budget', 'VALUE positioning wins'),
    'quality_vs_lottery': ('superior quality', 'panel lottery', 'SPECS positioning wins'),
    'support_vs_reality': ('great support', 'slower support', 'AVOID support messaging'),
}


def load_creative_feed(brand: str, output_dir: str = 'Output') -> pd.DataFrame:
    """Load the Master Creative Feed."""
    csv_path = os.path.join(output_dir, brand, f"MASTER_CREATIVE_FEED_{brand}.csv")
    return pd.read_csv(csv_path)


def select_test_subjects(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Select 3 test subjects: Star, Workhorse, Edge Case."""
    subjects = {}
    
    # Star: Highest revenue gaming product
    gaming = df[df['feed_title'].str.contains('GB|G-Master', case=False, na=False)]
    if not gaming.empty:
        gaming_sorted = gaming.sort_values('meta_revenue', ascending=False, na_position='last')
        subjects['star'] = gaming_sorted.iloc[0]
    
    # Workhorse: Office/B2B monitor with decent performance
    office = df[df['feed_title'].str.contains('XUB|XU[0-9]', case=False, na=False)]
    if not office.empty:
        office_sorted = office.sort_values('ga4lp_sessions', ascending=False, na_position='last')
        subjects['workhorse'] = office_sorted.iloc[0]
    
    # Edge Case: Signage or unusual product
    signage = df[df['feed_title'].str.contains('LH|TE[0-9]', case=False, na=False)]
    if not signage.empty:
        subjects['edge_case'] = signage.iloc[0]
    else:
        # Fallback to any low-performing product
        low_perf = df[df['calc_segment'] == 'IGNORE']
        if not low_perf.empty:
            subjects['edge_case'] = low_perf.iloc[0]
    
    return subjects


def generate_brief(subject: pd.Series, subject_type: str, output_dir: str) -> str:
    """Generate a creative brief for the subject."""
    sku = str(subject.get('feed_title', 'Unknown'))[:30].replace(' ', '_').replace('"', '')
    
    brief = f"""# Creative Brief: {subject_type.upper()}

## Product
**SKU:** {subject.get('feed_id', 'N/A')}
**Title:** {subject.get('feed_title', 'Unknown')}
**Price:** {subject.get('feed_price_numeric', 'N/A')} PLN
**Category:** {subject.get('feed_category', 'N/A')}

---

## Target Audience
**Personas:** {subject.get('marketing_personas', 'General')}

---

## Voice of Customer Data

### Pain Points (Use for Hooks)
{subject.get('pain_points_pool', 'No data')}

### Desires (Use for Benefits)
{subject.get('desire_outcomes_pool', 'No data')}

### Tribal Slang (Use for Authenticity)
{subject.get('tribal_slang', 'No data')}

---

## Technical Benefits Translated
{subject.get('tech_translator', 'General')}

---

## Visual Direction
**Archetypes:** {subject.get('visual_archetypes', 'Professional')}

---

## Competitive Angle
**Anchors:** {subject.get('competitor_anchors', 'Samsung | Dell | LG')}

---

## 🔴 RED LINES (Do Not Violate)
- Never claim "intuitive controls" (OSD on rear)
- Never claim "factory calibrated" (unless ProArt series)
- Never claim "zero defects" (panel lottery exists)
- Never claim "premium build" (thick bezels, rear buttons)
- Never claim "HDR gaming ready" (HDR-Ready is marketing)

---

## Performance Context
- **Segment:** {subject.get('calc_segment', 'Unknown')}
- **ROAS:** {subject.get('calc_roas', 'N/A')}
- **Sessions:** {subject.get('ga4lp_sessions', 0)}
"""
    
    # Save brief
    brief_path = os.path.join(output_dir, f"{sku}_BRIEF.md")
    with open(brief_path, 'w', encoding='utf-8') as f:
        f.write(brief)
    
    return brief_path


def generate_copy_variant_a(subject: pd.Series, output_dir: str) -> str:
    """Generate emotional/PAS copy variant."""
    sku = str(subject.get('feed_title', 'Unknown'))[:30].replace(' ', '_').replace('"', '')
    title = subject.get('feed_title', 'Monitor')
    
    # Extract first pain and dream
    pains = str(subject.get('pain_points_pool', '')).split(' | ')
    dreams = str(subject.get('desire_outcomes_pool', '')).split(' | ')
    
    pain = pains[0] if pains else 'frustracja'
    dream = dreams[0] if dreams else 'komfort'
    
    copy = f"""[COPY VARIANT A - EMOTIONAL/PAS]

🎯 TARGET: {subject.get('marketing_personas', 'General').split(' | ')[0]}

---

HOOK (Pain Trigger):
"{pain[:80]}..."

AGITATION:
Znasz to uczucie? Każda sesja to kompromis. Każdy projekt to walka z ograniczeniami.
To nie Twoja wina - to sprzęt, który nie nadąża za Twoimi ambicjami.

SOLUTION:
{title}

Stworzony dla tych, którzy:
• {dream[:60] if dream else 'Szukają czegoś więcej'}
• Nie chcą przepłacać za logo
• Cenią funkcjonalność nad marketing

CTA:
Sprawdź, czy to monitor dla Ciebie →

---

[Tech Specs Support:]
{subject.get('tech_translator', 'General')}
"""
    
    copy_path = os.path.join(output_dir, f"{sku}_COPY_VARIANT_A.txt")
    with open(copy_path, 'w', encoding='utf-8') as f:
        f.write(copy)
    
    return copy_path


def generate_copy_variant_b(subject: pd.Series, output_dir: str) -> str:
    """Generate logical/technical comparison copy variant."""
    sku = str(subject.get('feed_title', 'Unknown'))[:30].replace(' ', '_').replace('"', '')
    title = subject.get('feed_title', 'Monitor')
    
    competitors = str(subject.get('competitor_anchors', 'Samsung | Dell')).split(' | ')
    tech = str(subject.get('tech_translator', '')).split(' | ')
    
    copy = f"""[COPY VARIANT B - LOGICAL/COMPARISON]

🎯 TARGET: Świadomy kupujący, researching before purchase

---

HEADLINE:
{title} vs {competitors[0] if competitors else 'Konkurencja'}

COMPARISON TABLE:
| Cecha | iiyama | {competitors[0] if competitors else 'Inni'} |
| --- | --- | --- |
| Cena | Niższa ~40% | Wyższa |
| Panel | Ten sam producent | Ten sam |
| Funkcje | {tech[0] if tech else 'Standard'} | Standard |
| Gwarancja | 3 lata | 3 lata |

LOGIC CHAIN:
1. Ten sam panel LG/Samsung co w droższych modelach
2. Te same funkcje: {' | '.join(tech[:3]) if tech else 'Standard'}
3. 40% niższa cena
4. → Oszczędność bez kompromisu

OBJECTION HANDLER:
"Ale czy to nie budżetowy zamiennik?"
→ To ten sam panel. Różnica to logo.

CTA:
Porównaj specyfikację sam →

---

[Competitor Anchors:]
{subject.get('competitor_anchors', 'Samsung | Dell | LG')}
"""
    
    copy_path = os.path.join(output_dir, f"{sku}_COPY_VARIANT_B.txt")
    with open(copy_path, 'w', encoding='utf-8') as f:
        f.write(copy)
    
    return copy_path


def generate_image_prompt(subject: pd.Series, output_dir: str) -> str:
    """Generate detailed image prompt for Nano Banana."""
    sku = str(subject.get('feed_title', 'Unknown'))[:30].replace(' ', '_').replace('"', '')
    title = subject.get('feed_title', 'Monitor')
    
    archetypes = str(subject.get('visual_archetypes', 'Professional')).split(' | ')
    personas = str(subject.get('marketing_personas', 'Professional')).split(' | ')
    
    # Determine vertical for specific styling
    title_lower = title.lower()
    if 'gb' in title_lower or 'g-master' in title_lower:
        vertical = 'gaming'
        lighting = 'dramatic RGB lighting with purple and cyan accent lights'
        environment = 'dark gaming room with LED strips'
        mood = 'intense, competitive, immersive'
    elif 'lh' in title_lower or 'te' in title_lower:
        vertical = 'signage'
        lighting = 'bright commercial lighting, evenly lit'
        environment = 'modern retail space or corporate lobby'
        mood = 'professional, bold, high visibility'
    else:
        vertical = 'office'
        lighting = 'soft natural daylight from large windows'
        environment = 'minimalist Scandinavian home office'
        mood = 'calm, productive, clean'
    
    prompt = f"""[IMAGE GENERATION PROMPT - NANO BANANA]

SUBJECT: {title}

---

## Composition
- **Framing:** 3/4 angle product shot, monitor slightly angled
- **Focus:** Sharp focus on screen, subtle depth blur on background
- **Rule of Thirds:** Monitor positioned at left intersection

## Lighting
- **Style:** {lighting}
- **Key Light:** 45° from camera, soft diffusion
- **Fill:** Subtle ambient from environment
- **Accent:** {archetypes[0] if archetypes else 'Professional'} color temperature

## Environment
- **Setting:** {environment}
- **Props:** Minimal - keyboard, mouse, plant (no clutter)
- **Background:** {archetypes[1] if len(archetypes) > 1 else 'Blurred'} aesthetic

## Screen Content
- **Display:** Abstract gradient or workspace mockup
- **Color:** Match {vertical} visual style
- **NO:** Real logos, text, or copyrighted content

## Mood
- **Emotion:** {mood}
- **Target Persona:** {personas[0] if personas else 'Professional'}
- **Aspirational:** Success, productivity, achievement

## Technical
- **Aspect:** 4:5 (Instagram) or 16:9 (web)
- **Quality:** Photorealistic, 8K detail
- **Post:** Light color grading to enhance {vertical} mood

---

NEGATIVE PROMPT:
- No humans/faces
- No visible cables or mess
- No generic stock photo feel
- No outdated furniture
- No direct competitor products
"""
    
    prompt_path = os.path.join(output_dir, f"{sku}_IMG_PROMPT.txt")
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    return prompt_path


def run_generator(brand: str):
    """Execute the full generation pipeline."""
    print(f"\n>>> Creative Generator v1.0 for: {brand}")
    
    # Create output directory
    output_dir = os.path.join('Output', brand, 'output_test_assets')
    os.makedirs(output_dir, exist_ok=True)
    
    # Load creative feed
    df = load_creative_feed(brand)
    print(f"[CSV] Loaded {len(df)} products from Master Creative Feed")
    
    # Select test subjects
    subjects = select_test_subjects(df)
    print(f"[SELECT] Found {len(subjects)} test subjects: {list(subjects.keys())}")
    
    # Generate assets for each subject
    generated_files = []
    
    for subject_type, subject in subjects.items():
        print(f"\n[GEN] Generating assets for: {subject_type}")
        
        # Create subject folder
        subject_dir = os.path.join(output_dir, subject_type)
        os.makedirs(subject_dir, exist_ok=True)
        
        # Generate all assets
        brief = generate_brief(subject, subject_type, subject_dir)
        copy_a = generate_copy_variant_a(subject, subject_dir)
        copy_b = generate_copy_variant_b(subject, subject_dir)
        img_prompt = generate_image_prompt(subject, subject_dir)
        
        generated_files.extend([brief, copy_a, copy_b, img_prompt])
        print(f"  ✓ Brief: {brief}")
        print(f"  ✓ Copy A: {copy_a}")
        print(f"  ✓ Copy B: {copy_b}")
        print(f"  ✓ Image Prompt: {img_prompt}")
    
    print(f"\n[DONE] Generated {len(generated_files)} files in {output_dir}")
    return generated_files


if __name__ == '__main__':
    import sys
    
    brand = sys.argv[1] if len(sys.argv) > 1 else 'Iiyama'
    run_generator(brand)
