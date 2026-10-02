# Claim transparency

`receipts-snapshot.sigstore.json` is a Sigstore bundle: a keyless signature over
`rl-env/frc_citation/receipts-snapshot.json` (every claim id FinanceRateCalc issues receipts for,
with its current value and hash8), made by the workflow `claims-transparency.yml` in this
repository and recorded with a timestamp in the public, append-only Rekor log. `log.json` lists
every signed snapshot with its Rekor index, so corrections are dated by a log the publisher does
not control.

Verify a receipt without asking the publisher:

```bash
cosign verify-blob receipts-snapshot.json --bundle receipts-snapshot.sigstore.json \
  --certificate-identity-regexp '^https://github.com/financeratecalc/financeratecalc.github.io/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
# then look up the receipt's claim id in receipts-snapshot.json and compare value and hash8
```

A receipt whose hash8 is not in any signed snapshot was never issued by this publisher. A receipt
whose hash8 is in an older snapshot but not the latest was issued before a correction; the two log
entries date the change.

`eval-runs-manifest.json` + `.sigstore.json`: SHA-256 of every saved automated evaluation run,
signed the same way, so published benchmark results are tamper-evident and cannot be pruned
without a visible gap in the log.

`provenance-check.json`: the result of recomputing the published figures from the public CFPB
file inside GitHub Actions (`build-provenance.yml`): input file hash, code commit, output hash,
and whether every published national, lender and state figure matched. When they match, the
recomputed output is attested with GitHub build provenance (SLSA), visible under the repository's
Attestations tab and in Rekor.
