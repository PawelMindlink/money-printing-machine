---
description: Run the MSC-ALGO Pipeline for all brands
---

This workflow executes the complete end-to-end data fetching and margin clustering pipeline. It fetches the latest Google Analytics 4 data (with automatic pagination and Query String stripping), merges it with the product feeds and Meta Ads reports, and generates the final Growth Opportunities CSVs.

// turbo-all

1. Clean up old leftover files and test scripts
Remove any tracked/untracked test data left in the root directory before running.

```bash
if (Test-Path -Path .\diagnose_zeros.py) { Move-Item .\diagnose_zeros.py .\.archive_tests\ -Force }
if (Test-Path -Path .\test_ga4_pagination.py) { Move-Item .\test_ga4_pagination.py .\.archive_tests\ -Force }
if (Test-Path -Path .\test_ga4_single_path.py) { Move-Item .\test_ga4_single_path.py .\.archive_tests\ -Force }
```

1. Run the complete pipeline for Koszulkowy
Run the following command to process Koszulkowy and fetch GA4 data via API:

```bash
python src/complete_pipeline.py Koszulkowy
```

1. Run the complete pipeline for Iiyama
Run the following command to process Iiyama and fetch GA4 data via API:

```bash
python src/complete_pipeline.py Iiyama
```

1. Verify Output Files
Verify that the output files were created successfully in `Output/Koszulkowy` and `Output/Iiyama`.

```bash
Get-ChildItem -Path Output\* -Recurse -Filter *_Growth_Opportunities.csv
```
