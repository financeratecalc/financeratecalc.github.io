# claimcheck

Reference checker for Claim Contract 1.0 (draft). Publisher-agnostic: point it at any `claims.json`.

    python claimcheck.py audit https://financeratecalc.com/claims.json
    python claimcheck.py audit ./claims.json --root .
    python claimcheck.py check passport.json contract.json '{"population":"all_us_mortgages"}'
    python claimcheck.py vectors passport.json contract.json

Reports: load errors, hash mismatches, explicit and derived vector reproduction, author-blind
classification of every `does_not_establish` entry (source + syntactic/semantic), agreement rate
with the author's labels where present, distinct-sentence count, conformance level.

No dependencies beyond the standard library. CC BY 4.0.
