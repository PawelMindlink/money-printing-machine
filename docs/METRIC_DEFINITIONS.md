# Metric Definitions (v2.1 - MECE Update)

## 1. Source Prefixes

All variables now use strict prefixes to indicate their origin:

* `feed_`: Product Feed (Google/Meta XML).
* `ga4lp_`: GA4 Landing Page Report.
* `ga4item_`: GA4 Item Report.
* `meta_`: Meta Ads Export.
* `calc_`: Calculated Metrics.

## 2. Financial Metrics

* **`base_gross_margin`**: Dynamic margin based on Category or Brand default.
* **`calc_net_price`**: `feed_price_numeric / (1 + vat_rate)`.
* **`calc_bid_cap`**: `calc_net_price * base_gross_margin`.
  * *Definition:* The maximum Cost Per Acquisition (CPA) to break even on a single unit.
* **`calc_cost_cap`**: `calc_bid_cap * 0.7`.
  * *Definition:* Target CPA with a 30% safety buffer.
* **`calc_break_even_roas`**: `1 / base_gross_margin`.
  * *Definition:* The ROAS required to cover COGS.
* **`calc_scaling_roas`**: `calc_break_even_roas * 1.2`.
  * *Definition:* The ROAS threshold where scaling becomes safe (20% above break-even).

## 3. MECE Segments (Process 2)

Products are classified into one of 4 mutually exclusive segments based on Traffic (`ga4lp_sessions`) and Efficiency (`calc_arpiv` OR `meta_roas`).

### Quadrant 1: MONEY PRINTER

* **Definition:** High Traffic AND High Efficiency.
* **Action:** **Scale Aggressively**. Push Bid Caps, duplicate Ad Sets.

### Quadrant 2: HIDDEN GEM

* **Definition:** Low Traffic AND High Efficiency.
* **Action:** **Create Traffic**. Launch new Ad Sets, use Cost Caps. The product converts when seen.

### Quadrant 3: BLEEDING STAR

* **Definition:** High Traffic AND Low Efficiency.
* **Action:** **Fix Funnel**. Users are clicking but not buying. Check Price, Offer, or Page Load. Do NOT scale ads.

### Quadrant 4: ZOMBIE

* **Definition:** Low Traffic AND Low Efficiency.
* **Action:** **Ignore**.
