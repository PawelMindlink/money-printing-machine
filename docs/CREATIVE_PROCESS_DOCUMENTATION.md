# Creative Process Documentation

## Overview

This document describes the Voice of Customer (VOC) Harvest process and the Creative Data Bridge ETL pipeline.

## VOC Harvest Input Structure

### File Naming Convention

```
RAW_HARVEST_DATA_[vertical].json
```

**Supported Verticals:**

- `gaming` - Gaming monitors (G-Master series)
- `office` - Office/Business monitors (ProLite series)
- `prographics` - Professional graphics (Color-critical work)
- `signage` - Digital Signage (LH/TE series)

### Required JSON Structure

```json
{
  "vertical": "v_gaming",
  "harvest_date": "2026-02-02",
  "target_models": {
    "budget": {"code": "SKU-123", "price": "999 PLN"},
    "mid_range": {"code": "SKU-456", "price": "1499 PLN"}
  },
  "deep_harvest_insights": {
    "phase_1_ceneo": [
      {
        "id": "C01",
        "basket": "PAIN",
        "raw_quote": "User complaint verbatim...",
        "product": "Product Model",
        "slang_detected": ["term1", "term2"]
      }
    ]
  },
  "tribal_language_dictionary": {
    "polish_slang": {"positive": ["rewelka"], "negative": ["porażka"]}
  },
  "competitor_context": {
    "Samsung": "Main competitor...",
    "Dell": "Premium alternative..."
  }
}
```

### Basket Types

| Basket | Purpose |
| :--- | :--- |
| `PAIN` | Customer frustrations and complaints |
| `DREAM` | Desires, aspirations, ideal outcomes |
| `TRUST` | Satisfaction signals, brand loyalty |
| `TRIBAL` | Technical terms, insider vocabulary |
| `SLANG` | Polish colloquialisms |

---

## Output Schema (7 Creative Columns)

| Column | Format | Purpose |
| :--- | :--- | :--- |
| `marketing_personas` | Pipe-separated | Target avatars for ad targeting |
| `pain_points_pool` | Pipe-separated | Raw VOC quotes for hooks |
| `desire_outcomes_pool` | Pipe-separated | Dream states for benefits |
| `tribal_slang` | Pipe-separated | Insider vocabulary for copy |
| `tech_translator` | Pipe-separated | Feature→Benefit mappings |
| `visual_archetypes` | Pipe-separated | Aesthetic direction for creatives |
| `competitor_anchors` | Pipe-separated | Rivals for comparison ads |

---

## Tech Translator Mappings

| Technical Spec | Consumer Benefit |
| :--- | :--- |
| `165Hz` | Płynność |
| `4K/UHD` | Ostrość detali |
| `IPS` | Szerokie kąty widzenia |
| `USB-C` | Jeden kabel |
| `KVM` | Przełączanie PC |
| `Flicker-Free` | Ochrona oczu |
| `HDR` | Dynamiczny obraz |

---

## Usage

```bash
python src/creative_data_bridge.py [Brand]
```

**Output:** `Output/[Brand]/MASTER_CREATIVE_FEED_[Brand].csv`
