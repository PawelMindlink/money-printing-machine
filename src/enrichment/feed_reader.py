"""
Feed Reader — XML Product Feed Parser (Tech Translator Source of Truth).
Migrated from Personiarz without modification — this module is stable.

Reads g:description, g:title, g:product_type from Google Shopping RSS feed.
Also parses SEO keywords from product URL slugs.
"""

import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from typing import Dict, List, Optional


class FeedReader:
    """Parses Google Shopping XML feed + URL slugs for product specs."""

    def __init__(self, feed_path: str):
        self.feed_path = feed_path
        self.products: Dict[str, Dict] = {}
        self._loaded = False

    def _load_feed(self):
        """Parse XML feed once and cache all products by ID."""
        if self._loaded:
            return

        if not os.path.exists(self.feed_path):
            print(f"[FEED_READER] WARNING: Feed file not found: {self.feed_path}")
            self._loaded = True
            return

        ns = {"g": "http://base.google.com/ns/1.0"}

        print(f"[FEED_READER] Loading feed: {self.feed_path}...")
        try:
            tree = ET.parse(self.feed_path)
            root = tree.getroot()

            for item in root.iter("item"):
                prod_id = self._get_text(item, "g:id", ns)
                if not prod_id:
                    continue

                product_types = []
                for pt in item.findall("g:product_type", ns):
                    if pt.text:
                        product_types.append(pt.text.strip())

                self.products[prod_id] = {
                    "title": self._get_text(item, "g:title", ns),
                    "description": self._get_text(item, "g:description", ns),
                    "product_types": product_types,
                    "shipping_weight": self._get_text(item, "g:shipping_weight", ns),
                }

            print(f"[FEED_READER] Loaded {len(self.products)} products from feed.")
            self._loaded = True

        except Exception as e:
            print(f"[FEED_READER] ERROR parsing feed: {e}")
            self._loaded = True

    @staticmethod
    def _get_text(item, tag, ns) -> str:
        """Extract text from XML element, handling CDATA."""
        el = item.find(tag, ns)
        if el is not None and el.text:
            return el.text.strip()
        return ""

    def get_product_specs(self, product_id: str) -> Dict:
        """
        Get product specs for Tech Translator.

        Returns dict with: title, description, product_types, shipping_weight.
        Returns empty dict if product not found.
        """
        self._load_feed()

        product_id = str(product_id).strip()

        if product_id in self.products:
            return self.products[product_id]

        # Try fuzzy match (stripped whitespace)
        for pid in self.products:
            if pid.strip() == product_id:
                return self.products[pid]

        return {}

    def get_all_ids(self) -> List[str]:
        """Return all product IDs in the feed."""
        self._load_feed()
        return list(self.products.keys())

    @staticmethod
    def parse_url_specs(url: str) -> str:
        """
        Extract SEO-embedded product features from URL slug.

        Example:
        'https://dbxbushido.de/product-ger-3574-160-cm-60-kg-Boxsack-Naturleder.html'
        → '160 cm 60 kg Boxsack Naturleder'
        """
        if not url:
            return ""

        try:
            parsed = urlparse(unquote(url))
            path = parsed.path

            slug = path.split("/")[-1]

            # Remove file extensions and tracking suffixes
            slug = re.sub(r"\.(html|php|htm|asp)$", "", slug, flags=re.IGNORECASE)
            slug = re.sub(r"\.(facebookads|googleads)$", "", slug, flags=re.IGNORECASE)

            # Remove common prefixes like 'product-ger-3574-'
            slug = re.sub(
                r"^product-(ger|pol|eng|fra|deu|ita|esp)-\d+-",
                "",
                slug,
                flags=re.IGNORECASE,
            )

            # Remove pure numeric IDs (EAN/GTIN at end)
            slug = re.sub(r"-\d{10,}$", "", slug)

            features_text = slug.replace("-", " ").strip()
            features_text = re.sub(r"\s+", " ", features_text)

            return features_text
        except Exception:
            return ""
