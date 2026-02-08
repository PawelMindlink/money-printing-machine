# SPECYFIKACJA TECHNICZNA: MSC-ALGO v3.0

## 1. ZAŁOŻENIA WSTĘPNE I KONFIGURACJA

### A. Stałe Biznesowe (Input)

* `VAT_RATE`: (float) np. 0.23 (w kodzie: 0.23 dla 23%)
* `MARGIN_RATE`: (float) Marża przypisana do SKU lub Kategorii.
* `MIN_CONFIDENCE`: (float) 0.80

### B. Definicje Metryk (Calculated Fields)

Dla każdego wiersza danych obliczamy:

1. `Net_Revenue` = `Revenue` / `(1 + VAT_RATE)`
2. `Gross_Profit` = `Net_Revenue` * `MARGIN_RATE`
3. `CM` (Contribution Margin) = `Gross_Profit` - `Ad_Spend`
4. `GPPS` (Gross Profit Per Session) = `Gross_Profit` / `Sessions`
5. `GPPV` (Gross Profit Per View) = `Gross_Profit` / `Item_Views`

### C. Zbiory Aktywne i Progi (Thresholds 75%)

Progi wyznaczamy dynamicznie na podstawie danych z ostatnich 90 dni (używając percentyla 75 dla wartości > 0).

1. **Meta Ads:** `P75_VOL_META` (Revenue), `P75_EFF_META` (CM)
2. **Organic LP:** `P75_VOL_GA` (Sessions), `P75_EFF_GA` (GPPS)
3. **Item Views:** `P75_VOL_ITEM` (Views), `P75_EFF_ITEM` (GPPV)

### D. Wyliczenia Finansowe (ROAS & Caps)

1. **Bid Cap (Max CPA)**
   `Bid_Cap` = `(Price / (1 + VAT))` * `Margin`
   *(Maksymalny koszt pozyskania, przy którym wychodzimy na zero)*

2. **Critical ROAS (Break Even)**
   `Critical_ROAS` = `(1 + VAT)` / `Margin`
   *(Minimalny ROAS, poniżej którego tracimy pieniądze na każdej sztuce)*

3. **Scaling ROAS (Target)**
   `Scaling_ROAS` = `Critical_ROAS` * 1.2
   *(Bezpieczny cel ROAS zapewniający 20% buforu zysku)*

### E. Logika Przypisywania Marży

1. **Override Kategorii:** Jeśli produkt pasuje do wyjątku (np. "Akcesoria"), użyj przypisanej marży.
2. **Produkt Standardowy:** Jeśli brak wyjątku, użyj `Default_Margin`.
3. **Strona Nieproduktowa (np. Home):** Użyj `Min_Margin` (najniższa możliwa marża w systemie), aby zachować bezpieczeństwo wyliczeń.

### F. Logika Klastrowania Cenowego

Produkty są dzielone na grupy marżowe, a następnie klastrowane wg ceny:

1. Sortuj produkty malejąco po cenie.
2. Utwórz klaster z najdroższego produktu (Lider).
3. Dodawaj kolejne produkty, dopóki: `Cena_Produktu` >= `Cena_Lidera` / 1.5.
   *(Czyli Lider nie może być droższy niż 150% najtańszego produktu w klastrze)*.
4. Jeśli warunek nie jest spełniony, zamknij klaster i utwórz nowy z obecnego produktu.

---

## 2. LOGIKA PRZEPŁYWU DANYCH (DATA FLOW)

Zmienna stanu: `FLAGS = []`.

### FAZA 1: FILTR META ADS (Weryfikacja Płatna)

1. **CZY `Meta_Transactions` >= 10?**
    * **NIE:** -> Przejdź do FAZY 2.
    * **TAK:**
        * **CZY `CM` > 0?**
            * **TAK:**
                * IF `Revenue` >= `P75_VOL_META` AND `CM` >= `P75_EFF_META` -> **RETURN: PRIORYTET 1 (PROVEN STAR)**
                * ELSE -> **RETURN: PRIORYTET 2 (PROVEN COW)**
            * **NIE:**
                * `FLAGS.append("META_LOSER")`
                * -> Przejdź do FAZY 2.

