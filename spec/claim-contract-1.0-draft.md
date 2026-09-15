# Claim Contract 1.0 (draft 1)

**Machine-readable use conditions for published statistics.**

Status: draft 1, 2026-09-15. Editor: Ziya Yetiş (FinanceRateCalc). License: CC BY 4.0.
Reference implementation: 189 claims at https://financeratecalc.com/claims.json (passport format 0.1, contract format 0.1, which this document generalises).

---

## 1. The problem in one paragraph

Publishers release numbers. Machines repeat them. The number usually survives the trip; the sentence around it usually does not. "22.1% of decisioned FHA applications were denied in 2025" becomes "a quarter of mortgage applicants get rejected, so avoid lender X." The value is intact, the population, period, program scope and permitted inference are gone. Today this failure is filed under "AI hallucination", which places it entirely on the model. A Claim Contract moves half of it back to the publisher: the number ships with the conditions under which it may be restated, in a form a machine can check before writing.

robots.txt says whether a page may be read. llms.txt says what a site is about. A Claim Contract says how a specific statistic may be *used*.

## 2. Design rules

1. **Free text is the output of evidence, not its input.** A conforming writer certifies a proposed use against the contract, then writes. It does not write and then look for a source.
2. **Every number is generated from the dataset, never typed beside it.** A contract that cannot be regenerated from its source is not a contract, it is a caption.
3. **Corrections are part of the claim.** A value with no correction history is a value whose history is unknown. The contract carries the log.
4. **Saying what a number does not establish is as binding as saying what it does.**
5. **A machine must be able to answer "may I say this?" without reading prose.** Everything a checker needs is structured; prose is for humans.

## 3. Files

A conforming publisher exposes, at the site root:

| file | required | purpose |
|---|---|---|
| `/claims.json` | yes | index of every published claim: id, canonical URL, metric, sha256 |
| `/claims/<id>.json` | yes | the **passport**: what the number is and where it comes from |
| `/claims/<id>.contract.json` | yes | the **contract**: how the number may be restated |
| `/claims/<id>.reproduce.json` | recommended | how to recompute it from the primary source |

`llms.txt` SHOULD name `/claims.json`. `robots.txt` MUST NOT block `/claims/`.

## 4. The passport (`/claims/<id>.json`)

The passport answers *what is this number and where did it come from*.

```json
{
  "passport_version": "1.0",
  "passport_id": "frc:claim:national-fha-denial-rate-2025",
  "issuer": "FinanceRateCalc",
  "issued_at": "2026-08-12T00:00:00Z",
  "canonical_url": "https://financeratecalc.com/claims/national-fha-denial-rate-2025.json",
  "sha256": "13b9…c90",
  "claim": {
    "metric": "fha_denial_rate",
    "value": 0.221,
    "unit": "share_of_decisioned_applications",
    "subject": "United States, all reporting lenders",
    "period": "2025",
    "definition": "denials (action 3) / decisioned applications (actions 1,2,3), FHA (loan_type 2)",
    "n": 1187606
  },
  "provenance": {
    "primary_source": "CFPB/FFIEC HMDA public record, 2025",
    "dataset": "loan_type=2; action_taken in {1,2,3}",
    "code_history": "https://github.com/financeratecalc/financeratecalc.github.io"
  },
  "use_boundary": {
    "allowed": ["historical aggregate comparison", "journalism", "research"],
    "prohibited": ["individual approval prediction", "borrower profiling", "personalized lender recommendation"],
    "minimum_cell_size": 100
  },
  "corrections": [
    {"date": "2026-07-26", "from": 0.217, "to": 0.221, "reason": "29,691 reverse-mortgage (HECM) records removed from the universe", "log": "https://financeratecalc.com/corrections.html"}
  ],
  "attribution": {
    "required_text": "Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only.",
    "license": "CC BY 4.0"
  },
  "independent_reproduction_status": "not yet independently reproduced"
}
```

Required fields: `passport_version`, `passport_id`, `issuer`, `issued_at`, `canonical_url`, `sha256`, `claim.metric`, `claim.value`, `claim.unit`, `claim.subject`, `claim.period`, `claim.definition`, `provenance.primary_source`, `attribution.license`, `corrections` (may be an empty array, but MUST be present: an absent log and an empty log are different statements).

`sha256` is the hash of the claim object serialised canonically (sorted keys, no whitespace). A consumer that recomputes a different hash treats the passport as tampered or stale.

## 5. The contract (`/claims/<id>.contract.json`)

The contract answers *how may this number be restated*.

