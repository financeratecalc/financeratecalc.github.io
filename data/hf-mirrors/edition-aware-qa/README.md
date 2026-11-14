---
license: cc-by-4.0
task_categories:
- question-answering
language:
- en
tags:
- evaluation
- grounding
- provenance
- official-statistics
- finance
pretty_name: Edition-Aware QA (receipted figures from US public records)
size_categories:
- n<1K
---

# Edition-Aware QA: questions whose answer depends on the edition or the denominator

73 questions generated from figures that carry verifiable receipts at financeratecalc.com. Two things make a number wrong without being invented: the publisher printed a different value in a later edition, or the rate was computed on a different denominator. Each item tests one of them.

| Kind | Items | What it tests |
|---|---|---|
| as_printed | 36 | the figure as printed in a named edition of an official report |
| revised_between_editions | 2 | a figure two editions print differently; both values required |
| latest_edition_value | 2 | the later value; the first-printed value given as current fails |
| unchanged_between_editions | 13 | a figure the next edition restates unchanged |
| denominator_specified | 18 | one program and year, three denominators, three loan purposes |
| underspecified_rate | 2 | "the denial rate" asked without a definition; a bare number is incomplete |

## Why it is hard to contaminate

Items about an official edition are generated when the publisher releases it (monthly), from the document itself. An item about the September report cannot be in the training data of a model trained before that report existed. The set grows with each edition; the generating script and every source file are public.

## Scoring

Deterministic, no model: `scripts/build_edition_qa.py::score(answer_text, item)` in the publisher's repository. 1.0 = correct and complete; 0.5 = right number, required context missing; 0.0 = wrong, or a superseded value given as current.

## Sources and limits

Official figures are copied as printed from HUD's FHA Single Family Production Report, Ginnie Mae's monthly Issuance Summary and SBA's 7(a) and 504 activity file (US federal publications, public domain), each bound to the SHA-256 of its document. Rates are computed from the public CFPB HMDA 2025 loan-level file. The set does not establish why a publisher changed a figure, and a revision is not an error. Nothing here predicts any individual application or ranks any lender.

Verify any receipt: https://financeratecalc.com/verify.html. Revision ledger: https://financeratecalc.com/revision-ledger.html. Denominator map: https://financeratecalc.com/denominator-map.html. Licence: CC BY 4.0 (the official figures themselves are public domain).
