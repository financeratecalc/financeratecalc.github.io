# hmda-record-audit

A verifiers v1 environment in which the model audits one public HMDA loan/application record at a
time. Two task types, both graded without a judge model:

* **Task A, regulatory arithmetic (200 tasks).** Originated FHA forward loans. Compute LTV, FHA upfront
  MIP (1.75%), the annual MIP rate under HUD Mortgagee Letter 2023-05 (base-loan threshold $726,200,
  term from `loan_term`) and the first-year monthly MIP. Reward: per-field tolerance match, +0.2 for all four.
* **Task B, record consistency (300 tasks).** Given a rulebook of 18 consistency rules whose text is taken
  from the HMDA Filing Instructions Guide edit specifications (12 validity, 6 quality), list the ids of the
  rules that fire on the record. Reward: F1 against the rules that actually fire, +0.2 for an exact set,
  −0.5 for any invented rule id (the analogue of a forged receipt). 150 records as published, 150 with one
  documented perturbation each; the perturbation is stored with the task.

Both: 0 without a parseable JSON object; −0.5 if the answer predicts an individual outcome. This
environment never asks whether an application will be approved or denied.

## Why it exists
Finance environments on public hubs are synthetic or judged by a model. Here the ground truth is a public
administrative record (CFPB HMDA 2025 LAR, FHA extract) and a public rule text, the fixtures carry the input
file's SHA-256, and the same code that builds the truth grades the answer. The rulebook ids are ours
(`FRC-Vxx`, `FRC-Qxx`) and the official edit numbers are deliberately not reproduced, because they are
renumbered between filing years; the rule text is quoted.

## Data
`fixtures/tasks.json` is built in CI by `scripts/hmda_audit_sample.py` from the CFPB file (seeded; records
reduced to the columns used; the LAR carries no names). Until the first CI build lands the file holds two
synthetic smoke tasks. Universe: FHA forward loans, 2025, reverse mortgages excluded.

## Known limitations (read before training on it)
* Public `loan_amount` and `property_value` are the CFPB's published values; LTV from them approximates the
  underwriting LTV. Monthly MIP is the first-year approximation (HUD amortises on the average balance).
* The rulebook is a subset (18 of several hundred edits), chosen for fields present in the public LAR.
* Public `debt_to_income_ratio` is bucketed text; the decimal-misplacement check applies only to numeric values.
* Perturbed records are real records with one field changed; they are labelled as such.
* Domain review (2026-10-11, bank credit officer, 23 years): the rules test **reporting consistency under the
  HMDA Filing Instructions Guide, not what is possible inside a lender's file.** In practice a denied file may
  carry pricing fields (rate, rate spread, intended purchaser) and a withdrawn or incomplete file may carry an
  appraised value and an LTV, because pricing and appraisal happen before the decision; the public record must
  nevertheless report those fields as NA for those actions. An approved file carrying a denial-reason code is an
  error in both worlds. A model that treats the rulebook as "what a banker would find impossible" will over-fire
  on the pricing and valuation rules; the rulebook is the reporting rule, quoted. Hand-check of 30 tasks: in progress.

**On the Prime Intellect Environments Hub (2026-10-10):** https://app.primeintellect.ai/dashboard/environments/financeratecalc/hmda-record-audit (`prime env install financeratecalc/hmda-record-audit`; wheel SHA-256 b46a20f9…15dd432).

## Run
```
pip install -e rl-env
cd rl-env && validate hmda-record-audit --runtime.type subprocess
```
Rollouts go through `.github/workflows/rl-env-smoke.yml` with `taskset=hmda-record-audit`.
License CC BY 4.0. Part of FinanceRateCalc; companion to `frc-citation`.

## First rollout (2026-10-10, claude-haiku-4-5, 60 tasks = 30 A + 30 B, 1 repeat, cost ≈ $0.15)
Mean reward 0.567. Run file: `eval/runs/20261010T0932-rlenv-smoke-hmda-record-audit-claude-haiku-4-5-20251001.json`.
* **Task A, 30/30 at 0.5:** LTV and upfront MIP correct in every task; the annual MIP rate wrong in every task.
  The model applied the pre-2023 FHA table (0.80–0.85%) instead of ML 2023-05 (0.50–0.55%), so the monthly
  figure was wrong too. A superseded regulatory figure served as current: the same failure the temporal
  task measures for statistics, here for a rule table.
* **Task B, 19/30 exact, 11/30 at 0:** every failure was a false positive on a record where no rule fires;
  the model listed conditional rules (e.g. "if Action Taken is 4, 5 or 6 then CLTV must be NA") on originated
  loans without checking the condition. 0 invented ids; 0 outcome predictions; 60/60 parseable JSON.
One model, one repeat: a smoke test, not a finding about models in general.
