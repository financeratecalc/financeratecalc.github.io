# Universe declarations before figures: VA, USDA and conventional, 2025

**Declared 2026-11-09. No figure for these programs exists yet. Per the universes rule of 2026-09-15, a universe is declared before its figures; this document is that declaration. Counts are filled by the pipeline, not by hand, and the first run that produces them is linked here when it happens.**

## Why these three

The 2025 CFPB HMDA public loan-level file carries every program, not only FHA. The same pipeline that publishes the FHA figures (`scripts/reference_implementation.py` → `materialize_rebuild.py` → claim documents, contracts, receipts) can publish the same figures for VA, USDA and conventional loans with a different `loan_type` filter. The published FHA definitions do not change (pre-registration of 2026-11-04: a definitional change is published first as a dated amendment; none is made here).

## HMDA codes used

| Program | `loan_type` | Insurer / guarantor |
|---|---|---|
| Conventional | 1 | none (not government-insured or -guaranteed) |
| FHA | 2 | Federal Housing Administration — **already published, unchanged** |
| VA | 3 | Department of Veterans Affairs |
| USDA | 4 | USDA Rural Housing Service or Farm Service Agency |

## Universe definitions (proposed ids; status `declared` until the first run)

Common rules, identical to the FHA universe: an application is **decisioned** when `action_taken` is 1 (originated), 2 (approved, not accepted) or 3 (denied); **denial** = action 3; **reverse mortgages** (`reverse_mortgage` = 1) are excluded; purchased loans (6) and preapproval requests (7, 8) are outside the universe; withdrawn (4) and closed-for-incompleteness (5) files are counted only in the application-outcomes family (actions 1–5), never in a denial rate.

- **U-VA-2025-DECISIONED** — `loan_type = 3`; actions 1,2,3; `reverse_mortgage ≠ 1`.
- **U-USDA-2025-DECISIONED** — `loan_type = 4`; actions 1,2,3; `reverse_mortgage ≠ 1`.
- **U-CONV-2025-DECISIONED** — `loan_type = 1`; actions 1,2,3; `reverse_mortgage ≠ 1`; **and `open_end_line_of_credit ≠ 1`** (closed-end only).

### The one difference, stated before any number exists

The conventional universe excludes open-end lines of credit (HELOCs). FHA, VA and USDA programs are closed-end in practice, so the FHA universe never needed the filter and does not carry it; conventional lending includes millions of HELOC applications whose decision dynamics differ from closed-end mortgages, and a single "conventional denial rate" mixing the two would be a figure nobody means. The pipeline will also report, for every program, how many rows the open-end filter would have removed, so that the FHA universe's omission of the filter is measured rather than assumed. If the FHA count is not negligible, that goes to the corrections log as a disclosure, not as a change.

Business-or-commercial-purpose applications (`business_or_commercial_purpose` = 1) are **not** excluded in any universe, matching the FHA definition; their share is reported alongside.

## What will be published first, and what will not

First release per program: the national denominator, denials and rate; the 52 state figures; the application-outcomes shares (actions 1–5). Lender tables follow only after the national and state figures have passed the same dry-run comparison discipline as FHA (a rebuild must reproduce the published files field for field).

Not published, by contract: any sentence comparing programs' denial rates as if they measured the same applicants ("VA denies less than FHA"). The applicant populations differ by construction (eligibility, down payment, credit profile), so the cross-program difference is a composition fact, not a lender or program judgement. Each program's use contract prohibits that inference explicitly, and the bridge page says why.

## Claim id scheme

`<program>-national-denial-rate-2025`, `<program>-state-<xx>-denial-rate-2025`, `outcome-<program>-national-2025` …, where `<program>` ∈ {`va`, `usda`, `conv`}. FHA ids keep their current, unprefixed form. The scheme is reserved here so that no id is minted ad hoc.

## Input

Per-program extracts from the CFPB Data Browser, keyless: `https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv?years=2025&loan_types=<k>`. SHA-256 of each downloaded file recorded in the run report, as for FHA.

## Checks this document commits the pipeline to

1. Running the extended pipeline with `loan_type = 2` must still reproduce the published FHA files exactly (8,122 numeric fields, as in `provenance/release-day-dryrun.json`).
2. Each new program's universe count is published with its definition in `universes.json` before any rate is published on a page.
3. Every figure carries a receipt, a use contract and a reproduce query, from the first day.
