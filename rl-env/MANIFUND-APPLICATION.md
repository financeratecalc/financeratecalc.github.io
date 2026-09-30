# Manifund project proposal (draft 1, 2026-09-30)

Paste into manifund.org → Create project. Fields follow their form; trim where a box has a limit.

---

## Title
Source-faithful citation: a self-verifying evaluation and RL environment for how models restate published statistics

## One-line summary
Frontier models get the number right and the sentence wrong. This project ships a public, model-free way to measure that (Claim Contract 1.0 + claim receipts), an Inspect eval and a verifiers RL environment with deterministic rewards, and uses a small grant to scale the battery, run a second-provider grader, and train a small open model on the reward.

## Project description

### The problem
When a language model restates a statistic, the value usually survives and the conditions around it do not: the population, the period, the program scope, the attribution, and what the figure does not establish. Today this is filed under "hallucination" and measured by whether the number is right. On our battery (12 questions about US FHA mortgage denials, answers computed from the complete 2025 federal HMDA record, 1,187,606 decisions), Claude Sonnet 4.6 got every numeric figure right in every repeat and earned full contract credit in between 1/36 and 11/36 answers. Asked to carry a verification token, it carried it in 0/36 as prose and 23/36 when told the token is part of the figure, and forged a token in 2/36 even when every tool issued a real one. Accuracy metrics see none of this.

### What exists (all public, CC BY 4.0, one person, no funding)
- **Claim Contract 1.0** (draft 7): a machine-readable format in which a publisher ships each statistic with its restatement conditions; a derivation rule that keeps opinions out (every "does not establish" entry must derive from a passport field or a named policy clause); test vectors that are derivable, so a checker can verify a publisher and a publisher can verify a checker without trusting prose. 189 contracted claims live; a publisher-agnostic checker reproduced 14/14 explicit and 939/939 derived vectors.
- **Claim receipts**: `⟦FRC:<id>:<value>:<hash8>⟧`, a hash of the canonical claim object, verifiable offline; corrected values change the hash, so a stale quote identifies itself.
- **An Inspect AI task** (UK AISI format) with four source-access conditions, a value scorer that uses no model, a fidelity grader with public rubric vectors, and a 14-code failure taxonomy (e.g. OVERREACH_FROM_SOURCE, FABRICATED_RECEIPT, SOURCE_LAUNDERED). Nine automated administrations saved as they came, grader named per row.
- **A verifiers RL environment** with deterministic rewards (value, receipt validity, forgery penalty, red-line penalty), `validate` 12/12, first rollouts on 2026-09-29 (mean reward 0.75, 9/9 receipts valid, 0 forged).
- **Companion instruments**: a Cliché Index (19 folk claims; models rarely believe the contradicted ones, and assert the unknowable in at most 6/57 answers after a labelling correction), a correction-latency record per engine, a public misquote ledger.
- **A working paper** (fifth in a series of four SSRN papers on the underlying data) and a corrections log in which the publisher's own twelve error families are graded with the same codes as the models'.

### What the grant funds (6 months)
1. **Scale the battery** from 12 to ~200 questions by templating over the 386 contracted claims, with the answer key generated from data and self-checked (the current key passes 12/12).
2. **Second-provider grading**: every fidelity result so far passed through one model grader; the second grader was blocked by API quota. Fund paid quotas on two providers and publish grader agreement per question.
3. **Train and publish**: fine-tune a small open model (7–8B) on the deterministic reward and report whether receipt-carrying and non-forgery transfer to held-out claims and to a second publisher's contracts. Null results published with the same date discipline as positive ones.
4. **A second publisher**: instantiate contracts for one unrelated public statistics publisher (government or academic), so the standard is tested outside its author's site; the adoption test in the spec (a consumer publicly attesting it checks against a claims.json within 90 days) is the pre-registered success criterion.

### Why this is AI safety work
It is a measurement of a specific honesty failure (faithful-looking restatement that silently drops the conditions under which a claim is true), in a regulated real-world domain, with a reward that cannot be gamed by pleasing a judge, and with the publisher's own errors in the same ledger. The environment is small, deterministic, and cheap to run, which is exactly what makes it reusable by other labs.

### Track record
Ziya Yetiş, 23 years in bank credit (Turkey), founder of FinanceRateCalc; four SSRN working papers on the HMDA record (7156938, 7309319, 7341481, 7423798); benchmark on Hugging Face; MCP server in the public registry; every measurement, correction and failed run public in the repository.

## Budget
Minimum funding: **$6,000** — API quotas for two providers (~$2,500 across ~200 questions × 3 repeats × 4 conditions × 2 graders), compute for one small fine-tune (~$1,500), the rest as stipend for six months of evenings.
Full funding: **$18,000** — adds the second-publisher instantiation, a third grader provider, and a part-time contractor to run the adoption test outreach.

## Links
- Repository (spec, checker, task, environment, runs, paper): https://github.com/financeratecalc/financeratecalc.github.io
- Environment card: /rl-env/README.md · Spec: /spec/claim-contract-1.0-draft.md · Automated series: https://financeratecalc.com/verdict-automated.html
- Corrections log (including our own instrument errors): https://financeratecalc.com/corrections.html
- Benchmark: https://huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark

## What would make this a failure
A second grader that disagrees with the first on most rows (the measurement is grader noise); a fine-tune that carries receipts only on seen claims (the reward teaches memorisation, not behaviour); no consumer attestation within 90 days of the spec's publication (the standard is a format nobody checks against). Each of these is published as a null result.
