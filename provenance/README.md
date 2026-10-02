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
