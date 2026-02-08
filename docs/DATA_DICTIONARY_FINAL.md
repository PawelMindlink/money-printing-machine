# Data Dictionary (Final Output)

This document describes the columns present in the final output file (e.g., `Iiyama_Landing_Page_Final.csv`).

## Core Identifiers

| Column | Source | Description |
| :--- | :--- | :--- |
| **id** | Product Feed (`g:id`) | Unique Product Identifier. |
| **title** | Product Feed (`g:title`) | Name of the product (or Ad Name for synthetic items). |
| **brand** | Product Feed / Config | Brand name. |
| **category** | Product Feed | Product category (Mapped from `g:google_product_category` or `g:product_type`). |
| **price** | Product Feed (`g:price`) | Raw price string (e.g., "1200 PLN"). |
| **is_product** | Calculated | `TRUE` if URL pattern matches a product page, `FALSE` otherwise. |

## Logic & Classification

| Column | Source | Description |
| :--- | :--- | :--- |
| **priority** | Calculated | Final Action Priority (P1-P8). Determines if we scale, fix, or ignore. |
| **meta_class** | Calculated | `Profitable`, `Unprofitable`, `No Ads`. Based on Contribution Profit. |
| **ga4_class** | Calculated | `Star`, `Cash Cow`, `Hidden Gem`, `Slacker`. Based on organic performance. |
| **price_cluster** | Calculated | `TOP X PLN`. Groups products into price tiers within their margin group. |
| **gross_margin** | Config (`business_logic.json`) | Estimated gross margin rate based on category/title overrides. |

## Financial Metrics

| Column | Source | Description |
| :--- | :--- | :--- |
| **contribution_profit** | Calculated | `(MetaRev / (1+VAT) * Margin * Frequency) - MetaSpend`. The "North Star" metric. |
| **bid_cap** | Calculated | `Price / (1+VAT) * Margin`. Max CPA to break even. |
| **cost_cap** | Calculated | `BidCap * 0.7`. Recommended Cost Cap setting (30% safety buffer). |
| **critical_roas** | Calculated | `1 / BidCap`. Minimum ROAS to be profitable. |
| **scaling_roas** | Calculated | `1 / ((1+VAT) * Margin * Frequency)`. Target ROAS for scaling. |
| **meta_spend** | Meta Ads CSV | Total ad spend for this URL. |
| **meta_revenue** | Meta Ads CSV | Total purchase conversion value attributed to ads. |
| **meta_purchases** | Meta Ads CSV | Number of purchases attributed to ads. |
| **arpu** | Calculated | `Revenue / Users`. Average Revenue Per User. |
| **arpiv** | Calculated | `Item Revenue / Items Viewed`. Revenue per product view (independent of LP traffic). |
| **calc_frequency** | Calculated | `Purchases / First Time Purchasers`. Average purchases per customer. |

## GA4 Performance

| Column | Source | Description |
| :--- | :--- | :--- |
| **Sessions** | GA4 API/CSV | Total sessions on this landing page. |
| **Users** | GA4 API/CSV | Total Active Users on this landing page. |
| **Purchases** | GA4 API/CSV | Total purchases (Organic + Paid). |
| **Purchase revenue** | GA4 API/CSV | Total revenue (Organic + Paid). |

## Technical / Debug

| Column | Source | Description |
| :--- | :--- | :--- |
| **link** | Product Feed | Original Product URL. |
| **image_link** | Product Feed | URL to product image. |
| **gtin** | Product Feed | Global Trade Item Number. |
| **mpn** | Product Feed | Manufacturer Part Number. |
