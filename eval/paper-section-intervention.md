# Section draft — A publisher-side intervention on AI fidelity (measured 2026-09-20/21)

*Draft for the fifth paper. Every figure below is read from `eval/experiment-quotable-sentence.json` and `eval/runs/`; nothing is typed by hand. Fractions are of runs (12 questions × 3 repeats = 36 answers); no percentages, by rule.*

## Question
When an AI system has the source in hand — the publisher's own tools, returning the figure with its contract — does it restate the figure within that contract? And can the publisher change the answer from its side of the interface?

## Design
One model (Claude Sonnet 4.6), the frozen 12-question battery (v1.3, key self-check 12/12), condition C (source connected via MCP), three repeats. The only variable is the publisher's tool output. Grader: a model, with public rubric vectors; the grader was corrected once mid-experiment (see "Grader error").

## Baseline (worker 1.10.1)
Tool results returned raw fields. Value correct 27/36; full marks 10/36; consistent questions 4/12. The most frequent codes: ATTRIBUTION_DRIFT 17/36, CAUSAL_LEAK 7/36, INDIVIDUAL_LEAK 2/36, RECOMMENDATION_LEAK 4/36.

## Intervention 1 — a contract-shaped sentence (worker 1.12)
Every figure-bearing tool result gained `quotable_sentence`: the figure already inside its population, program, period and attribution. After the grader was corrected: value correct 27/36; full marks 11/36; consistent questions 4/12.

What moved: ATTRIBUTION_DRIFT 17/36 → 6/36. Most of what the baseline grader had called drift was a different thing, now coded OVERREACH_FROM_SOURCE (16/36): the model repeating raw context fields the tool returned and presenting them as the source's findings. Nothing invented; something promoted. The publisher can act on this — the uncontracted block was removed from the tool — and the question that depended on it went from I/I/I to C/P/P.

What did not move: FABRICATED_SUPPORT stayed at 8/36: numbers in no tool output. This is the residual a publisher cannot remove from its side.

Where the quotable sentence is the whole answer (the metro gap, the lender range) the model stops and takes full marks in every repeat. Where the model keeps writing past the sentence, it overreaches. The intervention works exactly to the edge of the sentence.

## Grader error (kept in the record)
The first after-run (20260920T2222) was graded by a grader that could not see the tool outputs; it coded OVERREACH as FABRICATED (17/36). The run is superseded and retained. Reading the rationales, not the counts, found it.

## Intervention 2 — the claim receipt
A serial number attached to the figure (⟦FRC:id:value:hash8⟧). Placement at end of sentence: carried in 0/36 answers. Attached to the number (worker 1.13): 1/36, and that one was a verbatim copy. A text token does not survive paraphrase.

## Condition D — a receipt-aware client
Same tools, same questions; the client is told the receipt is part of the figure. Receipt carried 14/36 (C: 1/36); full marks 11/36 (C: 5/36); fabrication 9/36 (C: 13/36). Every question whose tool returned a receipt carried it in every repeat; questions whose tools did not yet issue receipts carried none. For the one figure with no receipt, the model forged one (FABRICATED_RECEIPT). Coverage was then made complete (worker 1.14); the full-coverage run is pending (provider credit).

## What this establishes, and what it does not
- Fidelity is partly a property of the interface. Giving the model a contracted sentence fixes the population and attribution on the questions the sentence covers; it does not stop the model from continuing.
- A verifiable token survives only in a client that asks for it. The publisher cannot force it through prose; a convention on the client side can.
- A receipt convention must be complete or absent.
- n = 3 for one model. Consistency figures moved with grading changes and are not headlined. Two graders were planned; the second provider's credit was exhausted, so grader agreement is unreported for these runs.
