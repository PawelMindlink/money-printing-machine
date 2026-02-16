# Data Dictionary (v3.0 — Anchor-Based Bidding)

> **Single Source of Truth** for all columns in the final output CSV.
> Replaces: `METRIC_DEFINITIONS.md`, `DATA_DICTIONARY_FINAL.md`.

---

## Output Columns (43 — GOLD_STANDARD)

### Core Identifiers

| # | Column | Source | Description |
|---|--------|--------|-------------|
| 1 | `feed_id` | Product Feed `g:id` | Unique product identifier (SKU). |
| 2 | `feed_title` | Product Feed `g:title` | Product name. For non-products: auto-generated from URL slug. |
| 3 | `feed_brand` | Product Feed / Config | Brand name. |
| 4 | `feed_category` | Product Feed `g:google_product_category` | Product category (mapped from feed). |
| 5 | `calc_gross_price` | Calculated | Gross price (PLN). `MIN(feed_price, meta_AOV, GA4_AOV)` for non-products. |
| 6 | `is_product` | Calculated | `TRUE` if entity is a product, `FALSE` for categories/landing pages. |
| 7 | `is_price_inferred` | Calculated | `TRUE` if price was estimated (non-product entities). |
| 8 | `feed_link` | Product Feed `g:link` | Original product URL. |
| 9 | `norm_url` | Calculated | Normalized URL (stripped protocol, domain, params, extensions). |

### Classification (MSC-ALGO Waterfall)

| # | Column | Source | Description |
|---|--------|--------|-------------|
| 10 | `calc_priority` | MSC-ALGO Waterfall | Numeric priority: 1=PROVEN_STAR, 2=PROVEN_COW, 3=LAUNCH, 4=FIX_LP, 5=SCALE_UP, 6=DIRECT_TO_PDP, 7=FEED_DPA, 8=IGNORE. |
| 11 | `calc_segment` | MSC-ALGO | Text label: `PROVEN_STAR`, `PROVEN_COW`, `NEW_STAR_LAUNCH`, `RECOVERY_LAUNCH`, `SCALE_UP`, `DIRECT_TO_PDP`, `FEED_DPA`, `FIX_LANDING_PAGE`, `IGNORE`. |
| 12 | `calc_reason` | MSC-ALGO | Human-readable reason for classification (e.g. "Meta Ads profitable, high volume"). |
| 13 | `calc_is_actionable` | Calculated | `TRUE` if priority ∈ {1–7}. `FALSE` for IGNORE. |
| 14 | `calc_action_type` | Calculated | Campaign action: `SCALE_SPEND`, `MAINTAIN_SPEND`, `NEW_AD_CREATIVES`, `UX_PRICE_AUDIT`, `BROAD_AD_TARGETING`, `CONVERSION_CAMPAIGN`, `CATALOG_ADS_DPA`, `IGNORE`. |
| 15 | `meta_class` | Calculated | Meta Ads classification: `Profitable`, `Unprofitable`, `No Ads`. Based on `calc_contribution_profit`. |
| 16 | `ga4_class` | Calculated | GA4 classification: `Star`, `Cash Cow`, `Hidden Gem`, `Slacker`. Based on organic performance thresholds (P75). |
| 17 | `calc_entity_type` | Calculated | `PRODUCT` or `CATEGORY_OR_AD`. Determines whether item enters product-level analysis. |

### Financial Metrics

| # | Column | Source | Formula | Description |
|---|--------|--------|---------|-------------|
| 18 | `base_gross_margin` | Config (Margin Rules Template) | — | Margin rate (e.g. 0.10 = 10%). From default_rate or category_overrides. |
| 19 | `calc_contribution_profit` | Calculated | `(meta_revenue / (1+VAT)) × margin − meta_spend` | **North Star metric.** Net profit after ad spend. |
| 20 | `calc_price_cluster` | Calculated | Price clustering algorithm | Label: `TOP {max_price} PLN`. Groups products by margin + price proximity (1.5× rule). |
| 21 | `critical_roas` | Calculated | `((1+VAT) / margin) × 1.2` | **Minimum ROAS target.** Break-even + 20% safety buffer for CPA fluctuations. |
| 22 | `scaling_roas` | Calculated | `critical_roas × 1.4` | **Scaling threshold.** Above this → trade efficiency for volume. |
| 23 | `calc_critical_roas` | Alias | `= critical_roas` | Export alias. Previously named `calc_break_even_roas` (renamed v3.0). |
| 24 | `calc_net_price` | Calculated | `calc_gross_price / (1+VAT)` | Price without VAT. |
| 25 | `calc_bid_cap` | Calculated (cluster) | `anchor_price / (1+VAT) × margin` | **Max CPA (hard ceiling).** Based on cluster anchor (highest price). Meta never exceeds this. |
| 26 | `calc_cost_cap` | Calculated (cluster) | `calc_bid_cap × 0.70` | **Target CPA (soft target).** 30% profit reserve. Meta optimizes average cost below this. |
| 27 | `cluster_avg_margin` | Calculated | Mean of `base_gross_margin` within cluster | Average margin for the price cluster. |
| 28 | `calc_roas` | Calculated | `meta_revenue / meta_spend` | **Actual ROAS** from Meta Ads. |

### Efficiency Metrics

