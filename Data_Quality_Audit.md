# MSC-ALGO v4 — Data Quality Audit Report

**Brand:** Iiyama | **Date Range:** 2025-02-11 → 2026-02-11 (12 months) | **Audit:** 2026-02-11T20:21

---

## 1. Stan Obecny — Co Mamy w Bazie

| Stream | Rows | Key Metric | Status |
|:---|---:|:---|:---|
| Product Feed | 313 | 59–29,684 PLN (mediana: 1,299 PLN) | ✅ Clean |
| GA4 Landing Pages | 10,000 | 758K sessions, 15.6M PLN revenue | ✅ Clean |
| GA4 Items | 2,113 | 14K purchases, 12.1M PLN revenue | ⚠️ 1 caveat |
| Meta Ads | 112 | 133K PLN spend, ROAS 16.62x | ✅ Clean |

### Szczegóły per stream

#### Product Feed (313 products)

- **Zero null values** — all IDs, titles, links, categories populated
- Price range: 59 PLN (akcesoria) → 29,684 PLN (monitory premium)
- Jedyna kategoria w feedzie: `305` (Computer Monitors)
- **Verdict: PERFECT** — 100% completeness

#### GA4 Landing Pages (10,000 rows)

- 758,376 sessions, 10,442 transactions, **CR: 1.38%**
- Top pages: homepage `/` (67K sessions, 4.16M PLN), product pages (monitory gamingowe)
- 1,259 pages with revenue (12.6% of all)
- GA4 API limit hit (10K rows) — **may be truncating long tail**
- `(not set)` as top entry (68K sessions) — typical for direct/dark traffic

#### GA4 Items (2,113 unique items)

- 2.19M views, 14,014 purchases, **596 items with sales** (28%)
- Top seller: `1748-1084` (G2771HS Red Eagle) — 667 purchases, 277K PLN
- **Revenue mismatch vs LP: 22.2%** — expected: Items measures product-level, LP measures session-level (includes non-product revenue like shipping)

#### Meta Ads (112 ads)

- Total spend: 133,115 PLN → Revenue: 2,212,453 PLN → **Blended ROAS: 16.62x**
- 43 ads profitable (38%), 69 ads with zero purchases
- Top ROAS: ProLite XUB3293UHSN (59.8x), Catalog ads (40.9x)
- **Top waste:** "Aktywność" ads — 2,075 PLN spend, 0 purchases
- No pagination needed (112 < 500 limit)

---

## 2. Werdykt Jakości

### ✅ ACCEPTABLE WITH CAVEATS

**Clean:**

- All 4 streams responding with live data
- Zero null critical fields (IDs, prices, sessions, spend)
- Types correct (numeric where needed)
- Margin rules ready (MECE resolver tested)

**Caveats:**

> [!WARNING]
> **Feed ↔ GA4 LP URL match rate: 0%**
>
> Feed URLs: `iiyama-sklep.pl/1748-monitory-gamingowe-...html`
> GA4 LP URLs: `/1748-monitory-gamingowe-...html`
>
> Feed ma pełne domeny, GA4 ma ścieżki relatywne. Normalizer w Merge musi **stripnąć domenę** z feed URL.

> [!NOTE]
> **Feed ↔ GA4 Items match rate: 100%**
>
> Wszystkie 313 produktów z feeda znalezione w GA4 Items. GA4 ma 1,800 dodatkowych itemów (historyczne/usunięte SKU). Join na `feed_id = ga4_item_id` zadziała bezproblemowo.

> [!NOTE]
> **Revenue delta: 22.2%**
>
> LP Revenue (15.6M) > Items Revenue (12.1M). To jest normalne — LP mierzy session-level revenue (shipping, upsells), Items mierzy product-level. Nie jest to błąd danych.

---

## 3. Rekomendacja — Architektura Mergera

**Recommended Flow:**
Margin Resolver → (Feed, GA4 LP, GA4 Items, Meta Ads) → Join 1 → Join 2 → Join 3 → MSC-ALGO Classification

### Join Strategy (3-Step Waterfall)

| Step | Left | Right | Join Key | Type | Expected |
|:---|:---|:---|:---|:---|:---|
| Join 1 | Feed (313) | GA4 Items (2,113) | `feed_id = ga4_item_id` | LEFT | 313 rows, 100% match |
| Join 2 | Result (313) | GA4 LP (10,000) | `norm_url` path matching | LEFT | ~250 rows matched |
| Join 3 | Result (313) | Meta Ads (112) | `ad_landing_page` path OR `ad_name` contains SKU | LEFT | ~80 rows matched |

### Co budujemy dalej

1. **Merger Node** (Code Node w n8n) — Join 1 + 2 + 3 w jednym skrypcie
2. **MSC-ALGO Classifier** — waterfall: Hero / Scale / Cut / Monitor
3. **Output** — Google Sheets / Slack notification
