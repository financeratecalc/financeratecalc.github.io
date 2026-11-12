# Universe declarations before figures: purchase and refinance, 2025

**Declared 2026-11-12. No purchase-only or refinance-only figure exists on this site yet. Per the universes rule of 2026-09-15 a universe is declared before its figures; this document is that declaration. Counts are filled by the pipeline (`scripts/denominator_grid.py`), not by hand.**

## Why

Answer engines asked for "the FHA denial rate" return 22%, 14%, 12% and 39% in the same week, each from a different page, most without a stated denominator. Three things differ between those numbers: the loan purpose counted, the applications counted in the denominator, and scope filters such as first-lien owner-occupied site-built homes. This site has published one cell of that table (all purposes, decisioned applications). The purchase and refinance cells are the ones readers ask for most, and no source observed so far publishes them with a denominator.

## Universes

Common rules, identical to the published program universes: decisioned = `action_taken` 1, 2 or 3; denial = 3; `reverse_mortgage` = 1 excluded; conventional also excludes `open_end_line_of_credit` = 1.

| Universe id | Program | Loan purpose |
|---|---|---|
| U-FHA-2025-DECISIONED-PURCHASE | `loan_type` 2 | `loan_purpose` 1 (home purchase) |
| U-FHA-2025-DECISIONED-REFINANCE | `loan_type` 2 | `loan_purpose` 31 or 32 (refinancing, including cash-out) |
| U-VA-2025-DECISIONED-PURCHASE | `loan_type` 3 | `loan_purpose` 1 |
| U-VA-2025-DECISIONED-REFINANCE | `loan_type` 3 | `loan_purpose` 31 or 32 |

USDA and conventional follow the same scheme once their program universes carry a count.

## The guard

A run writes nothing unless (a) its all-purpose decisioned count equals the published count of the program universe (1,187,606 for FHA; 712,121 for VA) and (b) the purposes add up to that total. A split that does not reconcile to the published figure is not published.

## What is published, and what is not

- **With receipts:** the purchase and the refinance denial rate per program, on the decisioned base. Claim ids `purpose-<program>-purchase-denial-rate-2025` and `purpose-<program>-refinance-denial-rate-2025`, `<program>` ∈ {`fha`, `va`, `usda`, `conv`}.
- **As a reference table, without receipts:** every purpose × scope cell with its five action counts and its rate on three bases (decisioned; acted on; denied plus originated), so a figure met elsewhere can be placed. The "standard" scope is first lien, owner-occupied principal residence, site-built, 1–4 units.
- **Not published:** any statement about which denominator another publisher used. A cell that reproduces a number found elsewhere is a match, not an attribution. No sentence that one purpose or program is easier to obtain: the applicant populations differ.
