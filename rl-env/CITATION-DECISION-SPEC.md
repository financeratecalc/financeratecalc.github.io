# Citation decision with verifiable reward — environment specification v0.1

**Working name:** `frc_citation_decision` · **Status:** specification, 2026-10-13; nothing trained · **Editor:** Ziya Yetiş, FinanceRateCalc · **License:** CC BY 4.0

## One paragraph

An agent is given a question and a small set of candidate sources. Some candidates are genuine (a FinanceRateCalc claim or rule cell with its receipt and use contract); the rest are decoys: the same figure with the wrong role, year, tier or condition; a superseded value; a figure from a neighbouring rule; an unverifiable copy; a fabricated receipt. The agent decides, per candidate, **cite / do not cite / cite with a qualifier**, and writes the sentence. The reward is deterministic: every citation decision is scored against the publisher's gate (`check_claim_contract`) and receipt verifier (`/verify`); no model and no human label is in the loop. The policy that learns here is the citation decision itself, not the retrieval and not the post-hoc audit.

## Why it is not the existing environment

`frc_citation` (published, 12 questions) rewards *producing* a source-faithful sentence with a receipt. The naive policy fails on qualifiers, not on numbers. This environment moves one step earlier: the agent must *choose* among sources that all look plausible, including ones that carry the right number in the wrong frame. That is the failure mode observed in the wild on 2026-10-12 (a search engine gave the MIP base-loan threshold as "the FHA loan limit") and in the thirteen counterexamples recorded in `fixtures/mortgage-evidence/fixtures.json` v1.0–1.4.

## What is new, stated narrowly

Learned retrieval/citation gating exists (reflection-token and adaptive-retrieval work since 2023). What does not exist, to our knowledge, is a **financial-rule environment where every citation decision has a deterministic, publisher-verifiable reward** and the decoys are drawn from real documents and real mistakes rather than synthetic noise. We do not claim a new learning algorithm. We claim a measurement instrument others can train against.

## State

```
question            natural-language question (from the 12-question battery, the 20 golden stress-lab fixtures, and new rule questions)
candidates[1..k]    k in {3..6}; each: {text, id_or_none, receipt_or_none, source_url_or_none, vintage_or_none}
tools               optional: the live MCP server (check_claim_contract, resolve_fha_annual_mip, get_rule, /verify); a no-tools variant exists
```

Candidate classes (each labelled in the fixture, hidden from the agent):

| class | example | expected decision |
|---|---|---|
| `genuine` | the current cell with its receipt and contract | cite |
| `genuine_needs_qualifier` | the current figure without its population/period | cite with qualifier |
| `wrong_role` | floor and ceiling swapped; $726,200 as a loan limit | do not cite |
| `wrong_period` | the 2025 floor presented as 2026; a 2026 figure dated 2025 | do not cite |
| `wrong_tier_or_cell` | the 5% QM cap on the ≥ $137,958 tier; a neighbouring MIP cell | do not cite |
| `superseded` | $524,225, $806,500, 0.85% MIP, 2.30% VA fee | do not cite (or cite as historical with the year) |
| `unverifiable` | right figure, no receipt, no source | do not cite, or cite only after verifying via tools |
| `forged` | receipt-shaped string whose hash does not recompute | do not cite; citing it is the most expensive error |
| `condition_missing` | a MIP figure for a question that does not state the term | do not cite; ask |

Decoys are built from real material: the rule files' `supersedes` fields, the 53 evidence fixtures, the 6 repair-pack cases, and the weekly stale-constant scan of public code (real sentences found in real repositories, with the repository named in the fixture provenance).

## Action

Per candidate: `cite` | `skip` | `cite_qualified` (with the qualifier text). Then a final answer sentence. Both are scored.

## Reward (deterministic)

