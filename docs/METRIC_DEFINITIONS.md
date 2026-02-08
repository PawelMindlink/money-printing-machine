# Metric Definitions

This document defines the key financial and performance metrics used in the Money Printing Machine pipeline.

## Financial Metrics

### 1. Contribution Profit (CP)

The core metric for determining ad profitability. It represents the profit remaining after covering the cost of goods sold (COGS), VAT, and Ad Spend.

**Formula:**

```python
Net Revenue = Meta Revenue / (1 + VAT Rate)
Gross Profit = Net Revenue * Gross Margin * Frequency
Contribution Profit = Gross Profit - Meta Ad Spend
```

- **Meta Revenue**: `Purchases Conversion Value` from Meta Ads.
- **VAT Rate**: Configured per brand (e.g., 23% = 0.23).
- **Gross Margin**: Configured per product category in `business_logic.json`.
- **Frequency**: Calculated multiplier to account for potential upsells/repeat purchases (defaults to Purchase/FirstTimePurchase ratio).
- **Meta Ad Spend**: `Amount Spent` from Meta Ads.

### 2. Frequency

A multiplier indicating how many times, on average, a customer purchases.
**Formula:** `Total Purchases / First Time Purchasers`
*(Derived from GA4 Data)*

## Classifications

### Meta Class

- **Profitable**: CP > 0
- **Unprofitable**: CP <= 0
- **No Ads**: Ad Spend is 0 or missing.

### GA4 Class (Organic/Total Performance)

Items are classified based on their organic activity (Sessions) and conversion performance (Transactions & ARPU).

1. **Slacker**: Low traffic (Sessions < 25th percentile) OR Low Performance (Low Transactions and Low ARPU). Effectively "Everything Else".
2. **Stars**: High Transactions (Top 25%) AND High ARPU (Top 25%).
3. **Cash Cows**: High Transactions (Top 25%) but Lower ARPU.
4. **Hidden Gems**: Low Transactions but High ARPU (Top 25%).

## Priority Groups (P-Class)

Combining Meta and GA4 performance to determine action.

| Priority | GA4 Class | Meta Class | Action |
| :--- | :--- | :--- | :--- |
| **P1** | Star | Profitable | **Scale Aggressively** |
| **P2** | Cash Cow | Profitable | **Scale / Optimization** |
| **P3** | Hidden Gem (or Slacker) | Profitable | **Scale** (Profit validates potential) |
| **P4** | Star | No Ads/Unprofitable | **Launch Ads / Fix Ads** |
| **P5** | Cash Cow | No Ads/Unprofitable | **Launch Ads / Fix Ads** |
| **P6** | Hidden Gem | No Ads | **Launch Ads** |
| **P8** | Slacker | Any | **Ignore / Monitor** |

## Bidding & ROAS Metrics (New)

| Metric | Formula | Purpose |
| :--- | :--- | :--- |
| **Bid Cap** | `Price / (1+VAT) * Margin` | Maximum allowable CPA to break even. |
| **Cost Cap** | `Bid Cap * 0.7` | Recommended target CPA (includes 30% safety buffer). |
| **Critical ROAS** | `1 / Bid Cap` | Minimum ROAS required for profitability. |
| **Scaling ROAS** | `1 / ((1+VAT) * Margin * Frequency)` | Target ROAS for profitable scaling. |
| **ARPIV** | `Item Revenue / Items Viewed` | Average Revenue Per Item View (Visual Merchandising potential). |
| **IsProduct** | URL Pattern Match | `TRUE` if URL is a product page, `FALSE` for categories/home. |
