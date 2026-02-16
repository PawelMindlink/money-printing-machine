# SYSTEM ARCHITECTURE

## 1. Data Preparation (Wsad)

The foundation of the Money Printing Machine is the harmonization of three distinct data sources into a single, cohesive dataset.

### Inputs

* **Product Feed (`feed.csv` / XML)**: The source of truth for inventory. Contains SKU, Title, Category, Price, and Links.
* **Meta Ads Export (`meta_ads.csv`)**: Performance data from ad campaigns, aggregated by Ad Link.
* **GA4 Export (`ga4_export.csv`)**: User behavior data (Sessions, Revenue, Purchases) aggregated by Landing Page Path.
* **Configuration (`config.json`)**: Brand-specific settings (VAT rates, Margin restrictions, Account ID).

### Setup

A **Google Service Account** is used to securely authenticate with the GA4 API. The credentials JSON path is injected via environment variables or config, ensuring secure access to granular traffic data without manual exports.

### Standardization

To merge these disparate sources, **URL Normalization** is critical. We strip all non-essential elements to create a common join key:

1. **Protocol Removal**: `https://` and `http://` are removed.
2. **Domain Stripping**: `www.domain.com` is removed, leaving only the path.
3. **Parameter Cleaning**: All query parameters (after `?`) are discarded.
4. **Extension Handling**: `.html`, `.php` are treated consistently.
5. **Trailing Slashes**: Removed to ensure `/product` matches `/product/`.

---

## 2. Data Merging (Scalanie)

### The Join Logic

The central nervous system of the architecture is the **Left Join** on the normalized URL logic.

1. **Base Layer**: The Product Feed. Every active product is a row.
2. **Enrichment 1 (Meta)**: We join Meta Ads data.
    * *Unmatched Ads:* Ads pointing to URLs not in the feed (e.g., Category Pages, Homepage) are captured via an **Outer Join** strategy and labeled as `CATEGORY_OR_AD`.
3. **Enrichment 2 (GA4)**: We join GA4 Landing Page data.
    * *Path Matching:* We use `extract_path(url)` to align Feed Links with GA4 Page Paths.

### Handling Missing Data

* **Synthetic Rows**: If a high-spending ad points to a non-existent feed URL, a "Synthetic Product" row is created to ensure the spend is tracked and optimized.
* **Zero-Filling**: Missing metrics (Spend, Revenue) are filled with 0 to allow mathematical operations.

### The SmartMatcher Cascade (Anti-Fragile Linking)

