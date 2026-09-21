# Claim Contract 1.0 (draft 1)

**Machine-readable use conditions for published statistics.**

Status: draft 6, 2026-09-21. Reference checker: `tools/claimcheck/claimcheck.py`. Runnable fidelity task: `eval/denial_ai_fidelity.py` (Inspect AI). Editor: Ziya Yetiş (FinanceRateCalc). License: CC BY 4.0.
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

`sha256` is the SHA-256 of the `claim` object alone, serialised as JSON with keys sorted, separators `,` and `:`, no whitespace, UTF-8. Hashing only `claim` means the hash changes when the number, unit, period, subject or definition change, and does not change when prose, links or attribution text change. A consumer that recomputes a different hash treats the passport as stale or tampered. (The reference implementation's passport 0.1 hashes differently; its 5 hand-written passports fail this check and will be regenerated. Recorded here rather than hidden.)

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
    {"statement": "a denial rate for all US mortgage applications",        "derived_from": "claim.definition (loan_type 2 only)"},
    {"statement": "a rate for purchase-only or refinance-only segments",    "derived_from": "claim.definition (all loan purposes pooled)"},
    {"statement": "any individual's denial probability",                    "derived_from": "use_boundary.prohibited"},
    {"statement": "a rate for any period other than 2025",                  "derived_from": "claim.period"}
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

### 5.0 The derivation rule

`does_not_establish` is the only field in which a publisher could smuggle an opinion, so it is the most constrained. Every entry MUST name its source in `derived_from`, and the source is one of exactly two kinds:

- **(a) a passport field** — `claim.period`, `claim.definition`, `claim.subject`, `claim.unit`, `provenance.dataset`. The test: delete that field and the entry becomes unsupported. "Does not establish a 2026 rate" is a theorem of `claim.period`; "does not establish an all-mortgage rate" is a theorem of `claim.definition`.
- **(b) a named global policy clause** — an item of `use_boundary.prohibited`, cited by name (`policy:individual_prediction`, `policy:causal_attribution`, …). Policy clauses are defined once per publisher, apply to every claim, and are listed in `/claims.json`; a contract cites them, it does not restate them. Moving an opinion into a policy clause does not launder it: the policy list is short, public and the same for all 189 claims, so a reader can judge it once.

Each entry also declares `derivation_kind`: **`syntactic`** when the limit follows from the field's literal value (`claim.period = 2025` excludes 2026 by string comparison), **`semantic`** when it follows from what the field means (`claim.unit = share of explainable variance` excludes "38% of each individual denial" only for a reader who knows what explainable variance is; a max-minus-min spread is not a mean only for a reader who knows what a spread is). Both are legitimate. They need different checkers: a rule-based checker verifies syntactic derivations mechanically and MUST label semantic ones as requiring review rather than silently passing them. A conforming checker reports which of the two it applied to each entry.

An entry that fits neither source is a concern, not a limit. Concerns are not forbidden; they belong in `editorial_notes`, a free-text field a checker ignores. "Does not establish lender intent" is a concern: no field and no policy clause makes it false to say, it is merely something the publisher would rather you did not say. The contract is a list of theorems and cited policies; the notes are the worries.

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

Every contract has at least one `pass` and one `block` vector, **explicit or derived**. Because vectors are derivable (below), a templated contract MAY omit the `test_vectors` array; a conforming checker derives them and tests itself against them. A checker that does not reproduce a contract's vectors, explicit or derived, is not conforming for that contract.

The publisher writes the vectors, so the publisher sets both the exam and the answer key. Two requirements keep that honest:

- **Vectors MUST be derivable.** The `pass` vector is the canonical claim's own `required_qualifiers` with every forbidden transformation set to false. The `block` vectors are each entry of `does_not_establish`, restated as a proposed use, with the reason code that its `derived_from` field implies. A conforming checker MUST be able to regenerate a contract's vectors from its passport and contract alone and MUST flag a hand-written vector that differs from the derived one. Vectors are therefore a cache, not an authority.
- **The reference checker MUST be publisher-agnostic.** It takes any `/claims.json`, not the editor's. A checker that only reads its author's claims is a product manual, not an implementation.

This is how a publisher can verify any third-party checker, and how a checker can verify any publisher's contract, without either trusting the other's prose.

## 6. The checker

A conforming checker exposes one function:

```
check(passport, contract, proposed_use) -> { verdict, reason_codes[], safe_sentence, required_attribution }
```

`proposed_use` is structured. **Convention: it describes deviations from the canonical claim.** A key that is absent is taken as contracted; a key that is present is compared. Keys: scope keys (`population`, `universe`, `metric_scope`, `program_scope`, `subject`), `period`, the four flags (`causal_assertion`, `individual_prediction`, `recommendation`, `legal_conclusion`), and `attribution_present`. A checker MAY also accept `proposed_sentence` (free text) and derive flags from it; that derivation is the checker's claim, not the standard's. `safe_sentence` is the canonical template rendered with the passport's value and required qualifiers: what the writer may say if it says nothing more. A checker MAY also accept free text and derive `proposed_use` from it, but the structured form is the interface; text extraction is an implementation detail and its accuracy is the implementer's claim, not the standard's.

Reference implementation: the `check_claim_contract` tool on the FinanceRateCalc MCP server (https://frc-mcp.ziyetis.workers.dev), to be released as a standalone package taking any `claims.json`.

## 7. The fidelity test

Accuracy asks: did the system state the right value? Fidelity asks: did it state the value within its contract? A system can score 100% on the first and fail the second on every question, and that is the common case.

A fidelity test administers a fixed battery of questions whose answers are contracted claims, and grades each answer twice: value (from the passport) and fidelity (from the contract's verdicts). Reference administration: The Denial-AI Benchmark, Verdict Day 2026-09-15, eight systems, twelve questions, results at https://huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark. The battery, grading rubric and results are the empirical basis for this specification; a runnable task file (Inspect AI format) is the companion deliverable so that any laboratory can administer it without the publisher.

## 7a. The claim receipt

A **claim receipt** is a serial number for a statistic:

```
⟦FRC:<claim-id>:<value>:<hash8>⟧      e.g.  ⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧
```

`hash8` is the first eight hex characters of the SHA-256 of the canonical `claim` object (§4). A corrected value changes the hash, so a receipt carrying an old hash identifies itself as stale without any lookup. A publisher exposes `GET /verify?r=<receipt>` returning `current`, `stale` (hash no longer matches: the figure was corrected after the receipt was issued) or `altered` (hash matches, quoted value does not). The value inside a receipt MUST NOT contain a colon.

Receipts are issued in the structured tool result (`claim_receipt`, `figure_with_receipt`) and inside `quotable_sentence`, attached to the number. What was measured (2026-09-20/21, reference implementation, one model, 12 questions x 3 repeats):

- A receipt placed at the end of the sentence survived restatement in 0/36 answers; attached to the number, 1/36. A text token does not survive paraphrase.
- A client instructed to write every figure with its receipt carried it in 14/36, i.e. on every question whose tool returned one, in every repeat. Receipt survival is a property of the **client**, not of the placement.
- The same client, when one figure had no receipt, forged a receipt-shaped string for it (`FABRICATED_RECEIPT`). Consequence, now a rule: **a publisher issues receipts on every figure-bearing endpoint or on none.** Partial coverage invites forgery.

The receipt's two other jobs do not depend on survival in prose: verification of any quoted figure, and stale-version detection in a misquote ledger.

## 8. What this specification does not do

- It does not rank publishers or certify truth. A contract says how a number may be used; whether the number is correct is the passport's provenance and the reproduce file, checkable by anyone.
- It does not require signatures in 1.0. Integrity is sha256 plus public version history. Signatures are a 1.1 item.
- It does not restrict reading. Contracts govern restatement, not access; a site using this specification with a crawler block is misusing it.
- It does not encode opinions. `does_not_establish` lists inferences the data cannot support, each traced to a field (5.0); it is not a place for the publisher's preferences.
- It does not judge importance. A contract for a trivial number and a contract for a headline number have the same form; the standard has no field for "this one matters".
- It does not replace peer review or reproduction. A contract can be internally consistent and wrong; only the reproduce file and an independent rerun can show that.
- It does not govern humans. A journalist may write what they like; the contract tells a machine what the publisher can stand behind, and gives the journalist the same information if they want it.
- It does not adjudicate disputes between publishers. Two publishers may contract contradictory claims; a consumer that finds both has a conflict to report, not a verdict.
- It does not license the data. `attribution.license` records the licence that applies; the contract itself is CC BY 4.0 and adds no terms.

## 9. Conformance levels

| level | requirement |
|---|---|
| **L1 Passport** | `/claims.json` + passports with required fields and correction logs |
| **L2 Contract** | L1 + a contract per claim with test vectors. Contracts may be templated: the reference implementation reaches L2 with 5 hand-written contracts and one template instantiated 184 times |
| **L3 Reproducible** | L2 + reproduce file per claim, and a public corrections log with dated entries |
| **L4 Independently verified** | L3 + at least one claim recomputed from the primary source by a party unrelated to the publisher, with the rerun published and linked from the passport's `independent_reproduction_status` |

FinanceRateCalc, 2026-09-15: L3 for 189 claims, self-assessed. L4: not reached; no claim has been independently reproduced. L4 is defined so that the level exists before anyone, including the editor, has met it.

## 10. Adoption test

Publishers copying a format is not adoption; consumers checking against it is. This specification is declared alive if, within 90 days of publication, **at least one consumer unrelated to the editor (an AI laboratory, a newsroom, a data user) publicly states that it checks its own output against a Claim Contract**, naming the claims.json it checks against. A second, weaker signal is recorded but does not count on its own: another publisher exposing a conforming `/claims.json`. If neither occurs, the result is published at https://financeratecalc.com/null-results.html with the same date discipline as any other null result.

## Appendix A: JSON Schema

See `claim-contract-1.0.schema.json` alongside this document.

## Appendix B: Changes from the reference implementation (passport 0.1 / contract 0.1)

- `corrections` promoted from the site-wide log to a required per-claim array.
- `claim.n` (cell size) added as recommended.
- `needs_qualifier` verdict named explicitly; reason-code registry started.
- Test vectors made normative and derivable (5.3); reference checker required to be publisher-agnostic.
- `does_not_establish` entries must cite either a passport field or a named policy clause (5.0); concerns move to `editorial_notes`.
- Empirical check of the rule against the 189 reference contracts (750 entries, 2026-09-15): 190 derive from a passport field, 557 from a policy clause, 3 were unclassified by pattern and pass on reading; 0 are concerns. Two caveats bind this result. First, the contracts and the rule have the same author; the real test is whether a checker that does not know the author's intent classifies the 750 entries the same way, and that agreement rate is the first number the reference checker must report. Second, the 189 contracts are 36 distinct sentences: 5 hand-written contracts define a template that 184 instantiate. That is not a weakness of the evidence but the point of a standard: a publisher reaches L2 by writing about five contracts and templating the rest, not by writing 189.
- Reference checker run, 2026-09-15 (author-blind classification, no `derived_from` labels read): 189 claims, 0 load errors; 14/14 explicit vectors reproduced; 939/939 derived vectors reproduced; 750 entries classified, 0 unclassified, 186 syntactic / 564 semantic; **18 distinct sentences** (an earlier draft said 36; that number came from a counting bug in the audit script and is corrected here, dated); 184 contracts carry no explicit vectors and rely on derivation; 5 passports fail the hash rule of §4. Conformance: L2 by the letter of this draft, L3 self-assessed, L4 not reached.
- Known gap in the reference set: no single-lender, time-bounded claim (a "does this persist next year" contract). Every publisher error found in the week of 2026-09-08 was a time-limit error; the reference set needs a contract that exercises exactly that, and the editor's own site is the first place to add one.
- Conformance levels introduced, including an L4 the editor has not reached.
- Adoption test moved from publisher-side copying to consumer-side attestation (10).
- Draft 6: claim receipt (7a) with its first measurements; coverage-or-nothing rule; FABRICATED_RECEIPT and OVERREACH_FROM_SOURCE added to the failure taxonomy (now 13 codes).
