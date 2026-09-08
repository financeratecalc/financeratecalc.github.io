# FHA Lender Denial Outlier Screen — 2025

Free, LEI-keyed screening file computed from the complete public CFPB HMDA
2025 record (FHA forward loans, `loan_type = 2`; HECM excluded).
Licence: CC BY 4.0. No signup, no login, no vendor contract.

**File:** `lender-outlier-screen-2025.csv` (238 rows)
**sha256:** `ccf1a85f2f266dffe3cfc1378480675f0e7488351712935e16c7a2309e64b370`
**Model version:** `frc-mix-expectation-v1.1` (adds confidence intervals and standardised residuals; v1.0 file remains available on request)

## What this is

For each lender with at least 500 decisioned FHA applications in 2025:
the **observed** denial rate, the rate **expected** from that lender's own
applicant and loan profile, and the ratio between them.

A ratio of 1.0 means the lender's denials match what its own applicant mix
predicts — not what the average lender does.

## What this is not

A screening signal for further review. **Not** evidence of misconduct,
discrimination, causation, or non-compliance, and **not** a legal
conclusion or a compliance opinion. HMDA contains no credit scores, so the
expectation is a mix proxy built from published fields — it is not a risk
model, and unobserved credit risk can move a ratio on its own. Nothing
here says anything about an individual application.

## Field dictionary

| Field | Meaning |
|---|---|
| `lei` | Legal Entity Identifier as filed in HMDA. The join key. |
| `lender_name` | Mapped name where a public source allows it; blank means LEI-only. The LEI is authoritative. |
| `apps_total_2025` | Decisioned FHA applications in 2025 (actions 1, 2, 3). |
| `observed_denial_rate_pct` | Denied / decisioned, as filed. |
| `expected_denial_rate_pct` | Applicant-mix model expectation (see below). |
| `observed_expected_ratio` | observed ÷ expected. |
| `ratio_ci95_low`, `ratio_ci95_high` | 95% confidence interval for the ratio (Byar approximation). If the interval contains 1.0, no signal is claimed. |
| `standardized_residual_z` | (observed − expected) / √(n·p·(1−p)). **Rank on this, not on the raw ratio.** |
| `excess_denials` | observed − expected, in applications. |
| `flag` | `above_expectation_ci_excludes_1`, `below_expectation_ci_excludes_1`, or `not_distinguishable`. |
| `profile_coverage_pct` | Share of the lender's applications that fell into peer cells with enough observations to model. |
| `status` | `screening_signal`, or `screening_only_insufficient_coverage` when coverage < 70% or applications < 1,000. |
| `model_version` | Expectation model that produced the row. |

## How the expectation is built

Each application is placed in a peer cell defined by
`state × loan amount × income × DTI band × CLTV band`. The expected denial
count is what the lender would have recorded if each of its applications
had been decided at the national rate for its cell. Cells with fewer than
25 observations fall back to the national rate. Expected rate = expected
denials ÷ decisioned applications.

## Intended use

Join it to your own seller or counterparty list **locally**, on `lei`. You
do not need to send your list anywhere, including to us. Rows flagged
`screening_only_insufficient_coverage` must not be read as "elevated risk"
on their own.

## Versioning

When the expectation model changes, the new file is published under a new
`model_version` and the previous file stays online at its original URL, so
prior results remain reproducible and comparable. Corrections are recorded
in the public log: https://financeratecalc.com/corrections.html

## Source & citation

CFPB HMDA 2025 public loan/application record.
Companion research: doi:10.2139/ssrn.7309319 · doi:10.2139/ssrn.7341481

> FinanceRateCalc (2026). FHA Lender Denial Outlier Screen 2025
> (`frc-mix-expectation-v1.0`). https://financeratecalc.com/lender-outlier-screen.html

Questions on method: ziyetis@gmail.com — no lender, vendor or AI company
funds this work, and we accept no payment from any lender in the screen.
