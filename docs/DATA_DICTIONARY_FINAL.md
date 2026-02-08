# Data Dictionary (Final Output)

This document describes the columns present in the final output file (e.g., `Iiyama_Growth_Opportunities.csv`).

## Core Identifiers

| Column | Source | Description |
| :--- | :--- | :--- |
| **feed_id** | Product Feed (`g:id`) | Unique Product Identifier. |
| **feed_title** | Product Feed (`g:title`) | Name of the product (or Ad Name for synthetic items). |
| **feed_brand** | Product Feed / Config | Brand name. |
| **feed_category** | Product Feed | Product category (Mapped from `g:google_product_category` or `g:product_type`). |
| **feed_price_numeric** | Product Feed (`g:price`) | Numeric price value (e.g., `1200.0`). |
| **is_product** | Calculated | `TRUE` if entity is a product, `FALSE` for categories/ads. |

## Logic & Classification

| Column | Source | Description |
| :--- | :--- | :--- |
| **calc_priority** | MSC-ALGO | Numeric priority (1=PROVEN_STAR, 2=PROVEN_COW, 3=LAUNCH, 5=SCALE_UP, 6=DIRECT_TO_PDP, 7=FEED_DPA, 8=IGNORE, 99=FIX_LP). |
| **calc_segment** | MSC-ALGO | Text label: `PROVEN_STAR`, `PROVEN_COW`, `NEW_STAR_LAUNCH`, `RECOVERY_LAUNCH`, `SCALE_UP`, `DIRECT_TO_PDP`, `FEED_DPA`, `FIX_LANDING_PAGE`, `IGNORE`. |
| **meta_class** | Calculated | `Profitable`, `Unprofitable`, `No Ads`. Based on Contribution Profit. |
| **ga4_class** | Calculated | `Star`, `Cash Cow`, `Hidden Gem`, `Slacker`. Based on organic performance thresholds. |

## Financial Metrics

| Column | Source | Description |
| :--- | :--- | :--- |
| **base_gross_margin** | Config (`business_logic.json`) | Gross margin rate (e.g., 0.45 = 45%). |
| **calc_contribution_profit** | Calculated | `(MetaRev / (1+VAT) * Margin) - MetaSpend`. The "North Star" metric. |
| **calc_bid_cap** | Calculated | `Price / (1+VAT) * Margin`. Max CPA to break even. |
| **calc_cost_cap** | Calculated | `BidCap * 0.7`. Recommended Cost Cap setting (30% safety buffer). |
| **critical_roas** | Calculated | `1 / BidCap`. Minimum ROAS to be profitable. |
| **scaling_roas** | Calculated | `BreakEvenROAS * 1.2`. Target ROAS for scaling. |
| **calc_break_even_roas** | Calculated | `1 / Margin`. Minimum ROAS to break even. |
| **calc_roas** | Calculated | `meta_revenue / meta_spend`. Actual ROAS from Meta Ads. |

## Efficiency Metrics

| Column | Source | Description |
| :--- | :--- | :--- |
| **calc_gpps** | Calculated | `GrossProfit(LP) / Sessions`. Gross Profit Per Session. |
| **calc_cr** | Calculated | `Purchases / Sessions`. Conversion Rate. |
| **calc_frequency** | Calculated | `Purchases / FirstTimePurchasers`. Purchase Frequency. |
| **calc_gppv** | Calculated | `GrossProfit(Item) / ItemViews`. Gross Profit Per View. |
| **arpu** | Calculated | `Revenue / Users`. Average Revenue Per User. |
| **arpiv** | Calculated | `ItemRevenue / ItemViews`. Average Revenue Per Item View. |

## Meta Ads Data

| Column | Source | Description |
| :--- | :--- | :--- |
| **meta_spend** | Meta Ads CSV | Total ad spend for this URL. |
| **meta_revenue** | Meta Ads CSV | Total purchase conversion value attributed to ads. |
| **meta_purchases** | Meta Ads CSV | Number of purchases attributed to ads. |

## GA4 Performance

| Column | Source | Description |
| :--- | :--- | :--- |
| **ga4lp_sessions** | GA4 API/CSV | Total sessions on this landing page. |
| **ga4lp_revenue** | GA4 API/CSV | Total revenue from this landing page. |
| **ga4lp_purchases** | GA4 API/CSV | Number of purchases/transactions on this landing page. |
| **ga4lp_first_time_purchasers** | GA4 API/CSV | Number of first-time purchasers. |
| **ga4item_views** | GA4 API/CSV | Total item views (product detail page views). |
| **ga4item_revenue** | GA4 API/CSV | Total item revenue. |
