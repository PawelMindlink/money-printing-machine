# N8N Workflow Documentation

## Overview

The "Money Printing Machine" pipeline is triggered manually via n8n but executes Python scripts for the heavy lifting.

## Workflow Structure

1. **Manual Trigger**: Starts the flow.
2. **Set Brands**: Defines the brands to process (JSON Array: `[{ brand: "Bushido"}, { brand: "Iiyama" }]`).
3. **Pipeline Engine**:
    - **Node Type**: Execute Command
    - **Command**: `python src/complete_pipeline.py {{ $json.brand }}`
    - **Action**: Runs the data ingestion, joining, and classification logic for each brand.
4. **Summary Engine**:
    - **Node Type**: Execute Command
    - **Command**: `python src/summary_engine.py`
    - **Action**: Aggregates results from all brands into `Output/GLOBAL_SUMMARY.md`.

## Local Execution (No n8n)

To run the same logic without n8n, use the `master_runner.py` script:

```powershell
python src/master_runner.py
```

This script replicates the n8n behavior by iterating through clients defined in `business_logic.json`.

## Configuration

- **Business Logic**: `business_logic.json` controls margins, VAT, and active clients.
- **Credentials**: `GA4_CREDS_PATH` env var or hardcoded path in `complete_pipeline.py`.