| # | Column | Source | Formula | Description |
|---|--------|--------|---------|-------------|
| 29 | `calc_gpps` | Calculated | `GP(LP) / ga4lp_sessions` | Gross Profit Per Session. Key organic efficiency metric. |
| 30 | `calc_cr` | Calculated | `ga4lp_purchases / ga4lp_sessions` | Conversion Rate. |
| 31 | `calc_frequency` | Calculated | `ga4lp_purchases / ga4lp_first_time_purchasers` | Purchase Frequency. Repeat buyer indicator. |
| 32 | `calc_gppv` | Calculated | `GP(Item) / ga4item_views` | Gross Profit Per Item View. Product demand signal. |
| 33 | `arpu` | Calculated | `ga4lp_revenue / ga4lp_users` | Average Revenue Per User. |
| 34 | `arpiv` | Calculated | `ga4item_revenue / ga4item_views` | Average Revenue Per Item View. |

### Meta Ads Data (Raw Performance)

| # | Column | Source | Description |
|---|--------|--------|-------------|
| 35 | `meta_spend` | Meta Ads Export | Total ad spend (PLN) for this URL. |
| 36 | `meta_revenue` | Meta Ads Export | Total purchase conversion value attributed to ads. |
| 37 | `meta_purchases` | Meta Ads Export | Number of purchases attributed to ads. |

### GA4 Data (Organic Performance)

| # | Column | Source | Description |
|---|--------|--------|-------------|
| 38 | `ga4lp_sessions` | GA4 Landing Page | Total sessions on this landing page. |
| 39 | `ga4lp_revenue` | GA4 Landing Page | Total revenue from this landing page. |
| 40 | `ga4lp_purchases` | GA4 Landing Page | Number of purchases on this landing page. |
| 41 | `ga4lp_first_time_purchasers` | GA4 Landing Page | Number of first-time purchasers. |
| 42 | `ga4item_views` | GA4 Item Report | Total item views (product detail page views). |
| 43 | `ga4item_revenue` | GA4 Item Report | Total item revenue. |

---

## Intermediate Columns (Not in Final Output)

These columns exist during pipeline processing but are NOT exported:

| Column | Formula | Used By |
|--------|---------|---------|
| `calc_net_revenue_meta` | `meta_revenue / (1+VAT)` | `calc_contribution_profit` |
| `calc_net_revenue_lp` | `ga4lp_revenue / (1+VAT)` | `calc_gpps` |
| `calc_net_revenue_item` | `ga4item_revenue / (1+VAT)` | `calc_gppv` |
| `calc_gross_profit_meta` | `calc_net_revenue_meta × margin` | `calc_contribution_profit` |
| `calc_gross_profit_lp` | `calc_net_revenue_lp × margin` | `calc_gpps` |
| `calc_gross_profit_item` | `calc_net_revenue_item × margin` | `calc_gppv` |
| `bid_cap` | Cluster-level bid cap (internal) | `calc_bid_cap` |
| `cost_cap` | Cluster-level cost cap (internal) | `calc_cost_cap` |
| `is_price_missing` | `TRUE` if `calc_gross_price == 0` | Price clustering |
| `path_key` | URL path extracted from `feed_link` | SmartMatcher join |

---

## Dynamic Thresholds (P75)

Calculated at runtime from the active dataset. Used in MSC-ALGO Waterfall:

| Threshold | Formula | Used For |
|-----------|---------|----------|
| `P75_VOL_META` | 75th percentile of `meta_revenue` (where > 0) | Meta Ads volume gate |
| `P75_EFF_META` | 75th percentile of `calc_contribution_profit` (where > 0) | Meta Ads efficiency gate |
| `P75_VOL_GA` | 75th percentile of `ga4lp_sessions` (where > 0) | GA4 LP volume gate |
| `P75_EFF_GA` | 75th percentile of `calc_gpps` (where > 0) | GA4 LP efficiency gate |
| `P75_VOL_ITEM` | 75th percentile of `ga4item_views` (where > 0) | GA4 Item volume gate |
| `P75_EFF_ITEM` | 75th percentile of `calc_gppv` (where > 0) | GA4 Item efficiency gate |
| `MIN_ORGANIC_SESSIONS` | `max(50, min(100 / avg_CR, 2000))` | Minimum sessions for statistical significance |

---

## Invariants (Always True)

These relationships must hold for any valid output:

```
calc_bid_cap > calc_cost_cap                    (always)
scaling_roas > critical_roas > break_even_pure  (always)
critical_roas = break_even × 1.2               (20% buffer)
scaling_roas = critical_roas × 1.4             (scaling headroom)
calc_cost_cap = calc_bid_cap × 0.70            (30% profit reserve)
```

---

## Process Scope

| Process | Data | Execution | Status |
|---------|------|-----------|--------|
| **Process 2: Growth Opportunities** | All 43 columns above | n8n → Python API (automated) | ✅ Active |
| **Process 1: Ad Analysis** | Per-product metrics via `ad_analysis.py` | Local script (manual) | ✅ Active, not in n8n |
| **Process 3: Psychography** | `persona_name`, `dreams`, `fears`, `social_proof`, `buying_objections`, `tech_translator` | Local scripts — Personiarz (manual) | 🔧 In development |