---

### FAZA 2: FILTR GA4 LANDING PAGE (Weryfikacja Oferty)

1. **CZY `Sessions` >= `MIN_ORGANIC_SESSIONS`?**
    * `MIN_ORGANIC_SESSIONS` = `100 / Avg_CR` (Cap at 2000).
    * **NIE:** -> Przejdź do FAZY 3.
    * **TAK:**
        * `IS_HIGH_VOL` = `Sessions` >= `P75_VOL_GA`
        * `IS_HIGH_EFF` = `GPPS` >= `P75_EFF_GA`

        * **SCENARIUSZ A (High Vol + High Eff):**
            * IF "META_LOSER" in FLAGS -> **RETURN: PRIORYTET 3 (RECOVERY LAUNCH)**
            * ELSE -> **RETURN: PRIORYTET 3 (NEW STAR LAUNCH)**

        * **SCENARIUSZ B (High Vol + Low Eff):**
            * -> **RETURN: PRIORYTET 99 (FIX LANDING PAGE)**

        * **SCENARIUSZ C (Low Vol + High Eff):**
            * -> **RETURN: PRIORYTET 5 (SCALE UP)**

        * **SCENARIUSZ D (Low Vol + Low Eff):**
            * `FLAGS.append("LP_FAILURE")`
            * -> Przejdź do FAZY 3.

---

### KROK 3: ANALIZA GA4 ITEMS (Popyt)

**Wejście:** Dane GA4 Item (Scope: Item).

1. **CZY `Entity_Type` == "PRODUCT"?**
    * **NIE:** $\rightarrow$ **RETURN: PRIORYTET 8 (IGNORE)** (Kategorie i strony główne nie podlegają analizie produktowej).
    * **TAK:**
        2.  **CZY `ga4item_views` >= `MIN_ORGANIC_SESSIONS`?**
            ***NIE:** $\rightarrow$ **RETURN: PRIORYTET 8 (IGNORE)**.
            *   **TAK:**
                *`IS_HIGH_VOL` = `ga4item_views` >= `P75_VOL_ITEM`
                *   `IS_HIGH_EFF` = `GPPV` >= `P75_EFF_ITEM`
                *
                *   Jeżeli `IS_HIGH_VOL` ORAZ `IS_HIGH_EFF` $\rightarrow$ **RETURN: PRIORYTET 6 (DIRECT-TO-PDP)** (Hidden Star).
                *Jeżeli `NOT IS_HIGH_VOL` ORAZ `IS_HIGH_EFF` $\rightarrow$ **RETURN: PRIORYTET 7 (FEED / DPA)** (Hidden Gem).
                *   Jeżeli `IS_HIGH_VOL` ORAZ `NOT IS_HIGH_EFF` $\rightarrow$ **RETURN: PRIORYTET 8 (IGNORE / WINDOW SHOPPING)**.
                *   Inne przypadki $\rightarrow$ **RETURN: PRIORYTET 8 (IGNORE)**.

---

## 3. LEGENDA WYJŚCIOWA (ACTION PLAN)

| Priorytet | Nazwa Systemowa | Akcja |
| :--- | :--- | :--- |
| **1** | **PROVEN STAR** | Skaluj budżet. |
| **2** | **PROVEN COW** | Utrzymaj. |
| **3** | **LAUNCH / RECOVERY** | Nowe kreacje (Wideo/Statyk). |
| **5** | **SCALE UP** | Kampania Broad / Advantage+. |
| **6** | **DIRECT-TO-PDP** | Kampania na konwersję (PDP). |
| **7** | **FEED / DPA** | Advantage+ Catalog Ads. |
| **99** | **FIX LANDING PAGE** | Audyt UX/Ceny. Wstrzymaj reklamy. |
| **8** | **IGNORE** | Brak działań. |
