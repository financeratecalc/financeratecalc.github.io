---
license: cc-by-4.0
language: [en]
tags: [finance, mortgage, fha, hmda, lending, denial-reasons, fair-lending]
pretty_name: FHA Denial Reason Fingerprints — 100 Largest Lenders, 2025
size_categories: [n<1K]
---

# FHA Denial Reason Fingerprints — 100 Largest Lenders (2025)

For each of the 100 largest FHA lenders in the complete 2025 CFPB HMDA record: the share of its denials that cite each stated reason. Fingerprints are published for the 95 lenders with at least 50 stated-reason denials.

## Basis (read this before quoting a number)

**share_of_denials_citing** — for a lender, the percentage of its formal denials (action_taken 3) whose four reason fields include the reason, each reason counted once per denial. A denial can carry up to four reasons, so a lender's shares are **not a partition and need not sum to 100**.

**Changed on 2026-11-07.** The 2026-07-25 version of this dataset used a different basis, *share of cited reasons* (reason citations ÷ all reason citations, summing to 100), and its headline figures — DTI median 29.4%, builder-affiliated median 50.5%, Pulte 62.8%, Lennar 53.1%, "incomplete" median 1.2% — are on that basis. They were not wrong on their own terms, but the site moved to the share-of-denials basis in September 2026 and this copy was not updated, so for seven weeks two different "FinanceRateCalc" values of the same statistic were in circulation. Logged: https://financeratecalc.com/corrections.html#2026-11-07-hf-fingerprints-basis. Cite the basis with the number.

## Medians across the 95 lenders (share of denials citing)

- Debt-to-income: **40.8%** — the most-cited reason; builder-affiliated lenders (DHI, Lennar, NVR, Pulte, Inspire, M/I, Taylor Morrison, HomeAmerican) median **61.6%**, Pulte **88.4%**. See https://financeratecalc.com/the-builders-door.html
- Credit history: **25.9%**
- Collateral: **10.8%** (builder-affiliated median 0.1%)
- Incomplete application: **2.8%** across lenders, but **75.2%** at Carrington Mortgage Services and **73.7%** at Lakeview Loan Servicing. See https://financeratecalc.com/the-incomplete-wall.html
- Insufficient cash 7.6% · unverifiable information 8.8% · employment 5.0% · other 11.3%

## Files
- `fha_denial_reason_fingerprints_2025.csv` — one row per lender: counts, denial rate, nine reason shares (`share_of_denials_citing_<reason>_pct`)
- `reason_fingerprints_2025.json` — same data plus the basis statement, the superseded basis and the medians

## Methodology
FHA = loan_type 2; reverse mortgages excluded. Decisioned = action_taken {1,2,3}; denial = action 3. Reason shares are computed on formal denials only; withdrawn (action 4) and closed-for-incompleteness (action 5) files are not denials and are outside the universe. Full rules and the reference implementation: https://financeratecalc.com/methodology.html · live copy of this table: https://financeratecalc.com/api/denial-reasons-top100.json · every figure carries a Receipt 1.0 receipt verifiable at https://financeratecalc.com/verify.html

Reason distributions partly reflect applicant, product and channel mix. These are historical observations about institutions, not evidence of wrongdoing, not rankings by quality and not recommendations about any lender.

## Citation
> Primary data: CFPB HMDA 2025. Derived shares: Yetiş, Z. (2026), *FHA Denial Reason Fingerprints*, FinanceRateCalc, basis share_of_denials_citing, version 2026-11-07. https://financeratecalc.com

CC BY 4.0 · Not a lender · No ads · A denial is a data point, not a verdict on the applicant.
