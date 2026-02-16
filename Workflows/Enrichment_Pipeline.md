# Enrichment Pipeline (Process 3) — Workflow Documentation

> **Twin Documentation** for `Enrichment_Pipeline.json` (per n8n-architect RULE 4)

## Business Logic

**Input** → `Output/{Brand}/{Brand}_Growth_Opportunities.csv` (34 cols from MSC-ALGO)
**Output** → `Output/{Brand}/{Brand}_Enriched_Products.csv` (34 + 10 = 44 cols)

## Node Map

```
Manual Trigger → Discover Brands → Load Config → Read Growth CSV → Filter Actionable
    → Split In Batches → Check Cache → Cache Router
        ├─ [hit]  → Collect Cached ───────────────────────────┐
        └─ [miss] → Perplexity: Reviews ─┐                    │
                    Perplexity: Category ─┤                    │
                                  Merge Harvest                │
                                  Extract Harvest Data         │
                                  Claude: Analyze              │
                                  Parse Analysis               │
                                  Update Cache ────────────────┤
                                                               └→ Merge All Results
                                                                   → Write Enriched CSV

Error Trigger → Log Error (separate track)
```

## 10 Enrichment Columns

| Column | Source | Description |
|--------|--------|-------------|
| `persona_name` | Claude | Persona label (e.g. "Pro Gamer") |
| `persona_dream` | Claude | #1 dream outcome |
| `persona_fear` | Claude | #1 fear/pain point |
| `persona_awareness` | Claude | Awareness level classification |
| `tech_translator` | Claude | Feature → Benefit pairs |
| `social_proof_quote` | Claude + Perplexity | Strongest user quotes |
| `competitive_edge` | Claude | Why THIS product wins |
| `visual_hook_suggestion` | Claude | What to zoom/circle in Meta Ad |
| `buying_objections` | Claude | Top hesitation reasons |
| `harvest_date` | System | Date of enrichment |

## Key Design Decisions

1. **Auto-discovery**: `Discover Brands` scans `Output/*/` — no manual brand input
2. **Cache**: Hash-based (product_id + price + category), 7-day expiry, brand-specific dirs
3. **APIs**: Perplexity (sonar) for research, Claude Sonnet for analysis — keys via `$env`
4. **Separation**: Completely independent from MSC-ALGO workflow — won't break it
