---
title: "FinanceRateCalc — receipts for the numbers AI quotes from public records"
url: https://financeratecalc.com/
note: The home page of financeratecalc.com as Markdown, generated from the same file as the HTML page. The receipt checker form and the interactive field of figures are left out; the receipts they show are in the text below.
---

# Numbers in the dark. Receipts bring the light.

AI systems quote statistics with the wrong month, the wrong denominator, or a value the publisher has since revised. Every figure here carries a **receipt**: a short code that fixes the number to its source file, its definition and its period. Move the light over a number to read its receipt, or [change one digit in the sentence below](#try) and watch the receipt catch it.

Point at any number in the field. Each one is a real figure from a public record, with the receipt that proves where it came from.

## Change one digit. See what a receipt does.

This sentence carries a receipt. Check it as issued, then change the number the way a careless quote would.

In 2025, Quoted value of decisioned FHA applications were denied. ⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧

Nothing has been checked yet. Press “Check this number”: the page asks the public verify service, the same one an AI agent or a newsroom script would ask.

Want the whole chain? [One figure, followed from a HUD report to an AI decision, with every check and who made it](https://financeratecalc.com/one-figure.html).

## Three receipts, as issued

- `⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧`
- Computed 262,250 denials of 1,187,606 FHA applications that reached a decision, 2025 federal HMDA record.[Check this receipt](https://financeratecalc.com/verify.html?r=⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧)
- `⟦FRC:va-national-denial-rate-2025:16.1%:32bdf09e⟧`
- Computed 115,026 denials of 712,121 VA applications that reached a decision, 2025.[Check this receipt](https://financeratecalc.com/verify.html?r=⟦FRC:va-national-denial-rate-2025:16.1%:32bdf09e⟧)
- `⟦FRC:official-hud-fhaprod-2026-08-refinance-count:20,681:430660e0⟧`
- Revised by the publisher HUD printed 20,681 refinance loans endorsed in the month for Aug 2026, then restated it as 20,682 one edition later. The report does not mark the change.[Check this receipt](https://financeratecalc.com/verify.html?r=⟦FRC:official-hud-fhaprod-2026-08-refinance-count:20,681:430660e0⟧)

## Revision watch: what the publisher changed without saying so

Official reports restate last month’s figures beside this month’s. When the restated number differs from the one first printed, that is a revision — and the report does not flag it. We compare every edition with the one before it and record each change on the original receipt. **3 silent revisions** found so far.

| Figure (HUD FHA production report) | Period | First printed | Restated as | Where |
| --- | --- | --- | --- | --- |
| Purchase loans endorsed in the month | Jul 2026 | 65,328 | 65,327 | Aug 2026 report |
| Refinance loans endorsed in the month | Jul 2026 | 22,210 | 22,212 | Aug 2026 report |
| Refinance loans endorsed in the month | Aug 2026 | 20,681 | 20,682 | Sep 2026 report |

[Every official figure and its revision status](https://financeratecalc.com/official-figures.html) · [revision ledger](https://financeratecalc.com/revision-ledger.html) · [revisions feed for machines](https://financeratecalc.com/data/revisions.json)

## Two kinds of receipt, and what each one attests

### Computed

We count the figure ourselves from the complete public file, with published code. The receipt binds the number to the file’s hash, the universe and the denominator.

- 1,187,606 FHA decisions in 2025; 22.1% denied
- A full rebuild reproduces 8,122 of 8,122 published fields
- An unaffiliated HMDA package arrives at the same counts

### Restated as printed

An agency published the figure; we compute nothing. The receipt binds the number to the official document’s hash, its table and row, its period — and records when a later edition changes it.

- HUD’s monthly FHA production report, 3 editions
- 3 figures already revised by the publisher, unmarked in the report
- An endorsement is not an application: the contract says so

## What carries a receipt today

| Figures | How | Receipts | Coverage |
| --- | --- | --- | --- |
| [FHA denial rates and application outcomes](https://financeratecalc.com/fha-denial-rates-top-100.html) | Computed from the 2025 federal HMDA file | 490 | National, 52 states and territories, 98 lenders, metro gaps, [five outcomes](https://financeratecalc.com/where-fha-applications-end.html) |
| [VA](https://financeratecalc.com/va-loan-denial-rates-2025.html), [USDA](https://financeratecalc.com/usda-loan-denial-rates-2025.html), [conventional](https://financeratecalc.com/conventional-loan-denial-rates-2025.html) denial rates and outcomes | Computed from the same file | 163 | National, states, five outcomes, one page per program. |
| [Purchase and refinance denial rates](https://financeratecalc.com/denominator-map.html) | Computed from the same file | 4 | The [denominator map](https://financeratecalc.com/denominator-map.html): every loan purpose, denominator and scope, so a rate quoted without one can be placed |
| [Official monthly figures](https://financeratecalc.com/official-figures.html) (HUD FHA production and loan performance; Ginnie Mae issuance; SBA 7(a) and 504 approvals) | Restated as printed from the official report | 59 | 11 editions, each bound to the PDF’s SHA-256. [Revision ledger](https://financeratecalc.com/revision-ledger.html): 312 figures compared across editions, 5 changed |
| **All receipts** |  | **716** | One file for machines: [llms-full.txt](https://financeratecalc.com/llms-full.txt) · signed snapshot in a [public log](https://financeratecalc.com/transparency/log.json) |

## We publish our own errors

A receipt is only worth something if the publisher admits when a number changes. The log has 35 dated entries; several were found because an AI system quoted a stale copy of ours exactly.

- 2026-11-27 Our own error, found 2026-11-27 while counting what was left of the May 2026 templates: five pages presented anonymous approval stories as…
- 2026-11-26 Our own error, found 2026-11-26 by an outside review of the site: two pages still invited readers to see which lender “fits your file”,…
- 2026-11-17 Our own error, found 2026-11-17 by counting every number printed on this site: about 6 in 100 carried a receipt

[Read the corrections log](https://financeratecalc.com/corrections.html) · [feed for machines](https://financeratecalc.com/corrections.json)

## How faithfully AI systems carry our figures

11 archived answers that quote us, graded on seven qualifiers: value, period, denominator, program, universe, no added claim, attribution. 1.00 means all seven survived.

| Answer engine | Answers | Score |
| --- | --- | --- |
| DeepSeek | 1 | 1.00 |
| ChatGPT | 2 | 0.93 |
| Meta AI | 2 | 0.93 |
| Perplexity | 1 | 0.86 |
| Engine not named | 5 | 0.71 |

[Method and every answer](https://financeratecalc.com/qualifier-survival.html) · [5 graded misquotes](https://financeratecalc.com/misquotes.html)

## Where to start

- **An AI gave me a number** Paste the receipt above, or [paste the whole answer](https://financeratecalc.com/check-answer.html): we mark what the number carries and what was added.
- **I was denied an FHA loan** [What the reason on your letter means](https://financeratecalc.com/denial-code-lookup.html) and what to ask the lender in writing. No prediction, no lender pick.
- **I report or research** The record: [100 largest FHA lenders](https://financeratecalc.com/fha-denial-rates-top-100.html), [every state](https://financeratecalc.com/fha-denial-rates-by-state.html), [metros](https://financeratecalc.com/metro/index.html), [why published rates differ](https://financeratecalc.com/why-fha-denial-rates-differ.html), [method](https://financeratecalc.com/methodology.html), [how to check us](https://financeratecalc.com/reconciliation.html). Writing for publication? [Put a receipt next to the number](https://financeratecalc.com/for-newsrooms.html).
- **I publish statistics** Put a live receipt next to your own numbers with [the free badge](https://financeratecalc.com/pricing.html), or have [receipts issued for your figures](https://financeratecalc.com/pricing.html). Want to know how AI systems restate your data? Ask for a [citation fidelity report](https://financeratecalc.com/pricing.html).
- **I use an AI assistant** [Add the connector](https://financeratecalc.com/connect.html) to Claude, ChatGPT, Grok, Le Chat, Manus, Gemini or Perplexity: one address, no account. Answers then carry a receipt you can check.
- **I build agents** [MCP server](https://financeratecalc.com/mcp-server.html) with 21 tools, [open datasets](https://financeratecalc.com/data-catalog.html), [the Receipt 1.0 format](https://financeratecalc.com/spec/receipt-1.0.md), [a reading proof for any document](https://financeratecalc.com/read-proof.html) and [a witness that signs it](https://financeratecalc.com/witness.html), [pricing](https://financeratecalc.com/pricing.html). Reading is free; the licence is [CC BY 4.0](https://financeratecalc.com/license.html).

[Every page](https://financeratecalc.com/site-index.html)[Metro pages](https://financeratecalc.com/metro/index.html)[Question pages](https://financeratecalc.com/stat/index.html)[City pages](https://financeratecalc.com/city/index.html)[Lender table](https://financeratecalc.com/fha-denial-rates-by-lender.html)[Denial reasons](https://financeratecalc.com/fha-denial-reasons-by-lender.html)[The door effect](https://financeratecalc.com/door-effect.html)[AI benchmark](https://financeratecalc.com/benchmark-scorecard.html)[Answers](https://financeratecalc.com/answers.html)[Tools](https://financeratecalc.com/tools.html)[Top-100 pack](https://financeratecalc.com/top-100-pack.html)[Glossary](https://financeratecalc.com/glossary.html)[Data](https://financeratecalc.com/data.html)

Published by Ziya Yetiş, 23 years in bank credit, working independently. No lender, servicer, vendor or AI company funds this site, and it carries no advertising. Figures are historical aggregates from public records: not predictions about any application, not ratings of any lender, not advice. Computed figures have been reproduced by an unaffiliated implementation and not yet by an unaffiliated person; [the specification for checking them is public](https://financeratecalc.com/reconciliation.html).
