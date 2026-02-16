"""
Enrichment Engine — Process 3: Qualitative Data Layer
Adds 10 psychographic columns to MSC-ALGO's 43 quantitative columns.

Pipeline: Growth_Opportunities.csv → Enriched_Products.csv
"""

from .enrichment_engine import EnrichmentEngine

__all__ = ["EnrichmentEngine"]
