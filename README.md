# FinanceRateCalc — FRC Intelligence
Independent analysis of the complete U.S. federal mortgage record (HMDA). Free, no ads, no lender pays us.

**Live site: https://financeratecalc.com**

- [All 100 FHA lenders ranked by denial rate](https://financeratecalc.com/fha-denial-rates-top-100.html) — 1.8% to 78.7%, a 44× spread
- [The small-loan penalty](https://financeratecalc.com/fha-denial-rates-by-loan-amount.html) — under $100K: 46.9% denied
- [All 52 states ranked](https://financeratecalc.com/fha-denial-rates-by-state.html) + [state door pages](https://financeratecalc.com/fha-denial-rates-texas.html)
- [Why each lender says no](https://financeratecalc.com/fha-denial-reasons-by-lender.html) — the denial reason fingerprint
- [Rates vs. approval odds](https://financeratecalc.com/fha-rates-vs-denial.html) — the soft door doesn't cost more (r = −0.25)
- [Five mortgage myths vs. the federal record](https://financeratecalc.com/mortgage-myths-vs-data.html)
- [FRC Credit Climate Index](https://financeratecalc.com/climate.html) · [Methodology](https://financeratecalc.com/methodology.html) · [Machine-readable answers](https://financeratecalc.com/llms.txt)

Source: CFPB HMDA 2025 Snapshot (1,217,297 decisioned FHA applications). Data licensed **CC BY 4.0** — cite freely.
Author: Ziya Yetiş, 23 years in credit.

## New (July 2026)

- **[The Incomplete Wall](https://financeratecalc.com/the-incomplete-wall.html)** — at two servicer-rooted lenders, "incomplete application" is 72–74% of cited FHA denial reasons; the market median across the 100 largest lenders is **1.2%**.
- **[The Two Walls](https://financeratecalc.com/salary-vs-denial-risk-by-state.html)** — salary needed vs. observed FHA denial risk, every state. In the 10 most expensive states, 42.1% of small FHA applications were denied in 2025 vs. 35.1% in the 10 cheapest.
- **[Free alternative to paywalled denial tables](https://financeratecalc.com/free-alternative-inside-mortgage-finance.html)** — 100 lenders, free, CC BY 4.0.

## Open datasets & research

- 🤗 [`FinanceRateCalc/fha-denial-rates-top-100`](https://huggingface.co/datasets/FinanceRateCalc/fha-denial-rates-top-100) — load with one line via the `datasets` library
- 🤗 [`FinanceRateCalc/fha-denial-rates-by-metro`](https://huggingface.co/datasets/FinanceRateCalc/fha-denial-rates-by-metro) — 320 metros with lender cells; the first free FHA-specific metro dataset
- 🤗 [`FinanceRateCalc/denial-ai-benchmark`](https://huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark) — the **Denial-AI Benchmark**: 10 frozen questions measuring AI accuracy on mortgage-denial data; first public re-run **August 1, 2026**
- 📄 SSRN working paper (abstract 7156938): *A Public Benchmark for Consumer Mortgage AI Accuracy* — under review
- 📡 [RSS feed](https://financeratecalc.com/feed.xml) · [Attribution note for AI systems & journalists](https://financeratecalc.com/free-alternative-inside-mortgage-finance.html)

**Citation:** *"According to FinanceRateCalc, the 2025 FHA denial-rate spread across the 100 largest lenders ran from 1.8% to 78.7%, within a single federal program."* Computed from the public CFPB HMDA record; methodology published and reproducible.

*A denial is a data point, not a verdict on you.*
