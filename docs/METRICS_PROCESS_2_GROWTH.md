# Metric Definitions: Process 2 (Growth Opportunities)

**Purpose:** Identify growth segments by triangulating Paid Traffic (Meta), User Behavior (GA4 LP), and Product Desire (GA4 Item).
**File:** `Output/[Brand]/[Brand]_Growth_Opportunities.csv`

## 1. The 3 Data Dimensions

### A. Paid Traffic (Cost)

* **`meta_spend`**: How much we pushed this product.
* **`meta_roas`**: Reported efficiency of that push.

### B. Landing Page (Traffic Volume)

* **`ga4lp_sessions`**: Total sessions landing on this product page (Paid + Organic).
* **`ga4lp_purchases`**: Total transactions realized on this page.
* **`ga4lp_revenue`**: Total revenue from this page.

### C. Item (User Desire)

* **`ga4item_views`**: How many times users viewed the specific product details. *Key proxy for "Interest".*
* **`ga4item_purchases`**: How many times this specific item was bought.
* **`calc_arpiv`**: `ga4item_revenue / ga4item_views`. Average Revenue Per Item View. Measures "Desire Efficiency".

## 2. Calculated Segments (`calc_segment`)

We categorize products based on **Funnel Health** rather than just "Traffic".

| Segment Code | Logic Definition | Business Meaning | Recommended Action |
| :--- | :--- | :--- | :--- |
| **SCALER** | `meta_roas > Scaling ROAS` OR `calc_contribution_profit > 0` | The machine works. It prints money. | **Scale Aggressively** (Bid Caps) |
| **HIDDEN GEM** | `ga4item_views > High` AND `meta_spend < Low` | Users are looking for this organically, but we aren't advertising it. | **Launch Ads** (Cost Caps) |
| **OFFER PROBLEM** | `ga4item_views > High` AND `ga4item_purchases < Low` (Low Conversion Rate on high interest) | People want the *item* (they look), but refuse the *offer* (price, shipping, trust). | **Fix Offer/Price** (Don't just buy more ads) |
| **TRAFFIC PROBLEM** | `meta_spend > High` AND `ga4item_views < Low` (vs Spend) | We pay for clicks, but they don't reach the product (Bounce on LP, Misleading Ad). | **Fix Creative/LP Alignment** |
| **ZOMBIE** | `ga4item_views < Low` AND `meta_spend < Low` | No interest, no ads. Dead stock. | **Ignore / Liquidate** |
| **BURNER** | `meta_spend > High` AND `meta_roas < BreakEven` AND `ga4item_views > High` | We pay, they look, they don't buy. A "Bleeding Star". | **Pause Ads & Fix Funnel** |

*(Note: Thresholds for "High/Low" are dynamic based on account quantiles, defaults: Spend > 50 PLN, Views > Median)*
