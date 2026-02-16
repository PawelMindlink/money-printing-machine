#!/usr/bin/env python3
"""
Enrichment Engine — Process 3: Qualitative Data Layer.

Takes Growth_Opportunities.csv (43 quantitative columns from MSC-ALGO)
and produces Enriched_Products.csv (43 quant + 10 qualitative columns).

Usage:
    python -m src.enrichment.enrichment_engine --input Output/Brand/Growth_Opportunities.csv
    python -m src.enrichment.enrichment_engine --input Output/Brand/Growth_Opportunities.csv --feed Input/Brand/feed.xml
    python -m src.enrichment.enrichment_engine --input Output/Brand/Growth_Opportunities.csv --no-cache
"""

import argparse
import os
import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.enrichment.harvester import Harvester
from src.enrichment.analyst import Analyst
from src.enrichment.feed_reader import FeedReader
from src.enrichment.cache import EnrichmentCache


# Qualitative columns added by this engine
ENRICHMENT_COLS = [
    "persona_name",
    "persona_dream",
    "persona_fear",
    "persona_awareness",
    "tech_translator",
    "social_proof_quote",
    "competitive_edge",
    "visual_hook_suggestion",
    "buying_objections",
    "harvest_date",
]


class EnrichmentEngine:
    """
    Orchestrator: Growth_Opportunities.csv → Enriched_Products.csv.

    Pipeline per product:
    1. Check cache (skip if fresh)
    2. Harvest (Perplexity/Google) — internet research
    3. Analyze (Claude Sonnet) — synthesize into 10 columns
    4. Quality gate (validate JSON completeness)
    5. Cache result
    """

    def __init__(
        self,
        feed_path: Optional[str] = None,
        cache_dir: str = "cache/enrichment",
        use_cache: bool = True,
        max_cache_age_days: int = 7,
    ):
        self.harvester = Harvester()
        self.analyst = Analyst()
        self.feed_reader = FeedReader(feed_path) if feed_path else None
        self.cache = EnrichmentCache(cache_dir, max_cache_age_days) if use_cache else None

        if self.cache:
            stats = self.cache.stats()
            print(f"[ENGINE] Cache: {stats['fresh']} fresh / {stats['total']} total entries")

    def enrich(self, input_csv: str, output_csv: Optional[str] = None) -> str:
        """
        Main entry point. Enriches a Growth_Opportunities CSV.

        Args:
            input_csv: Path to Growth_Opportunities.csv
            output_csv: Path for output (default: same dir, Enriched_Products.csv)

        Returns:
            Path to the output CSV
        """
        print(f"\n{'='*60}")
        print(f"  ENRICHMENT ENGINE — Process 3")
        print(f"  Input:  {input_csv}")
        print(f"{'='*60}\n")

        # Load input
        df = pd.read_csv(input_csv)
        total = len(df)
        print(f"[ENGINE] Loaded {total} rows from {input_csv}")

        # Filter: only actionable products (priority 1-7)
        if "calc_is_actionable" in df.columns:
            actionable_mask = df["calc_is_actionable"] == True
            actionable_count = actionable_mask.sum()
            print(f"[ENGINE] Actionable products: {actionable_count} / {total}")
        else:
            actionable_mask = pd.Series([True] * total)
            actionable_count = total
            print("[ENGINE] No calc_is_actionable column — processing all rows")

        # Initialize enrichment columns
        for col in ENRICHMENT_COLS:
            if col not in df.columns:
                df[col] = ""

        # Process each actionable product
        enriched = 0
        cached = 0
        failed = 0
        start_time = time.time()

        for idx in df[actionable_mask].index:
            row = df.loc[idx]
            product_id = str(row.get("feed_id", idx))
            product_name = str(row.get("feed_title", f"Product {product_id}"))
            category = str(row.get("feed_category", ""))
            price = float(row.get("calc_gross_price", 0))
            feed_link = str(row.get("feed_link", ""))

            progress = f"[{enriched + cached + failed + 1}/{actionable_count}]"
            print(f"\n{progress} Processing: {product_name[:60]}...")

            # 1. Check cache
            if self.cache:
                cached_result = self.cache.get(product_id, price, category)
                if cached_result:
                    print(f"  ✓ Cache hit")
                    for col in ENRICHMENT_COLS:
                        if col in cached_result:
                            df.at[idx, col] = cached_result[col]
                    cached += 1
                    continue

            # 2. Harvest
            try:
                harvest_data = self.harvester.harvest(product_name, category)
            except Exception as e:
                print(f"  ✗ Harvest failed: {e}")
                failed += 1
                continue

            # 3. Get feed specs (for Tech Translator)
            feed_specs = None
            url_specs = ""
            if self.feed_reader:
                feed_specs = self.feed_reader.get_product_specs(product_id)
            if feed_link:
                url_specs = FeedReader.parse_url_specs(feed_link)

            # 4. Analyze (LLM)
            try:
                analysis = self.analyst.analyze(
                    product_name=product_name,
                    category=category,
                    harvest_data=harvest_data,
                    feed_specs=feed_specs,
                    url_specs=url_specs,
                )
            except Exception as e:
                print(f"  ✗ Analysis failed: {e}")
                failed += 1
                continue

            # 5. Quality gate
            filled_count = sum(1 for v in analysis.values() if v)
            if filled_count < 3:
                print(f"  ⚠ Low quality: only {filled_count}/9 fields filled")

            # 6. Write to dataframe
            analysis["harvest_date"] = datetime.now().strftime("%Y-%m-%d")
            for col in ENRICHMENT_COLS:
                if col in analysis:
                    df.at[idx, col] = analysis[col]

            # 7. Cache
            if self.cache:
                self.cache.put(product_id, price, category, analysis)

            enriched += 1

            # Rate limiting between products
            time.sleep(0.5)

        # Summary
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"  ENRICHMENT COMPLETE")
        print(f"  Enriched: {enriched} | Cached: {cached} | Failed: {failed}")
        print(f"  Time: {elapsed:.1f}s ({elapsed/max(enriched+cached+failed, 1):.1f}s/product)")
        print(f"{'='*60}")

        # Save output
        if output_csv is None:
            input_dir = os.path.dirname(input_csv)
            output_csv = os.path.join(input_dir, "Enriched_Products.csv")

        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        print(f"\n[ENGINE] Output saved: {output_csv}")
        print(f"[ENGINE] Columns: {len(df.columns)} (43 quant + {len(ENRICHMENT_COLS)} qual)")

        return output_csv


def main():
    parser = argparse.ArgumentParser(description="Enrichment Engine — Process 3")
    parser.add_argument("--input", required=True, help="Path to Growth_Opportunities.csv")
    parser.add_argument("--output", default=None, help="Output path (default: Enriched_Products.csv)")
    parser.add_argument("--feed", default=None, help="Path to product feed XML (for Tech Translator)")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache, re-harvest everything")
    parser.add_argument("--cache-dir", default="cache/enrichment", help="Cache directory")
    parser.add_argument("--cache-age", type=int, default=7, help="Max cache age in days")

    args = parser.parse_args()

    engine = EnrichmentEngine(
        feed_path=args.feed,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        max_cache_age_days=args.cache_age,
    )

    engine.enrich(args.input, args.output)


if __name__ == "__main__":
    main()
