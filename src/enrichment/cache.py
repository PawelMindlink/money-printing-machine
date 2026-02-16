"""
Cache Layer for Enrichment Engine.
Hash-based skip: if product_id + price + category unchanged → reuse previous harvest.
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Optional


class EnrichmentCache:
    """File-based cache for harvest + analysis results."""

    def __init__(self, cache_dir: str = "cache/enrichment", max_age_days: int = 7):
        self.cache_dir = cache_dir
        self.max_age = timedelta(days=max_age_days)
        os.makedirs(cache_dir, exist_ok=True)

    @staticmethod
    def _make_key(product_id: str, price: float, category: str) -> str:
        """Deterministic hash from product identity signals."""
        raw = f"{product_id}|{price:.2f}|{category}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, product_id: str, price: float, category: str) -> Optional[Dict]:
        """Return cached result if fresh, else None."""
        key = self._make_key(product_id, price, category)
        path = self._cache_path(key)

        if not os.path.exists(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)

            cached_date = datetime.fromisoformat(entry.get("harvest_date", "2000-01-01"))
            if datetime.now() - cached_date > self.max_age:
                return None  # Expired

            return entry.get("data")
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def put(self, product_id: str, price: float, category: str, data: Dict) -> None:
        """Store enrichment result."""
        key = self._make_key(product_id, price, category)
        path = self._cache_path(key)

        entry = {
            "product_id": product_id,
            "harvest_date": datetime.now().isoformat(),
            "data": data,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

    def stats(self) -> Dict[str, int]:
        """Return cache stats."""
        if not os.path.exists(self.cache_dir):
            return {"total": 0, "fresh": 0, "expired": 0}

        total = 0
        fresh = 0
        for fname in os.listdir(self.cache_dir):
            if fname.endswith(".json"):
                total += 1
                try:
                    with open(os.path.join(self.cache_dir, fname), "r") as f:
                        entry = json.load(f)
                    cached_date = datetime.fromisoformat(entry.get("harvest_date", "2000-01-01"))
                    if datetime.now() - cached_date <= self.max_age:
                        fresh += 1
                except Exception:
                    pass

        return {"total": total, "fresh": fresh, "expired": total - fresh}
