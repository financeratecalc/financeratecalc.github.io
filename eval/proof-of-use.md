# Proof of use: who cites and verifies FinanceRateCalc figures

Generated 2026-11-09 from the public logs in this repository. Every number below links to its source file; nothing is estimated.

## 1. Named citations by AI answer engines (read by hand, archived verbatim)

10 recorded sightings across 5 sources (chatgpt.com, deepseek.com, meta.ai, perplexity.ai, statranker.org). Log: `eval/sightings.json`; answers: `eval/answer-engine-log/`.

- 2026-10-11 — statranker.org: US metro areas by FHA mortgage denial rate 2025; cites FinanceRateCalc data, methodology and corrections log as the source
- 2026-11-01 — perplexity.ai (answer engine): Three answers (highest-denial lenders; AmeriSave 2025; national rate and denominator) citing financeratecalc.com/answers.html, fha-denial-reasons-by-lender.html and five Hugging Face datasets; values and denominators correct; one stale value (NewRez 53.3%) traced to our own hub page and corrected the same evening (corrections #2026-11-01-lender-hub)
- 2026-11-03 — chatgpt.com (web search): One message, three questions (national rate and denominator; highest-denial lenders; AmeriSave): all figures and denominators exact, nine sources of which six are financeratecalc.com pages and two Hugging Face datasets
- 2026-11-03 — deepseek.com (search on; engine per owner): Same three questions: 3/3 exact with denominators; cites how-often, top-100 and the AmeriSave lender page, the HF dataset, and restates the July HECM correction correctly
- 2026-11-07 — perplexity.ai (answer engine): Discovery question on withdrawn vs denied shares: primary answer from a scarpero.com CSV (unexplained universe); FinanceRateCalc cited in a footnote via the HF benchmark dataset with the correct 22.1% / 1,187,606 and denominator
- 2026-11-07 — perplexity.ai (answer engine): DTI reason share question: FinanceRateCalc named as the source, figure (29.4%) and basis taken faithfully from the HF fingerprints mirror — which was stale on the superseded share-of-citations basis; corrected 2026-11-07
- 2026-11-09 — perplexity.ai (answer engine): Cited claims/national-fha-denial-rate-2025.json directly for the 22.1% figure, then derived it from another publisher's counts (96,258 / 754,290); primary answer again from the scarpero.com CSV
- 2026-11-09 — perplexity.ai (answer engine): ECOA code 18 question: cites denial-code-ecoa-18.html and denial-code-lookup.html (both rewritten 2026-11-07); answer structure follows the page (manual vs TOTAL, what to ask the lender); no figure quoted
- 2026-11-09 — meta.ai (answer engine): National figure 22.08% = 262,250 / 1,187,606 with denominator, HECM exclusion, reproducibility rule and the July correction restated exactly; withdrawn share not found and not invented
- 2026-11-09 — meta.ai (answer engine): Highest/lowest among the 100 largest: AmeriSave 78.7%, Flat Branch and Lakeview Community Capital 1.8%, quoted verbatim from answers.html with our caveat sentence; carried our stale 6.4% for CrossCountry (receipt 6.2%)

## 2. Fidelity of those citations (Qualifier Survival Index)

8 answers graded, mean QSI 0.857 of 1.0; by engine: Perplexity (web app, user se 0.857; ChatGPT (web search on, user 1.0; DeepSeek (search on) — engin 1.0; UNKNOWN — same engine as the 0.857; UNKNOWN — same engine as the 0.714; UNKNOWN — fourth engine, pas 0.571; Meta AI 0.928. Grader: `scripts/qualifier_survival.py`; page: /qualifier-survival.html.

Misquotes graded against the figure's use contract: 4 (`eval/misquotes-graded.json`, /misquotes.html).

## 3. Machine use, measured by us (not self-reported)

Worker usage snapshot 2026-11-09T13:56:04Z: 4,452 external calls over the logged window; 30 distinct client labels; receipt verifications 1,837 (1,566 returned `current`). Named non-FRC clients include: brickbluebot (502), rokmcp-probe (113), verifymcp-probe (71), brick.blue (69), ua-mcpcheckup-probe (32), sasame-audit (22), agent-index-prober (21), claude-code (12), faceabotprobe (11), ua-agent-collector (6), vouch-census (4), ua-agentforum (4). Source: `eval/usage-snapshot.json`, rebuilt daily.

Every figure carries a Receipt 1.0 receipt (`⟦FRC:id:value:hash8⟧`); verifying it at /verify is the usage signal. Spec: `spec/receipt-1.0.md`; conformance: 21 + 12 tests.

## 4. What is being used

- 2025 CFPB HMDA FHA record: 1,187,606 decisioned applications; national, 52 states, 319 metros, 98 lenders; application outcomes for 312 lenders; 9 open datasets on Hugging Face; MCP server with 17 tools (registry io.github.financeratecalc/frc-mcp).
- Reproduction: the full pipeline re-run on the CFPB file reproduces 8,122/8,122 published fields (`provenance/release-day-dryrun.json`); an unaffiliated implementation (hmda-analyzer) reproduces national, 52 states and 98 lender counts (`provenance/independent-reproduction.json`).
- Licence: CC BY 4.0 with attribution; machine-readable RSL 1.0 at /rsl.xml with a provenance reporting profile.
- Corrections: public log and feed (/corrections.json), 32 entries; stale copies found through engines' own citations are corrected and dated.

## 5. Independence

No lender, servicer, vendor or AI company funds this work. The query service is priced per call above a free quota; content is never paywalled.