```json
{
  "contract_version": "1.0",
  "passport_id": "frc:claim:national-fha-denial-rate-2025",
  "canonical_claim": {
    "template": "In {period}, {value} of decisioned FHA applications were denied.",
    "required_fields": ["period", "population", "program_scope"]
  },
  "required_qualifiers": {
    "period": "2025",
    "population": "decisioned FHA applications",
    "program_scope": "FHA only, not all mortgages"
  },
  "does_not_establish": [
    "a denial rate for all US mortgage applications",
    "a rate for purchase-only or refinance-only segments",
    "any individual's denial probability"
  ],
  "forbidden_transformations": [
    "causal_attribution", "individual_prediction", "personalized_lender_recommendation", "legal_conclusion"
  ],
  "test_vectors": [
    {"id": "pass-canonical", "proposed_use": {"population": "decisioned_fha_applications", "causal_assertion": false}, "expected_verdict": "pass"},
    {"id": "fail-scope",     "proposed_use": {"population": "all_us_mortgages"},                                     "expected_verdict": "block", "reason_code": "SCOPE_TOO_BROAD"},
    {"id": "fail-personal",  "proposed_use": {"individual_prediction": true},                                        "expected_verdict": "block", "reason_code": "INDIVIDUAL_PREDICTION_PROHIBITED"}
  ]
}
```

### 5.1 Verdicts

A checker returns exactly one of:

| verdict | meaning |
|---|---|
| `pass` | the proposed use restates the claim within its qualifiers and forbidden-transformation list |
| `needs_qualifier` | the use is permissible once a named qualifier is added (the checker returns which) |
| `block` | the use asserts something the claim does not establish, or applies a forbidden transformation |

`needs_qualifier` exists because most real misuse is omission, not invention: the number is right and the population is missing.

### 5.2 Reason codes (initial registry)

`SCOPE_TOO_BROAD`, `SCOPE_TOO_NARROW`, `PERIOD_MISSING`, `POPULATION_MISSING`, `CAUSAL_ATTRIBUTION`, `INDIVIDUAL_PREDICTION_PROHIBITED`, `RECOMMENDATION_PROHIBITED`, `LEGAL_CONCLUSION_PROHIBITED`, `STALE_VALUE` (a value superseded in `corrections`), `HASH_MISMATCH`, `ATTRIBUTION_MISSING`.

### 5.3 Test vectors are normative

Every contract ships at least one `pass` and one `block` vector. A checker that does not reproduce a contract's own test vectors is not conforming for that contract. This is how a publisher can verify any third-party checker, and how a checker can verify any publisher's contract, without either trusting the other's prose.

## 6. The checker

A conforming checker exposes one function:

```
check(passport, contract, proposed_use) -> { verdict, reason_codes[], safe_sentence, required_attribution }
```

`proposed_use` is structured (population, period, scope, causal_assertion, individual_prediction, recommendation, legal_conclusion, attribution_present). `safe_sentence` is the canonical template rendered with the passport's value and required qualifiers: what the writer may say if it says nothing more. A checker MAY also accept free text and derive `proposed_use` from it, but the structured form is the interface; text extraction is an implementation detail and its accuracy is the implementer's claim, not the standard's.

Reference implementation: the `check_claim_contract` tool on the FinanceRateCalc MCP server (https://frc-mcp.ziyetis.workers.dev), to be released as a standalone package taking any `claims.json`.

## 7. The fidelity test

Accuracy asks: did the system state the right value? Fidelity asks: did it state the value within its contract? A system can score 100% on the first and fail the second on every question, and that is the common case.

A fidelity test administers a fixed battery of questions whose answers are contracted claims, and grades each answer twice: value (from the passport) and fidelity (from the contract's verdicts). Reference administration: The Denial-AI Benchmark, Verdict Day 2026-09-15, eight systems, twelve questions, results at https://huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark. The battery, grading rubric and results are the empirical basis for this specification; a runnable task file (Inspect AI format) is the companion deliverable so that any laboratory can administer it without the publisher.

## 8. What this specification does not do

- It does not rank publishers or certify truth. A contract says how a number may be used; whether the number is correct is the passport's provenance and the reproduce file, checkable by anyone.
- It does not require signatures in 1.0. Integrity is sha256 plus public version history. Signatures are a 1.1 item.
- It does not restrict reading. Contracts govern restatement, not access; a site using this specification with a crawler block is misusing it.
- It does not encode opinions. `does_not_establish` lists inferences the data cannot support; it is not a place for the publisher's preferences.

## 9. Conformance levels

| level | requirement |
|---|---|
| **L1 Passport** | `/claims.json` + passports with required fields and correction logs |
| **L2 Contract** | L1 + a contract per claim with test vectors |
| **L3 Reproducible** | L2 + reproduce file per claim, and a public corrections log with dated entries |

FinanceRateCalc, 2026-09-15: L3 for 189 claims (self-assessed; independent reproduction status: none yet).

## 10. Adoption test

This specification is declared alive if, within 90 days of publication, at least one publisher other than the editor exposes a conforming `/claims.json`. If none does, that result is published at https://financeratecalc.com/null-results.html with the same date discipline as any other null result.

## Appendix A: JSON Schema

See `claim-contract-1.0.schema.json` alongside this document.

## Appendix B: Changes from the reference implementation (passport 0.1 / contract 0.1)

- `corrections` promoted from the site-wide log to a required per-claim array.
- `claim.n` (cell size) added as recommended.
- `needs_qualifier` verdict named explicitly; reason-code registry started.
- Test vectors made normative.
- Conformance levels introduced.
