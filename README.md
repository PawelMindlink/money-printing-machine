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

## n8n Integration

Ten projekt wykorzystuje **n8n Atom** do synchronizacji workflowów między tym repozytorium a Twoją instancją n8n.

1. **Workflows**: Wszystkie workflowy znajdują się w folderze `Workflows/`.
2. **Synchronizacja**:
    * Zainstaluj rozszerzenie [n8n Atom](https://www.atom8n.com/) w swoim edytorze.
    * Podłącz folder `Workflows/` do swojej instancji n8n.
    * Każda zmiana w pliku `.n8n` zostanie automatycznie odzwierciedlona w n8n.

### Pierwszy Import

Jeśli nie używasz jeszcze n8n Atom, możesz ręcznie zaimportować plik:
`Workflows/Daily_Report_Workflow.n8n` -> **Import from File** w UI n8n.
