# Expert Evaluation & Naming Standards

## 1. Priority Matrix: "OR" Logic Evaluation

### Executive Summary

The proposal to switch from **AND-based** logic (High Intent AND High Profit = Priority) to **OR-based** logic (High Intent OR High Profit = Priority) was evaluated by a simulated panel of experts: Data Analyst, Senior Media Buyer, and CFO.

**Consensus:** Pure "OR" logic is risky for automated scaling because it treats *potential* (High Organic Interest, Low Profit) the same as *proven profit* (Low Interest, High Profit). This dilutes budget efficiency.

### Detailed Expert Opinions

#### 🧑‍💻 The Data Analyst (Focus: Signal Integrity)
>
> "An 'OR' logic creates a massive increase in the volume of P1/P2 products. If we have 1,000 products:
>
> - **Current Logic (AND):** Identifies ~50 winners (Precision).
> - **Proposed Logic (OR):** Might flag ~400 products as 'Winners' (Recall).
>
> **Risk:** You introduce huge 'False Positives'. A product with high traffic but TERRIBLE conversion (a 'Slacker' or 'Bleeding Star') would be prioritized just because it has traffic. This is dangerous for automation."

#### 📉 The Senior Media Buyer (Focus: Operational Efficiency)
>
> "If everything is urgent, nothing is urgent.
>
> If I see a P1 queue with 300 items, and half of them are 'Unprofitable' on Meta but 'High Traffic' on GA4, I can't blindly scale them. I have to check each one manually to see *why* they are unprofitable.
>
> **Recommendation:** Keep 'Scaling' (Profitable) separate from 'Testing/Fixing' (High Traffic/No Profit). Do not mix them in the same Priority Bucket."

#### 💰 The CFO (Focus: ROAS & Cash Flow)
>
> "We must prioritize **Net Cash Flow**. A 'Star' product in GA4 that loses money on Meta (ROAS < Break-even) is a liability, not an asset, until fixed.
>
> **Verdict:** Prioritizing 'Unprofitable' items (even if they are Stars) alongside 'Profitable' items risks draining the daily budget on high-traffic losers before the winners get fed.
>
> **Safe Approach:** Ensure 'Profitable' items ALWAYS get budget first (P1-P3). 'Potential' items (P4-P6) should get a *testing* budget, not a *scaling* budget."

### 🔄 Revised Recommendation: "The Rescue Logic" (Hybrid)

Instead of a blunt "OR", use a specific **Rescue Clause** (which we partially implemented):

1. **Base Rule:** Profitability is King. If `Meta ROAS > Target`, it defaults to at least **P3**.
2. **Rescue Rule:** If a product is a **Star** (High Traffic/Sales) but **No Ads**, upgrade it to **P4** (Test immediately).
3. **Trap Rule:** If a product is a **Star** but **Unprofitable** on ads, keep it at **P4/P5** (Fix Creative/Landing Page), do NOT upgrade to P1 (Scale). Scaling a loser burns cash fast.

---

## 2. Naming Convention: Snake_case vs CamelCase

### Comparison Table

| Feature | `snake_case` (current) | `CamelCase` (proposed) | `Title Case` (human) |
| :--- | :--- | :--- | :--- |
| **Example** | `meta_revenue` | `MetaRevenue` | `Meta Revenue` |
| **Pros** | Python standard (PEP8).<br>Very readable.<br>Easy to select in IDEs. | Standard in JS/JSON (n8n friendly).<br>Matches generic coding style.<br>Slightly shorter. | Best for non-technical users (Excel).<br>Reads like a report. |
| **Cons** | Can be verbose.<br>Not standard in JS/C#. | Harder to read if long.<br>Inconsistent with Python libs (pandas). | **Terrible for code.**<br>Spaces require `df['Col Name']`.<br>Breaks SQL/Dot-notation. |
| **Platform** | Python, SQL, Data Warehouse | JavaScript, APIs, JSON systems | Excel, PDF Reports |

### 🔍 Recommendation for Money Printing Machine

**Verdict: Adopt `snake_case` for Pipeline, Map to `CamelCase` for Output (Optional)**

1. **Internal processing**: Keep `snake_case` (`contribution_profit`, `meta_revenue`).
    - *Why?* The entire Python ecosystem (pandas, numpy, scikit-learn) uses snake_case. Mixing styles makes the code look messy and harder to maintain (`df.MetaRevenue` vs `df.meta_revenue`).

2. **Final Output (CSV/n8n)**:
    - If the primary consumer is **n8n / JavaScript**, `CamelCase` is acceptable but `snake_case` is increasingly common there too.
    - If the primary consumer is **Excel / Human Business User**, `Title Case` ("Contribution Profit") is actually best.

**Decision Point:**
- If we switch to `CamelCase` effectively ("MetaRevenue"), we must rename **ALL** internal columns to match, or have a mapping layer at the very end.
- **My Advice:** Stick to `snake_case` for now to avoid breaking existing n8n mappings and scripts. If you strongly prefer `CamelCase` for the final CSV, I can add a dedicated "Rename" step at the end of the pipeline.
