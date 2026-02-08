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

## 2. MSC-ALGO Priorities (`calc_priority`)

We prioritize products based on a **Waterfall Model** (Hierarchy of Proof).

| Priority | Name | Logic |
| :--- | :--- | :--- |
| **1** | **PROVEN STAR** | High Meta Profit (`calc_contribution_profit > 0`) & High Volume (`meta_revenue >= P75`). |
| **2** | **PROVEN CASH COW** | High Meta Profit (`calc_contribution_profit > 0`) & Moderate Volume. |
| **3** | **ORGANIC STAR** / **RE-LAUNCH** | High Organic Potential (`ga4lp_sessions >= P75` & `calc_gpps >= P75`). |
| **4** | **HIGH TRAFFIC / LOW CONV** | High `ga4lp_sessions`, but low efficiency (Offer/LP problem). |
| **5** | **HIGH CONV / LOW TRAFFIC** | Low `ga4lp_sessions`, but high efficiency (`calc_gpps`). |
| **6** | **HIDDEN STAR** | High `ga4item_views` & `calc_gppv`, but no LP traffic. |
| **7** | **HIDDEN GEM** | Moderate `ga4item_views`, but high efficiency (`calc_gppv`). |
| **8** | **IGNORE** | Low activity / Insignificant data. |

*(Note: Thresholds for P75 (Top 25%) are calculated dynamically per client.)*
