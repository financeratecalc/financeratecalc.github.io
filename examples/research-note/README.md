# Research note from one published claim — one command, three files

This is what you get (national FHA denial rate, 2025; produced by the command below against the live endpoint):

```
# Research note: frc:claim:national-fha-denial-rate-2025

**Finding.** In 2025, 22.1% ⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b:c2610⟧ of decisioned FHA applications were denied (actions 1,2,3; loan_type 2).

Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only.

**Keep these qualifiers when you paraphrase:**
- period: 2025
- population: decisioned FHA applications
- program_scope: FHA only, not all mortgages

**This figure does not establish:**
- 22.1% of ALL US mortgage applications were denied
- 22.1% applies to purchase-only or refinance-only segments
- any individual's denial probability

**Provenance.** Data: CFPB/FFIEC HMDA public record, 2025. Passport … Use contract … Verify the receipt at any later date: https://frc-mcp.ziyetis.workers.dev/verify?r=…

Status: **verified** (verify: current; server 1.31.0). License CC BY 4.0.
```

Full sample: [`sample-output/brief.md`](sample-output/brief.md), [`sample-output/evidence.json`](sample-output/evidence.json), [`sample-output/manifest.json`](sample-output/manifest.json).

## Run it

```
node examples/research-note/make_note.mjs                                  # default claim, writes out/national-fha-denial-rate-2025/
node examples/research-note/make_note.mjs amerisave-fha-denial-rate-2025   # any of the 189 claim ids in https://financeratecalc.com/claims/index.json
node examples/research-note/make_note.mjs metro-gap-cleveland-oh-2025 notes/cleveland
```

Node 18+. No API key, no account, no model call. Public sources only: the cite card (`GET /cite/<id>`), the claim passport and use contract on financeratecalc.com, and the receipt check (`GET /verify`).

## What it does, in order

1. Fetches the cite card for the claim: the sentence we would accept, the value, the receipt, the attribution.
2. Fetches the passport and the use contract; keeps every required qualifier (period, population, program scope) and the "does not establish" list.
3. Verifies the receipt against the live server. `current` → status **verified**. `stale` → status **stale**, the note carries the correction link, exit code 2. Missing field → **incomplete**, exit code 2. "Delivered" is never written for an unverified figure.
4. Writes `brief.md` (the human note), `evidence.json` (the card, passport, contract and verification exactly as returned) and `manifest.json` (claim id, receipt, hash, period, data vintage, server version, URLs used, run time, status).
5. On a rerun into the same folder it reads the previous manifest; a changed receipt is reported in the note and the manifest (`previous_run.changed_since: true`), never presented as a silent update.

## What it is not

- It is not MCP adoption: this example uses the JSON cite/verify path. The same card reaches agents over MCP (`check_claim_contract`, `get_*` tools); `manifest.paths` records which path was used.
- It is not a test of agent behaviour. It shows that the integration can be set up and a sourced deliverable produced; the Agent Stress Lab measures what agents do with it.
- It does not predict any application, rank lenders or state causes; the contract's "does not establish" list is printed in every note.

## Environment variables (offline tests only)

`FRC_ENDPOINT` (default `https://frc-mcp.ziyetis.workers.dev`), `FRC_SITE_BASE` (default `https://financeratecalc.com`).

CC BY 4.0.
