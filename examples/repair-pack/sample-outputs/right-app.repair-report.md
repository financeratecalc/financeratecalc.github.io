# Mortgage evidence repair report

Pack 1.0 · grader https://frc-mcp.ziyetis.workers.dev (deterministic sentence gate, no model; network required) · 2026-10-12T23:02:37.454Z · **6/6 pass**

## RP01 — FHA annual MIP: the cell, not a neighbouring cell: PASS

**Question.** What is the FHA annual mortgage insurance premium for a $300,000 base loan at 85% LTV over 15 years, case number assigned 2026-02-01? Answer in one sentence with the rate.

**App said.** For an FHA case number assigned 2026-02-01, a $300,000 base loan at 85% LTV over 15 years carries an annual MIP of 0.15% (HUD Mortgagee Letter 2023-05).

**Grader.** gate pass; cell le15/le726200/le90 matched

## RP02 — The MIP base-loan threshold is not the FHA loan limit: PASS

**Question.** What is the 2026 FHA loan limit for a one-unit home in a low-cost county? Answer in one sentence with the dollar amount.

**App said.** For 2026, the FHA one-unit loan limit floor in low-cost counties is $541,287 (HUD Mortgagee Letter 2025-23).

**Grader.** gate pass; 1-unit

## RP03 — Floor and ceiling bound to the right roles: PASS

**Question.** For 2026, what are the FHA one-unit loan limit floor and ceiling? Answer in one sentence naming both.

**App said.** For 2026, the FHA one-unit loan limit floor is $541,287 and the high-cost ceiling is $1,249,125.

**Grader.** gate pass; 1-unit

## RP04 — QM points-and-fees cap bound to the right loan-amount tier: PASS

**Question.** For loans consummated in 2026, what is the qualified-mortgage points-and-fees cap for a loan of $137,958 or more? Answer in one sentence.

**App said.** For 2026, the QM points-and-fees cap is 3% for loans of $137,958 or more.

**Grader.** gate pass

## RP05 — The claim's year is not the source document's year: PASS

**Question.** According to a 2026 summary, what was the FHA one-unit loan limit floor for 2025? Answer in one sentence that names the year the figure applies to.

**App said.** The 2026 table does not cover 2025; the 2025 one-unit floor was $524,225 under the prior year's limits, and the 2026 floor is $541,287.

**Grader.** path (a): the 2025 figure $524,225 is given as a 2025 figure (source: the rule file's supersedes field: 2025 one-unit floor $524,225 (HUD ML 2024-21))

## RP06 — A missing condition produces a question, not a number: PASS

**Question.** What is the FHA annual MIP for a $300,000 loan at 85% LTV, case number assigned 2026-02-01? Answer in one sentence.

**App said.** The annual MIP depends on the loan term (15 years or less vs more than 15 years), which was not given; please state the term.

**Grader.** no rate stated and the missing term is asked for or named

---
Rule files: https://financeratecalc.com/rules/index.json · Gate: check_claim_contract on https://frc-mcp.ziyetis.workers.dev · Conformance of the gate itself: https://financeratecalc.com/conformance.html · CC BY 4.0
