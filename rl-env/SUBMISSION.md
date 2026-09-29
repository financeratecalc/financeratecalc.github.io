# Submission drafts (2026-09-29)

## A. Prime Intellect — novel environments research program (typeform)

Answers to paste. Adjust the personal fields.

**Name / affiliation:** Ziya Yetiş, FinanceRateCalc (independent; 23 years bank credit, one-person research site).

**Environment name:** frc-citation — source-faithful citation of published statistics with deterministic rewards.

**One paragraph:** A model answers 12 questions about US FHA mortgage denials by calling a live publisher's MCP tools (the complete 2025 federal HMDA record, 1,187,606 decisions), then must restate the figure inside its published use contract and carry the figure's claim receipt `⟦FRC:<id>:<value>:<hash8>⟧` verbatim. Rewards need no judge: value match from the answer key, receipt validity by recomputing the receipt hash from the publisher's data (offline snapshot of 386 claims, identical to the live `/verify`), penalties for forged receipts and for four red lines (individual prediction, lender recommendation, misconduct claims, causal claims). The gap it trains is the one frontier models currently fail: on the Inspect reference (Claude Sonnet 4.6, 12 × 3) the figure was right in every numeric answer while full contract credit was earned in 1/36 to 11/36 answers, the receipt survived in 0/36 as prose and 23/36 with a receipt-aware client, and a receipt was forged in 2/36 even at full coverage.

**Why novel:** existing citation/fact environments grade whether the number is right; this one grades whether the sentence around the number is right and verifiable, against a machine-readable contract the publisher ships (Claim Contract 1.0, draft spec included). The reward is a real verification protocol, not a rubric.

**Status:** verifiers 0.3.1 package (`validate` 12/12, one Haiku rollout: mean 0.75, 9/9 receipts valid, 0 forged) and a legacy-API package for community-environments with `vf-eval` outputs (mean 0.75). Inspect AI reference task with nine saved runs. All CC BY 4.0.

**What we would do with compute/stipend:** (1) scale the battery from 12 to ~200 questions by templating over 386 contracted claims; (2) train a small open model on the deterministic reward and publish whether receipt-carrying and non-forgery transfer to unseen claims; (3) a second, independent grader for the judged fidelity signal.

**Links:** https://github.com/financeratecalc/financeratecalc.github.io/tree/main/rl-env · spec: /spec/claim-contract-1.0-draft.md · runs: /eval/runs · https://financeratecalc.com/verdict-automated.html

## B. Pull request to PrimeIntellect-ai/prime-environments

Branch content: `rl-env/community/frc_citation/` copied to `environments/frc_citation/` (pyproject, module, README, questions.json, receipts-snapshot.json, outputs/). Title: "frc-citation: source-faithful citation of published statistics, deterministic rewards". Body: the paragraph above plus the rubric table from the README and the `vf-eval` line.

Needs a fork of prime-environments under the financeratecalc account (one click on GitHub: Fork). Then the branch is pushed from here and the PR opened.

## C. Inspect Evals (UK AISI) — PR

`eval/denial_ai_fidelity.py` + README following their template; no payment; after A/B.
