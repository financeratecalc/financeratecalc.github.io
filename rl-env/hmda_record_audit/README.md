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
* Domain review: the rule selection and the arithmetic were reviewed by a bank credit officer (23 years);
  30 tasks were hand-checked (see `fixtures/review.md` once it exists).

## Run
```
pip install -e rl-env
cd rl-env && validate hmda-record-audit --runtime.type subprocess
```
Rollouts go through `.github/workflows/rl-env-smoke.yml` with `taskset=hmda-record-audit`.
License CC BY 4.0. Part of FinanceRateCalc; companion to `frc-citation`.
