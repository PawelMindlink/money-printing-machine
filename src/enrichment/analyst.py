"""
Analyst — LLM Synthesis for Psychographic Columns.
Refactored from Personiarz: .env integration, extended schema (10 columns), Claude Sonnet preferred.
"""

import json
import os
import re
from typing import Dict, Any, Optional


class Analyst:
    """Synthesizes harvested internet data into structured psychographic columns."""

    def __init__(self):
        """Initialize LLM provider from environment variables."""
        self.provider = None
        self.client = None
        self.model = None

        # Priority: Anthropic > OpenAI (no Google — user specified Claude Sonnet)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")

        if anthropic_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=anthropic_key)
                self.provider = "anthropic"
                self.model = "claude-sonnet-4-5"
                print("[ANALYST] Claude Sonnet configured ✓")
            except ImportError:
                print("[ERROR] anthropic package not installed. Run: pip install anthropic")

        elif openai_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=openai_key)
                self.provider = "openai"
                self.model = "gpt-4o"
                print("[ANALYST] OpenAI GPT-4o configured ✓")
            except ImportError:
                print("[ERROR] openai package not installed. Run: pip install openai")

        else:
            print("[ANALYST] WARNING: No LLM API key found. Will return empty analysis.")

    def analyze(
        self,
        product_name: str,
        category: str,
        harvest_data: Dict[str, str],
        feed_specs: Optional[Dict] = None,
        url_specs: str = "",
    ) -> Dict[str, str]:
        """
        Synthesize harvest + feed data into 10 psychographic columns.

        Returns dict with keys:
            persona_name, persona_dream, persona_fear, persona_awareness,
            tech_translator, social_proof_quote, competitive_edge,
            visual_hook_suggestion, buying_objections, harvest_date
        """
        if not self.provider:
            return self._empty_result()

        # Build the mega-prompt for all 10 columns in one call
        prompt = self._build_prompt(product_name, category, harvest_data, feed_specs, url_specs)

        response_text = self._call_llm(prompt)
        if not response_text:
            return self._empty_result()

        result = self._parse_json_response(response_text)

        # Ensure all expected keys exist
        expected_keys = [
            "persona_name", "persona_dream", "persona_fear", "persona_awareness",
            "tech_translator", "social_proof_quote", "competitive_edge",
            "visual_hook_suggestion", "buying_objections",
        ]
        for key in expected_keys:
            if key not in result:
                result[key] = ""

        return result

    def _build_prompt(
        self,
        product_name: str,
        category: str,
        harvest_data: Dict[str, str],
        feed_specs: Optional[Dict],
        url_specs: str,
    ) -> str:
        """Build the analysis prompt with all available data sources."""

        # Feed specs section
        feed_section = ""
        if feed_specs:
            feed_section = f"""
[SOURCE C: PRODUCT FEED (Technical Specs)]
- Title: {feed_specs.get('title', '')}
- Description: {feed_specs.get('description', '')}
- Categories: {', '.join(feed_specs.get('product_types', []))}
"""
        if url_specs:
            feed_section += f"\n[SOURCE D: URL SEO Keywords]\n{url_specs}\n"

        return f"""
ACT AS: Consumer Psychologist & E-commerce Strategist.
TASK: Create a complete psychographic profile for product: '{product_name}' (Category: {category}).

INPUT DATA:

[SOURCE A: PRODUCT-SPECIFIC REVIEWS]
{harvest_data.get('product_reviews', 'Brak danych.')}

[SOURCE B: CATEGORY-LEVEL INSIGHTS]
{harvest_data.get('category_insights', 'Brak danych.')}
{feed_section}

OUTPUT FORMAT: Return ONLY a valid JSON object with these exact keys:

{{
    "persona_name": "One-word persona label (e.g. 'Pro Gamer', 'Mama Optymalizatorka', 'Budget Hunter')",
    "persona_dream": "The #1 Dream Outcome this persona wants from this product. Be specific and emotional. (Hormozi: What is their Heaven state?)",
    "persona_fear": "The #1 Fear/Pain Point. What keeps them up at night about this category? (Hormozi: What Effort/Sacrifice do they want to avoid?)",
    "persona_awareness": "One of: 'unaware' | 'problem_aware' | 'solution_aware' | 'product_aware'. Based on the reviews — are people searching for solutions, comparing products, or already decided?",
    "tech_translator": "Translate EVERY technical spec from Sources C/D into a clear BENEFIT. Format: 'Spec -> Benefit | Spec -> Benefit'. If no specs available, return empty string.",
    "social_proof_quote": "The 2-3 STRONGEST positive quotes from Source A. Real user words only. If Source A says 'Brak danych', return empty string.",
    "competitive_edge": "What makes THIS product better than alternatives in this category? Based on Sources A+B. If unclear, state the category's key differentiator.",
    "visual_hook_suggestion": "For a Meta Ad designer: what physical feature of this product should be zoomed in on, circled, or contrasted? (e.g. 'thin bezels vs competitor chunky frames', 'leather texture close-up')",
    "buying_objections": "Top 2-3 reasons people hesitate to buy from Source B. (e.g. 'Drogi', 'Nie wiem jaki rozmiar wybrać', 'Boję się że nie będzie pasował')"
}}

RULES:
- NO HALLUCINATIONS. Only use facts from the INPUT DATA.
- Language: POLISH (Polski).
- Style: Emotional, direct, copywriter-ready.
- If a source is empty/missing, return empty string for fields that depend on it.
- The tech_translator must ONLY use specs from Sources C/D. Never invent features.
"""

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM provider."""
        try:
            if self.provider == "anthropic":
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text

            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content

        except Exception as e:
            print(f"  [ERROR] LLM call failed: {e}")
            return ""

    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from LLM response, handling markdown blocks and extra text."""
        # 1. Try direct parse (cleanest)
        try:
            clean = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        # 2. Extract first JSON object via brace matching
        try:
            start = response_text.find("{")
            end = response_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(response_text[start : end + 1])
        except json.JSONDecodeError:
            pass

        print(f"  [ERROR] JSON parsing failed. Response preview: {response_text[:100]}...")
        return {}

    @staticmethod
    def _empty_result() -> Dict[str, str]:
        """Return empty result with all expected keys."""
        return {
            "persona_name": "",
            "persona_dream": "",
            "persona_fear": "",
            "persona_awareness": "",
            "tech_translator": "",
            "social_proof_quote": "",
            "competitive_edge": "",
            "visual_hook_suggestion": "",
            "buying_objections": "",
        }