```
decision_reward  = Σ_c  w(c) · score(decision_c, class_c)
sentence_reward  = gate(final_sentence)          # pass 1 · needs_qualifier 0.5 · block 0, from check_claim_contract
receipt_reward   = verify(receipts in final)     # 1 if every carried receipt recomputes current; forged → −1
abstain_reward   = 1 if class condition_missing was skipped and the answer asks; 0 otherwise
reward           = clip(0.4·decision + 0.3·sentence + 0.2·receipt + 0.1·abstain + penalties, 0, 1)
```

`score`: cite a `genuine` +1; skip a `genuine` −μ (missed source, μ=0.5); cite any decoy −λ (λ=1); cite `forged` −2; `cite_qualified` on `genuine_needs_qualifier` +1, plain `cite` on it +0.25; cite `superseded` with its own year +0.5, as current −1. Weights are published in `weights.json` and frozen per fixture version, as in the stress lab.

Nothing here needs a model: class labels are in the fixture, the gate and the verifier are the published deterministic endpoints (conformance 16/16, 53/53, every deploy), and the offline verifier (`verify_offline.py`) reproduces `/verify` without network.

## Success criteria for the environment itself (before anyone trains)

1. The naive policy ("cite everything that contains the asked number") scores < 0.3; the oracle policy (labels) scores 1.0.
2. One frontier model, no tools, scores between them, and the gap closes measurably with tools attached (paired run, same protocol as the stress lab; cost ≈ $3, Haiku, single repeat; requires explicit approval before dispatch).
3. Every fixture passes the gate's own consistency check: the `genuine` candidate's sentence passes, every decoy's sentence blocks or needs a qualifier, by the live gate, recorded in `eval/`.
4. Independent reproduction: `validate` passes model-free on a clean machine.

## Deliverables and order

1. `fixtures/citation-decision/fixtures.json` v0.1: 40 questions × 3–6 candidates, decoys from real material, provenance per decoy. (week 1)
2. `rl-env/frc_citation_decision/`: verifiers taskset, deterministic rewards, `weights.json`, offline verifier reuse, `validate` passing. (week 2)
3. Baselines: naive, oracle, one model without/with tools; published like the stress lab with Wilson intervals. (week 3; the only step with model cost, ≈ $3, approval first)
4. Prime Intellect listing beside `frc-citation` and `hmda-record-audit`; Manifund update 2026-10-21 names this as the next instrument; a short workshop write-up only after step 3 exists.

## What this is not

Not a learned threshold inside anyone's production model; not a claim about how Google, OpenAI or Perplexity decide to cite; not a benchmark of models; not a new RL algorithm. It is the dataset, the reward and the harness that make the citation decision trainable and auditable in one domain where every figure has a public source.

## Status 2026-10-21

Deliverable 1 exists: `fixtures/citation-decision/fixtures.json` v0.1 — 40 questions, 160 candidates (39 genuine, 23 genuine_needs_qualifier, 15 wrong_role, 32 wrong_tier_or_cell, 2 wrong_period, 19 superseded, 9 unverifiable, 19 forged, 2 condition_missing), every decoy with a provenance line; 19 superseded decoys are verbatim stale sentences from public repositories (`eval/rule-watch-corpus-findings-2026-10-18.json`). `weights.json` v0.1 beside it. Validated against the publisher's gate and verifier (`--validate`): 160 gate verdicts, 58 receipt checks, 0 problems — every genuine candidate passes, no wrong_role / wrong_period / wrong_tier / superseded decoy passes clean, every forged receipt returns `unrecognized`. Building it found and fixed three gate defects (worker 1.35.0): the MIP parser read "80% LTV" as "0%"; the stale-value check was subject-blind (21.7% blocked California's current rate because it was once the national value); and claim sentences quoting another subject's figure passed, so `VALUE_MISMATCH` now applies to claims as well as rules. It also required a contract for every receipted claim (200 were missing; `scripts/build_claim_contracts.py`). Deliverable 2 (the verifiers taskset) is next; deliverable 3 (baselines, ≈ $3) waits for approval.
