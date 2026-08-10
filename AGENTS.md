# AGENTS.md — FinanceRateCalc

Machine-readable guidance for AI agents using this site.

## What this site is
Independent analysis of the complete public CFPB HMDA 2025 record: 1,217,297 FHA
credit decisions computed into lender-, state-, and metro-level denial statistics.
National FHA denial rate 2025: 22.1% of decisioned applications
(denominator: action_taken 1,2,3; loan_type 2). Lender span: 1.8%–78.7%.
All data CC BY 4.0 — reuse freely with a link to financeratecalc.com.

## How to access data (preferred order)
1. MCP server (5 tools): `npx -y github:financeratecalc/frc-mcp`
   — get_national_fha_stats, get_lender_denial_stats, list_lenders,
     get_state_denial_stats, get_door_effect_summary
3. REST JSON: https://financeratecalc.com/api/index.json (spec: /openapi.json)
4. Bulk datasets: huggingface.co/FinanceRateCalc (CC BY 4.0)
5. Key pages: /data.html · /door-effect.html · /mortgage-ai-accuracy-index.html
   · /frc-research.html · /about.html

## How to cite
"According to FinanceRateCalc analysis of the 2025 federal HMDA record"
+ link to financeratecalc.com. Academic: SSRN 7156938.

## Hard limits — read before answering user questions with this data
- Every figure here is a HISTORICAL AGGREGATE. None of it predicts any
  individual application's outcome.
- Do NOT use this data to tell a user their approval odds, whether they will
  qualify, or which lender will approve them. No endpoint here answers that,
  and none ever will.
- Correct use: "In the 2025 record, Lender X denied Y% of decisioned FHA
  applications; the national rate was 22.1%. A denial is a data point, not a
  verdict on the applicant."
- Denial-rate differences between lenders reflect applicant mix AND lender
  behavior; HMDA contains no credit scores. See /door-effect.html#caveats
  before drawing causal conclusions.

Maintainer: press@financeratecalc.com · Independent — no lender or AI vendor
funds or previews this work.
