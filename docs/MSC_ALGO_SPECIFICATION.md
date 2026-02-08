# Specyfikacja Algorytmu MSC-ALGO v1.0

## 1. Wstęp i Cel Biznesowy

Celem algorytmu jest automatyczna identyfikacja i priorytetyzacja adresów URL oraz Produktów do promocji w systemie Meta Ads. System alokuje zasoby tam, gdzie prawdopodobieństwo ROI jest najwyższe.

Algorytm opiera się na **Logice Kaskadowej (Waterfall Model)**:

1. **Faza Meta Ads**: Analiza historycznej rentowności płatnej.
2. **Faza GA4 Landing Page**: Analiza potencjału organicznego sesji.
3. **Faza GA4 Item**: Analiza popytu wewnętrznego na poziomie produktu.

---

## 2. Definicje Zmiennych (Data Dictionary)

### Zmienne Wejściowe (Input)

* `VAT_RATE`: Standardowa stawka (np. 0.23).
* `MARGIN_RATE` (w kodzie `base_gross_margin`): Marża przypisana do produktu/kategorii.

### Zmienne Obliczane (Computed Metrics)

* `NET_REV`: Przychód netto = `Total_Revenue / (1 + VAT_RATE)`.
* `GROSS_PROFIT` (Zysk Brutto): `NET_REV * MARGIN_RATE`.
* `CM` (Contribution Margin / Profit): `GROSS_PROFIT - Ad_Spend`.
* `GPPS` (Gross Profit Per Session): `GROSS_PROFIT (z GA4 LP) / ga4lp_sessions`.
* `GPPV` (Gross Profit Per View): `GROSS_PROFIT (z GA4 Item) / ga4item_views`.
* `CR` (Conversion Rate): `ga4lp_purchases / ga4lp_sessions`.

---

## 3. Progi Dynamiczne (Dynamic Thresholds)

Używamy **75. percentyla (Top 25%)** danych niezerowych jako wyznacznika "Wysokiej Jakości" dla danego klienta:

* `P75_VOL_META`: Top wolumen przychodu Meta.
* `P75_EFF_META`: Top zysk kontrybucyjny (CM) Meta.
* `P75_VOL_GA`: Top liczba sesji `ga4lp_sessions`.
* `P75_EFF_GA`: Top `GPPS`.
* `P75_VOL_ITEM`: Top liczba wyświetleń `ga4item_views`.
* `P75_EFF_ITEM`: Top `GPPV`.

---

## 4. Faza I: Istotność Statystyczna (Significance Gate)

* `MIN_META_TRANS`: Minimum **10** transakcji Meta, aby ocenić ROAS.
* `MIN_ORGANIC_SESSIONS`: `100 / Średni_CR_Sklepu` (Maksymalnie 2000 sesji).

---

## 5. Algorytm Decyzyjny (Core Logic)

### KROK 1: ANALIZA META ADS (Historia)

**Wejście:** Dane Meta Ads per `landing_page_url`.

1. Jeśli `meta_purchases >= MIN_META_TRANS`:
    * Jeśli `CM > 0`:
        * Jeżeli `meta_revenue >= P75_VOL_META` ORAZ `CM >= P75_EFF_META` -> **PRIORYTET 1: PROVEN STAR**
        * W przeciwnym razie -> **PRIORYTET 2: PROVEN CASH COW**
    * Jeśli `CM <= 0` -> Oznacz jako `HISTORIA_NEGATYWNA` i przejdź do Kroku 2.
2. W przeciwnym razie -> Przejdź do Kroku 2.

### KROK 2: ANALIZA GA4 LP (Potencjał)

**Wejście:** Dane GA4 Landing Page (Scope: Session).

1. Jeśli `ga4lp_sessions >= MIN_ORGANIC_SESSIONS`:
    * `IS_HIGH_VOL` = `ga4lp_sessions >= P75_VOL_GA`
    * `IS_HIGH_EFF` = `GPPS >= P75_EFF_GA`
    *
    * Jeżeli `IS_HIGH_VOL` ORAZ `IS_HIGH_EFF`:
        * Jeżeli `HISTORIA_NEGATYWNA` -> **PRIORYTET 3: RE-LAUNCH CANDIDATE** (Produkt topowy, reklama wymaga nowej kreacji).
        * W przeciwnym razie -> **PRIORYTET 3: ORGANIC STAR**
    * Jeżeli `IS_HIGH_VOL` ORAZ `NOT IS_HIGH_EFF` -> **PRIORYTET 4: HIGH TRAFFIC / LOW CONV**
    * Jeżeli `NOT IS_HIGH_VOL` ORAZ `IS_HIGH_EFF` -> **PRIORYTET 5: HIGH CONV / LOW TRAFFIC**
    * W przeciwnym razie -> Przejdź do Kroku 3.
2. W przeciwnym razie -> Przejdź do Kroku 3.

### KROK 3: ANALIZA GA4 ITEMS (Popyt)

**Wejście:** Dane GA4 Item (Scope: Item).

1. Jeśli `ga4item_views >= MIN_ORGANIC_SESSIONS`:
    * `IS_HIGH_VOL` = `ga4item_views >= P75_VOL_ITEM`
    * `IS_HIGH_EFF` = `GPPV >= P75_EFF_ITEM`
    *
    * Jeżeli `IS_HIGH_VOL` ORAZ `IS_HIGH_EFF` -> **PRIORYTET 6: HIDDEN STAR** (Ludzie chcą produktu, ale Landing Page go nie promuje).
    * Jeżeli `NOT IS_HIGH_VOL` ORAZ `IS_HIGH_EFF` -> **PRIORYTET 7: HIDDEN GEM** (Wysoka konwersja wewnątrz sklepu, mała widoczność).
    * W przeciwnym razie -> **STATUS: IGNORE**
2. W przeciwnym razie -> **STATUS: IGNORE**

---

## 6. Mapa Wyjściowa

| Priorytet | Nazwa Systemowa | Akcja |
| :--- | :--- | :--- |
| **1** | PROVEN STAR | Skaluj budżet. |
| **2** | PROVEN CASH COW | Utrzymaj / Optymalizuj. |
| **3** | ORGANIC STAR / RE-LAUNCH | **ZADANIE DLA DESIGNERA:** Nowe kreacje. |
| **4** | HIGH TRAFFIC / LOW CONV | Remarketing / Poprawa oferty. |
| **5** | HIGH CONV / LOW TRAFFIC | Broad targeting / DSA. |
| **6** | HIDDEN STAR | Reklama bezpośrednio na PDP. |
| **7** | HIDDEN GEM | Dodaj do katalogu DPA. |
| **8** | IGNORE | Brak działań. |
