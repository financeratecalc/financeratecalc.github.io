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

## B. Prime Intellect Hub — DONE 2026-10-02

Published as `financeratecalc/frc-citation`: https://app.primeintellect.ai/dashboard/environments/financeratecalc/frc-citation. The PR route is closed upstream (pull requests disabled); the fork branch `financeratecalc/community-environments:frc-citation` holds the same package. Research-program form (A) submitted 2026-10-02. Inspect Register issue: https://github.com/UKGovernmentBEIS/inspect_evals/issues/2613.

## B (old). Pull request to PrimeIntellect-ai/prime-environments

Branch content: `rl-env/community/frc_citation/` copied to `environments/frc_citation/` (pyproject, module, README, questions.json, receipts-snapshot.json, outputs/). Title: "frc-citation: source-faithful citation of published statistics, deterministic rewards". Body: the paragraph above plus the rubric table from the README and the `vf-eval` line.

Needs a fork of prime-environments under the financeratecalc account (one click on GitHub: Fork). Then the branch is pushed from here and the PR opened.

## C. Inspect Evals Register (UK AISI) — issue, not PR

Inspect Evals no longer accepts code; evals are *registered* (pinned commit of the upstream repo). Requirements met on 2026-10-01: root `pyproject.toml` with `[project]` and `inspect_ai` dependency; `@task` functions in `eval/denial_ai_fidelity.py`; `eval/__init__.py`; assets pinnable via `FRC_SITE=<raw URL at commit>`.

Steps (yours, ~5 minutes): open https://github.com/UKGovernmentBEIS/inspect_evals/issues/new?template=register-submission.yml and fill:
- **arXiv URL**: the form asks for arXiv. We have SSRN only; enter the SSRN DOI of the fifth paper once posted (or https://doi.org/10.2139/ssrn.7156938 for the benchmark paper) and say so in the notes. If arXiv is mandatory, the paper must be posted to arXiv first (cs.CY/cs.CL; needs an endorser) — tell me and I prepare the arXiv version.
- **Source URL**: `https://github.com/financeratecalc/financeratecalc.github.io/blob/<40-char commit sha>/eval/denial_ai_fidelity.py#L199` (one task per issue; start with `denial_ai_fidelity_with_source`, line of its `def`). I will give you the exact URL with the SHA.
- **Maintainers**: your GitHub username.
A bot validates and opens the PR. Then two models' `.eval` logs for a full run go to their log uploader (we have Haiku and Sonnet logs as workflow artifacts; I will download and hand them to you).

## D. Perplexity publisher program — SENT 2026-10-02

Written application to press@perplexity.ai (no public program address exists), two offers: (1) the graded ledger entries on how Perplexity restates FRC figures (2026-09-20, 2026-09-22), (2) the correction feed `corrections.json` (spec §7d). No call requested. Follow-up: one resend on 2026-10-12 if no reply, then closed. Expected money if accepted: small (revenue share is pro-rated by citations and visits); expected value: first external acceptance, API/partner-team access for the feed.

## E. Publisher outreach (free 10-figure scan) — log

| date sent | publisher | channel | framing | follow-up due | status |
|---|---|---|---|---|---|
| 2026-10-04 | LendingTree | press mailbox | their own denial studies | 2026-10-14 | sent |
| 2026-10-04 | Bankrate | PR manager | rate-survey qualifiers | 2026-10-14 | sent |
| 2026-10-04 | NerdWallet | press mailbox | methodology notes dropped | 2026-10-14 | sent |
| 2026-10-04 | Zillow Research | press mailbox | "do you measure this?" | 2026-10-14 | sent |
| 2026-10-02 | Perplexity (publisher program) | press mailbox | ledger evidence + corrections feed | 2026-10-12 | sent |

Rule: one follow-up per publisher, ten days after the first email, then closed. Replies and scan deliveries are logged here with dates; no reply text is reproduced.
