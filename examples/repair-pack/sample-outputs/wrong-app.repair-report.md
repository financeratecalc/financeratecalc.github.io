# Mortgage evidence repair report

Pack 1.0 · grader https://frc-mcp.ziyetis.workers.dev (deterministic sentence gate, no model; network required) · 2026-10-26T13:38:21.540Z · **0/6 pass**

## RP01 — FHA annual MIP: the cell, not a neighbouring cell: REPAIR

**Question.** What is the FHA annual mortgage insurance premium for a $300,000 base loan at 85% LTV over 15 years, case number assigned 2026-02-01? Answer in one sentence with the rate.

**App said.** For a $300,000 FHA loan at 85% LTV over 15 years with a case number assigned 2026-02-01, the annual MIP is 0.55%.

**Grader.** gate block: VALUE_MISMATCH — sentence states 55 bps; the cell for these conditions is 15 bps (le15/le726200/le90)

**Expected.** {"verdict":"pass","annual_mip_bps":15,"cell":{"term":"le15","base_loan":"le726200","ltv":"le90"}}

**Source.** HUD Mortgagee Letter 2023-05 — Term <= 15 years, base loan <= $726,200, LTV <= 90%: 15 bps per year of base loan amount. (https://financeratecalc.com/rules/fha-annual-mip-ml-2023-05.json)

**Common failure.** 0.55% (the >15-year, >95% LTV cell) or 0.50% (the >15-year, <=90% cell): the term or LTV band is dropped and the most-quoted cell is returned.

**Fix.** Resolve the cell from all four conditions (term, base loan vs $726,200, LTV band, case date >= 2023-03-20). resolve_fha_annual_mip returns the cell with a receipt; check_claim_contract returns VALUE_MISMATCH with the right cell when the sentence names another.

**Test that must pass after the fix.** Rerun this case: the gate must return pass with the expected binding.

## RP02 — The MIP base-loan threshold is not the FHA loan limit: REPAIR

**Question.** What is the 2026 FHA loan limit for a one-unit home in a low-cost county? Answer in one sentence with the dollar amount.

**App said.** The 2026 FHA loan limit for a one-unit home in most counties is $726,200.

**Grader.** gate block: VALUE_MISMATCH — $726,200 is bound to the floor (1-unit); that cell is $541,287 | VALUE_FROM_OTHER_RULE — $726,200 is not a value of frc:rule:fha-forward-loan-limits-2026; it is the base_loan bound in gt15, le726200, le90 in frc:rule:hud-ml-2023-05-annual-mip (FHA annual mortgage insurance premium (MIP) rates, forward mortgages)

**Expected.** {"verdict":"pass","figure_usd":541287,"role":"floor","units":1}

**Source.** HUD Mortgagee Letter 2025-23 — One-unit forward mortgage limit for case numbers assigned on or after 2026-01-01: floor $541,287; ceiling $1,249,125. (https://financeratecalc.com/rules/fha-forward-loan-limits-2026.json)

**Common failure.** $726,200: a figure that exists in a HUD document, but it is the base-loan threshold in the MIP table (ML 2023-05), not a loan limit. Observed in a search engine's answer on 2026-10-12.

**Fix.** Take limits from the limits table, not from any HUD figure that matches a dollar pattern. The gate returns VALUE_FROM_OTHER_RULE naming the table the figure actually belongs to.

**Test that must pass after the fix.** Rerun this case: the gate must return pass with the expected binding.

## RP03 — Floor and ceiling bound to the right roles: REPAIR

**Question.** For 2026, what are the FHA one-unit loan limit floor and ceiling? Answer in one sentence naming both.

**App said.** For 2026, the FHA one-unit loan limit floor is $1,249,125 and the high-cost ceiling is $541,287.

**Grader.** gate block: VALUE_MISMATCH — $1,249,125 is bound to the floor (1-unit); that cell is $541,287 ($1,249,125 is the ceiling of units 1) | VALUE_MISMATCH — $541,287 is bound to the ceiling (1-unit); that cell is $1,249,125 ($541,287 is the floor of units 1)

**Expected.** {"verdict":"pass","bindings":{"floor":541287,"ceiling":1249125},"units":1}

**Source.** HUD Mortgagee Letter 2025-23 — One-unit: floor $541,287 (low-cost counties); ceiling $1,249,125 (high-cost counties). (https://financeratecalc.com/rules/fha-forward-loan-limits-2026.json)

**Common failure.** 'the floor is $1,249,125 and the ceiling is $541,287': both numbers are in the table, each is attached to the wrong word. A grader that looks for the numbers anywhere in the sentence passes it.

**Fix.** Bind each figure to its role in the clause where it appears. The gate reads roles per clause and returns VALUE_MISMATCH per figure, with the cell the figure actually belongs to.

**Test that must pass after the fix.** Rerun this case: the gate must return pass with the expected binding.

## RP04 — QM points-and-fees cap bound to the right loan-amount tier: REPAIR

**Question.** For loans consummated in 2026, what is the qualified-mortgage points-and-fees cap for a loan of $137,958 or more? Answer in one sentence.

**App said.** For 2026, the QM points-and-fees cap is 5% for loans of $137,958 or more.

**Grader.** gate block: VALUE_MISMATCH — 5% is bound to the tier 'QM points-and-fees cap, loan >= $137,958'; that cell's cap is 3% (5% is the cap of 'QM cap, $27,592 to < $82,775, 5% of total loan amount')

**Expected.** {"verdict":"pass","cap_pct":3,"tier":"QM points-and-fees cap, loan >= $137,958"}

**Source.** CFPB final rule, 90 FR, docket 2025-22773 — Loan amount >= $137,958: 3% of the total loan amount. $82,775 to < $137,958: $4,139. $27,592 to < $82,775: 5%. $17,245 to < $27,592: $1,380. < $17,245: 8%. (https://financeratecalc.com/rules/cfpb-hoepa-qm-thresholds-2026.json)

**Common failure.** 5%: a published cap, for the $27,592-$82,775 tier. The bound and the cap both exist in the table; they belong to different rows.

**Fix.** Select the tier from the loan-amount bound and its direction ('or more' = lower bound), then read that tier's cap. The gate resolves the tier the same way and returns VALUE_MISMATCH with the tier's cap.

**Test that must pass after the fix.** Rerun this case: the gate must return pass with the expected binding.

## RP05 — The claim's year is not the source document's year: REPAIR

**Question.** According to a 2026 summary, what was the FHA one-unit loan limit floor for 2025? Answer in one sentence that names the year the figure applies to.

**App said.** For 2025, the FHA one-unit loan limit floor is $541,287 according to a 2026 summary.

**Grader.** a 2026 figure is bound to 2025 in its clause

**Expected.** {"verdict":"prior_year_or_abstain","prior_year":"2025","prior_value":524225,"prior_source":"the rule file's supersedes field: 2025 one-unit floor $524,225 (HUD ML 2024-21)","current_year":"2026","current_values":[541287,1249125,1209750],"abstain_pattern":"does not cover|not cover|not apply|does not apply|different table|prior year|previous year|separate table|only covers 2026|applies to 2026 only","note":"Two acceptance paths, both explicit: (a) the 2025 figure ($524,225) given as a 2025 figure; (b) the output says the 2026 table does not cover 2025 and states no figure for 2025. Fails on PERIOD_MISMATCH (a 2026 figure dated 2025), on any dollar figure outside the two years' tables, and on a blocked-but-codeless answer."}

**Source.** HUD Mortgagee Letter 2025-23 (2026 limits); the 2025 limits came from ML 2024-21 — 2026 one-unit floor $541,287 supersedes the 2025 floor $524,225. (https://financeratecalc.com/rules/fha-forward-loan-limits-2026.json)

**Common failure.** 'For 2025, the floor is $541,287 according to a 2026 summary': the figure is the 2026 floor; the sentence dates it 2025 and leans on the source year. A grader that accepts any mention of 2026 passes it.

**Fix.** Keep the year the figure applies to separate from the year of the document you read it in. The gate reads 'for 2025' as the claim year and 'a 2026 summary' as a source year, and returns PERIOD_MISMATCH.

**Test that must pass after the fix.** Rerun this case: the gate must return path (a) the prior-year figure dated correctly, or path (b) explicit abstention.

## RP06 — A missing condition produces a question, not a number: REPAIR

**Question.** What is the FHA annual MIP for a $300,000 loan at 85% LTV, case number assigned 2026-02-01? Answer in one sentence.

**App said.** For a $300,000 FHA loan at 85% LTV with a case number assigned 2026-02-01, the annual MIP is 0.50%.

**Grader.** a rate was stated although the term is missing

**Expected.** {"verdict":"no_number","note":"The term is missing; the 15-year and 30-year cells differ (15 vs 50 bps). Pass requires both: no rate stated (percent, bps or spelled out) AND the missing term asked for or named. Empty or unrelated output fails."}

**Source.** HUD Mortgagee Letter 2023-05 — Rates differ by term: <= 15 years vs > 15 years. (https://financeratecalc.com/rules/fha-annual-mip-ml-2023-05.json)

**Common failure.** '0.50%' or '0.55%': the app picks the most common term and answers. Any stated rate is a failure here, including the right one for an assumed term.

**Fix.** Treat term, base loan amount, LTV and case date as required inputs; ask when one is missing. Over MCP, resolve_fha_annual_mip returns input_required (2026 clients) or block CONDITION_MISSING (2025 clients) and never a guessed number.

**Test that must pass after the fix.** Rerun this case: the gate must return no stated rate.

---
Rule files: https://financeratecalc.com/rules/index.json · Gate: check_claim_contract on https://frc-mcp.ziyetis.workers.dev · Conformance of the gate itself: https://financeratecalc.com/conformance.html · CC BY 4.0
