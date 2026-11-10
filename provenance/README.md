# Build provenance

`rebuild-report.json` is produced by `.github/workflows/build-provenance.yml`: a GitHub-hosted runner
downloads the public CFPB HMDA 2025 FHA extract (URL and SHA-256 recorded in the report), runs
`scripts/reference_implementation.py` at the commit recorded in the report, and compares the result
with the published data files. The report is then attested with GitHub build provenance (SLSA v1 provenance predicate as issued by GitHub's attestation action on hosted runners,
which GitHub documents as Build Level 2; nobody has certified this chain at any level; GitHub OIDC identity, Sigstore, Rekor), so the chain from a claim receipt to the federal input file has no human
computer in it:

    receipt hash8 → signed receipts snapshot (transparency/) → this attested rebuild report → SHA-256 of the CFPB file

First attested rebuild, 2026-10-02: input 768,203,712 bytes, sha256 `cc94236a…`; national
1,187,606 decisioned / 262,250 denied / 22.08% reproduced exactly; 98/98 published top-100 lenders
matched by LEI (rate and count); 52/52 states matched. `history/` keeps every run.

Verify the attestation yourself (needs the GitHub CLI):

```bash
gh attestation verify provenance/rebuild-report.json --repo financeratecalc/financeratecalc.github.io
```

What this proves: that this code, run on that file, yields these numbers. What it does not prove:
that the code is the right reading of the method, or that the CFPB file is correct. Independent
replication (level L4 of the specification) still requires an implementation written by someone else.


## Release-day machine (2026-11-04)

`release-day-dryrun.json`: the latest run of the full pipeline (CFPB file → reference implementation → materialized api/ files) compared number by number with the published files. The 2025 dry run of 2026-11-04 is IDENTICAL on 8,122 numeric fields. `release-day-preregistration.md` / `.json`: what we commit to publish within six hours of the 2026 file, hashed at registration.

## independent-reproduction.json

Written by `scripts/independent_reproduction.py` (release-day workflow, input `independent=yes`). The national, state and lender figures are recomputed by **hmda-analyzer** (PyPI, Jay Patel), an unaffiliated HMDA package not written against our specification, whose own denominator happens to be action_taken 1–3 with denial = action 3. Our only contribution to the computation is the universe pre-filter (loan_type 2, reverse mortgages out), stated in the file. Status wording matters: this is a reproduction by an *unaffiliated implementation*, run by the publisher. It is not a reproduction performed by an unaffiliated person, so the site's "not independently reproduced" line stays until one is.

## Level-2 receipts: official publications restated (2026-11-10)

`scripts/official_restate.py` downloads an official document (first source: HUD's monthly FHA Single Family Production Report), records its SHA-256, and copies a fixed set of labelled cells exactly as printed into `data/official/<source>-<period>.json`; the claim builders then issue `official-<source>-<yyyy-mm>-<figure>` receipts, contracts and snapshot entries like any other family. Nothing is computed: a Level-2 receipt attests that this figure, with this definition, period and exclusion note, appears in that document with that hash — so an AI system restating it can be checked against the source without us. Contracts state what the figure is not (an HMDA origination or application count, a denial rate, a lender figure). Run: release-day workflow, input `official=hud-fhaprod:2026-08`.
