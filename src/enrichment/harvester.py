"""
Harvester — Internet Research via Perplexity/Google APIs.
Refactored from Personiarz with .env integration and 2-stream architecture.

Stream 1: Product-specific reviews (social proof, buying objections)
Stream 2: Category-level psychology (dreams, fears, motivations)
"""

import os
import requests
import json
import time
from typing import Dict, List, Optional


class Harvester:
    """Dual-stream internet research for product psychographics."""

    def __init__(self):
        """Load API keys from environment (.env via load_dotenv)."""
        self.perplexity_key = os.getenv("PERPLEXITY_API_KEY", "")
        self.google_key = os.getenv("GOOGLE_SEARCH_API_KEY", "")
        self.google_cx = os.getenv("GOOGLE_SEARCH_CX", "")

        if self.perplexity_key:
            print("[HARVESTER] Perplexity API configured ✓")
        elif self.google_key:
            print("[HARVESTER] Google Search API configured ✓")
        else:
            print("[HARVESTER] WARNING: No API keys found. Will use mock mode.")

    def harvest(self, product_name: str, category: str) -> Dict[str, str]:
        """
        Dual-stream harvest for a single product.

        Returns:
            dict with keys: product_reviews, category_insights, source
        """
        if self.perplexity_key:
            return self._harvest_perplexity(product_name, category)
        elif self.google_key:
            return self._harvest_google(product_name, category)
        else:
            return self._harvest_mock(product_name, category)

    # --- Perplexity (Primary) ---

    def _harvest_perplexity(self, product_name: str, category: str) -> Dict:
        """Dual-stream Perplexity harvest with rate limiting."""

        # STREAM 1: Product-specific reviews
        prompt_product = (
            f"Znajdź opinie, recenzje i komentarze użytkowników o produkcie: {product_name}. "
            f"Szukam POZYTYWNYCH cytatów, doświadczeń, i konkretnych opinii. "
            f"Jeśli nie znajdziesz informacji o tym konkretnym produkcie, napisz: "
            f"'Brak danych o tym konkretnym produkcie.'"
        )
        product_result = self._ask_perplexity(prompt_product, f"reviews:{product_name[:40]}")

        # Rate limit: 0.5s between calls
        time.sleep(0.5)

        # STREAM 2: Category-level psychology
        prompt_category = (
            f"Kategoria produktowa: {category}. "
            f"Znajdź w internecie: "
            f"1. Czego ludzie szukają / oczekują kupując produkty z tej kategorii (marzenia, cele) "
            f"2. Jakie mają obawy, problemy i frustracje z produktami z tej kategorii "
            f"3. Co ich zaskakuje (pozytywnie lub negatywnie) w tej kategorii "
            f"Podaj konkretne przykłady z forów, opinii i dyskusji."
        )
        category_result = self._ask_perplexity(prompt_category, f"category:{category[:40]}")

        return {
            "source": "perplexity_dual",
            "product_reviews": product_result,
            "category_insights": category_result,
        }

    def _ask_perplexity(self, prompt: str, label: str = "") -> str:
        """Single Perplexity API call."""
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sonar",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Jesteś researcherem internetowym. Zwracasz tylko fakty i cytaty "
                        "z wiarygodnych źródeł. Odpowiadaj po polsku."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        print(f"  [HARVESTER] Perplexity: '{label}'...")
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [ERROR] Perplexity API failed: {e}")
            return ""

    # --- Google (Fallback) ---

    def _harvest_google(self, product_name: str, category: str) -> Dict:
        """Google Custom Search fallback."""
        query_a = f"{product_name} opinie forum"
        results_a = self._google_search(query_a)

        query_b = f"problemy z {category} forum" if category else f"problemy z {product_name} forum"
        results_b = self._google_search(query_b)

        return {
            "source": "google_search",
            "product_reviews": "\n".join(results_a) if results_a else "",
            "category_insights": "\n".join(results_b) if results_b else "",
        }

    def _google_search(self, query: str) -> List[str]:
        """Single Google Custom Search API call."""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_key,
            "cx": self.google_cx,
            "q": query,
            "num": 3,
            "lr": "lang_pl",
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return [item["snippet"] for item in data.get("items", [])]
        except Exception as e:
            print(f"  [ERROR] Google Search API failed: {e}")
            return []

    # --- Mock (Development) ---

    def _harvest_mock(self, product_name: str, category: str) -> Dict:
        """Mock data for development/testing without API keys."""
        return {
            "source": "mock",
            "product_reviews": (
                f"Używam {product_name} od miesiąca i jestem zadowolony. "
                f"Najlepszy produkt w tej cenie, polecam! "
                f"Trochę słaby packaging, ale sam produkt żyleta."
            ),
            "category_insights": (
                f"Ludzie kupujący {category} szukają najlepszego stosunku jakości do ceny. "
                f"Największe obawy: trwałość i jakość materiałów. "
                f"Pozytywne zaskoczenie: szybka dostawa i dobra obsługa."
            ),
        }
