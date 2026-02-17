# N8N Workflow Documentation

> [!WARNING]
> **DEPRECATED** — This file describes the legacy v1/v2 CLI-based workflow.
> Current documentation: [Workflows/MSC_ALGO_v5_Hybrid.md](../Workflows/MSC_ALGO_v5_Hybrid.md)

## Legacy Overview (v1/v2)

The original pipeline was triggered manually via n8n but executed Python scripts via `Execute Command` nodes.

This architecture was replaced in v5 with a hybrid approach:

- **n8n** handles data ingestion (Feed, GA4, Meta Ads) and I/O
- **Python API** (`main.py`) handles joining, classification, and business logic
- Communication via HTTP POST to `/process` endpoint

See [MSC_ALGO_v5_Hybrid.md](../Workflows/MSC_ALGO_v5_Hybrid.md) for current documentation.
