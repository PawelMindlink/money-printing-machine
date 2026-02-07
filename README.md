# Money Printing Machine 🖨️💸

**Automated Marketing Intelligence System**

## Overview

This system processes e-commerce data (GA4, Meta Ads, Product Feeds) to autonomously classify products into strategic tiers (P1-P8) and allocate advertising budgets.

## Setup

1. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2. **Add Data**:
    Place data in `Input/{Brand}/`:
    * `product_feed.xml`
    * `ga4_items.csv`
    * `meta_ads.csv`

3. **Run Pipeline**:

    ```bash
    python src/ingest_normalized.py
    python src/join_datasets.py
    python src/calculate_metrics.py
    ```

## Architecture

See `PROJECT_ARCHITECTURE.md` (in docs/artifacts) for details on the Hybrid Python + n8n setup.
