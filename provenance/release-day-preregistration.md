# Pre-registration: the 2026 HMDA release day

**Registered 2026-11-04. Hash of this file and the pipeline commit are recorded in `provenance/release-day-preregistration.json` when the dry run below reports IDENTICAL.**

## What we commit to

When the CFPB publishes the 2026 HMDA public loan-level file (the 2025 file was published 31 March 2026), FinanceRateCalc will, **within six hours of the file becoming downloadable**, publish from it:

1. the national FHA denial rate for 2026 with its denominator (decisioned forward FHA applications, actions 1–3, reverse mortgages excluded) and the share of applications acted on that were withdrawn, denied, closed for incompleteness, originated, and approved but not accepted;
2. the same figures for every state and for every metro with at least 500 decisioned FHA applications;
3. the denial rate, decisioned volume and stated-reason shares for the 100 largest FHA lenders by 2026 decisioned volume (a fresh cut; the 2025 panel is not carried over);
4. a receipt (`⟦FRC:<id>:<value>:<hash8>⟧`) and a use contract for every figure, verifiable at `/verify` without this publisher, under Receipt 1.0;
5. the full bundle (`llms-full.txt`), the MCP tools, the A2A card and the HF datasets refreshed to the new year.

Every figure will be computed by the pipeline named below, from the file whose SHA-256 is recorded at download time, with no hand-typed number anywhere in the chain.

## What we will not do

- Publish any 2026 figure before the full file is downloadable (no partial, leaked or vendor-sourced numbers).
- Change the published definitions (universe, denominator, reason-share basis) between now and release day. A definitional change, if ever needed, is published here first as a dated amendment.
- Rank lenders by anything other than observed rate, call any lender better or worse, or predict any application.

## The pipeline

`scripts/reference_implementation.py` → `scripts/materialize_rebuild.py --panel fresh` → `scripts/application_outcomes.py`, `scripts/door_report_cells.py` → `scripts/build_api_summaries.py` → `scripts/build_claim_documents.py` → `scripts/build_claim_contracts.py` → `scripts/build_receipt_hash_history.py` → `scripts/build_receipts_snapshot.py` → page builders → `scripts/build_llms_full.py` → `scripts/check_page_values.py`, `scripts/check_page_phrasing.py`. Orchestrated by `.github/workflows/application-outcomes.yml` ("Release-day machine") with `apply=APPLY`.

## Why this can be believed

The same pipeline, run on the 2025 file (SHA-256 `cc94236a94f960bbd8a5a5b0710500719252f18af550d0d38fe7c9d01a21e717`) in dry-run mode on 2026-11-04, reproduced every published 2025 figure — 8,122 numeric fields across the national, 52 state, 319 metro and 98 lender files — with zero differences (`provenance/release-day-dryrun.json`). Three conventions had to be made explicit along the way and are now in code rather than memory: the 2025 lender panel's membership was fixed on the pre-correction file (five lenders at the margin would differ on a fresh cut — disclosed in the corrections log); the 2025 peer medians were fixed in July; metro lender cells are listed by observed rate. A 2026 build uses fresh cuts for all three.

## How to hold us to it

On release day, compare the timestamp of the CFPB file's availability with the commit time of the first 2026 claim document in this repository. The input hash, the code commit and the run id will be in `provenance/release-day-dryrun.json` (mode `APPLY`). If we miss six hours, the delay and its cause go in the corrections log.

Signed by publication: this file's SHA-256 at registration is in `provenance/release-day-preregistration.json` and the file is in git history; any later edit is visible as a diff.