To solve the "Ghost Product" problem (where Meta URLs don't match Feed URLs exactly), we use a multi-layered **SmartMatcher** logic:

1. **Level 1: Silver Bullet (Product ID)**: Explicitly matches Meta Content IDs with Feed IDs.
2. **Level 2: ID Extractor (The Hero)**: Uses regex to pull numeric SKU IDs (4+ digits) from the URL path (e.g., `/35946-product.html` -> `35946`).
3. **Level 3: Semantic Tokenizer (Fuzzy Match)**: If IDs are missing, the system tokenizes URLs and calculates subset inclusion. If >80% of tokens match, it links the records.

### Safety Valve (Anomaly Detection)

Even with SmartMatcher, some matches might be risky. We implement a **Sanitize Ghost Prices** logic:

* **The Check**: If a product has no Feed ID but has high revenue, it's flagged.
* **Anomaly**: If price > 2.5x the Category Average, the item is considered a "Ghost".
* **Action**: The price is clamped to the Category Average, and the item is marked as `calc_is_actionable = False` to prevent over-bidding.

---

## 3. Business Logic & Account Structure (Obliczenia)

### Price Clustering Algorithm (The Core Logic)

To optimize Meta Ads Bidding, we group products into **Price Clusters**. This allows us to set Bid Caps that are appropriate for a *range* of products, rather than managing thousands of individual bids.

**The Algorithm:**

1. **Split by Margin Group**: Inventory is first divided by `calc_margin_group` (e.g., High Margin vs. Low Margin).
2. **Sort**: Products within a group are sorted by `calc_gross_price` Descending.
3. **Cluster Creation**:
    * The most expensive product becomes the **Leader** of Cluster 1.
    * Subsequent products are added to Cluster 1 **IF**:
        $$MemberPrice \ge \frac{LeaderPrice}{1.5}$$
    * *Logic:* The Leader's price cannot be more than 150% of the cheapest member. This prevents a 1000 PLN product from sharing a bid cap with a 100 PLN product.
4. **Iteration**: If a product fails the check, it becomes the Leader of Cluster 2, and the process repeats.

### Bidding Strategy (v3.0 — Anchor-Based)

Bids are calculated at the **Cluster Level** using the **anchor price** (highest price in the cluster = leader):

1. **Bid Cap (Hard Ceiling)**: Max CPA Meta will NEVER exceed per single conversion.
    $$BidCap = \frac{AnchorPrice}{1 + VAT} \times Margin$$
2. **Cost Cap (Soft Target)**: 30% profit reserve. Meta optimizes average cost to stay at or below this.
    $$CostCap = BidCap \times 0.70$$
3. **Critical ROAS**: Break-even + 20% safety buffer for daily CPA fluctuations.
    $$CriticalROAS = \frac{1 + VAT}{Margin} \times 1.2$$
4. **Scaling ROAS**: Above this, trade efficiency for volume.
    $$ScalingROAS = CriticalROAS \times 1.4$$

*Invariants:* `CostCap < BidCap` and `ScalingROAS > CriticalROAS` (always hold).
*Result:* All products in a cluster receive identical Bid/Cost caps, stabilizing delivery.

### Non-Product Logic

For Landing Pages (Categories) without a single price:

* **Naming**: Titles are auto-generated from URLs (e.g., `domain.com/office-monitors` -> "Office Monitors").
* **Pricing**: A "Conservative Estimation" is used:
    $$Price = MIN(FeedPrice, MetaAOV, GA4AOV)$$

### Campaign Priority (`calc_priority`)

Products are assigned a Priority Label driving the Campaign Structure:

* **P1 (Proven Star)**: High Volume + High Efficiency (Scale Aggressively).
* **P2 (Proven Cow)**: High Efficiency + Moderate Volume (Maintain).
* **P3 (New Star)**: High Organic Traffic + High Potential (Launch Ads).
* **P4 (Fix LP)**: High Traffic + Low Conversion (UX Audit required).
* **Legacy/Deprecation Note**: Variables like `MIN_CONFIDENCE` have been replaced by specific gates:
  * `MIN_META_TRANS` (default 10): Minimum purchases to trust Ad data.
  * `MIN_ORGANIC_SESSIONS` (default 300): Semantic floor for statistical significance.

---

## 4. Feature Extraction (Cechy)

### Tech Translator

Raw specs are converted into Consumer Benefits using a Regex Map (`business_logic_layer.py`).

* *Input:* `165Hz`, `1ms`, `IPS`
* *Regex Match:* `r'\b165Hz\b'` -> "Płynność" (Fluidity)
* *Output:* A "Benefits Tag" used for Copywriting.

### Feature-to-Benefit

We map physical attributes to emotional outcomes:

* `4K Resolution` -> "See every detail" (Function) -> "Dominate the battlefield" (Emotion/Gaming).

---

## 5. Psychographics (Psychografia)

### Voice of Customer (Harvest)

We ingest `Harvest JSONs` containing raw user research (Reviews, Reddit threads, Surveys).

* **Baskets**: Insights are categorized into `PAIN`, `DREAM`, `OBJECTION`.

### The Bridge

The `creative_data_bridge.py` script maps these insights to Products based on **Verticals**:

* A "Gaming Monitor" inherits "Gaming" insights (e.g., "I hate screen tearing").
* An "Office Monitor" inherits "Productivity" insights (e.g., "My eyes hurt after 8 hours").

---

## 6. Creative Briefing (Briefy)

 The system synthesizes data into a structured **Markdown Brief** for the Creative Team (or AI Agent).

* **Sections**:
    ***Avatar**: Who are we talking to? (From Psychographics).
  * **Problem/Agitation**: What hurts them? (From `PAIN` basket).
    ***Solution**: How does this product fix it? (Tech Translator).
  * **Brand Constraints**: "Red Lines" (e.g., "Never use red text") are injected from `BRAND_CONSTRAINTS.md`.

---

## 7. Asset Generation (Generowanie)

### The Matrix

We generate 3 distinct creative variants per brief:

1. **Aesthetic**: High-design, beautiful visuals. Focus on "Desire".
2. **Native**: User-Generated-Content style. Focus on "Trust" and "Authenticity". pattern.
3. **Interrupt**: Bold, high-contrast, "Weird". Focus on "Attention".

### Output

Final assets are organized by SKU and Variation:

* `/Output/Brand/SKU_123/Aesthetic/Copy.txt`
* `/Output/Brand/SKU_123/Aesthetic/Img_Prompt.txt`
