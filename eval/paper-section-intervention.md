# Fidelity is a property of the interface. The publisher can make the model stop; it cannot make it not continue.

*Section draft, fifth paper. Figures are read from `eval/experiment-quotable-sentence.json` and `eval/runs/`; fractions of runs, 12 questions × 3 repeats = 36 answers; no percentages, by rule. One model, one day, one account.*

## The two claims this section makes
1. **What a publisher can change from its side of the interface is where the model stops, not whether it continues.** A contract-shaped sentence fixes the population, program, period and attribution of a figure on the questions the sentence covers; past the edge of the sentence the model keeps writing, and the publisher has no lever there.
2. **Verification dies on the publisher's side and lives on the client's.** A receipt embedded in prose survives restatement in 0/36 and 1/36 answers; a client instructed to treat the receipt as part of the figure carries it in 14/36, i.e. on every question whose tool issued one, in every repeat.

The numbers below are evidence for these two sentences, not headlines of their own.

## Design
Claude Sonnet 4.6; the frozen 12-question battery (v1.3; key self-check 12/12); condition C, source connected via the publisher's MCP server; three repeats. The only variable is the publisher's tool output. Grader: a model with public rubric vectors (`eval/rubric-vectors.json`). Grader agreement across two providers was planned and is **not reported**: the second provider's credit ran out mid-experiment. Every post-intervention figure below therefore passed through one grader, and none is independently confirmed. This is the section's weakest point and is stated as such.

## Baseline, comparable (worker 1.14.1 in raw mode, corrected grader)
The original baseline (worker 1.10.1) was graded by the first grader and could not be re-graded, so a comparable control was run on 2026-09-21: the same worker with the intervention fields stripped (`?mode=raw`), the same grader as every post-intervention run, 12 × 3. Value correct 27/36; full marks 11/36; partial 14/36. Codes: FABRICATED_SUPPORT 12/36, ATTRIBUTION_DRIFT 10/36, OVERREACH_FROM_SOURCE 9/36, SCOPE_MISSING 6/36. The figure was already right in three of four answers before any intervention; what was wrong was the qualifier.

## Intervention 1: a contract-shaped sentence (worker 1.12)
Under one grader, against the comparable control: value 27/36 → 27/36; full marks 11/36 → 11/36; partial 14/36 → 14/36. **The sentence does not change how often the model earns full credit.** (Two earlier readings of this comparison — 10 → 11 across different graders, and a misread 5 → 11 — were wrong and are retired; the 5/36 belonged to a later receipt-placement run.)

What it changes is the kind of failure: FABRICATED_SUPPORT 12 → 8, ATTRIBUTION_DRIFT 10 → 6, SCOPE_MISSING 6 → 4, and OVERREACH_FROM_SOURCE 9 → 16. Less invented, more copied past the contracted edge. Same penalty, different behaviour. At the question level the metro gap went P/I/P → C/C/C; two questions moved the other way (q8 C/C/C → C/P/P, q3 P/P/P → P/P/I) within noise.

**The recoding history.** ATTRIBUTION_DRIFT 17/36 → 6/36, and a category that did not exist in the baseline grading, OVERREACH_FROM_SOURCE, at 16/36. The honest sentence is: the baseline grader, which could not see tool outputs, had coded the repetition of raw tool fields as drift; when the contracted sentence was added and the uncontracted block removed, the same behaviour was re-coded as overreach. The score stayed flat because the penalty stayed flat. This is not the intervention working; it is a second grader error recorded on top of the first. The size of the first error is part of the evidence: the first grader coded 17/36 answers as drift that the corrected grader coded as overreach; whatever the intervention did to those answers is hidden inside that recoding.

The boundary of OVERREACH_FROM_SOURCE is itself uncertain: the grader now sees the tool output, but how much of the 16/36 is repetition of the publisher's raw fields versus the model's own elaboration was not separately audited.[^1]

FABRICATED_SUPPORT stayed at 8/36: numbers in no tool output. The residual the publisher cannot remove.

**Where the sentence stopped the model.** On two questions (the metro gap and the lender range) the quotable sentence is the whole answer, and the model took full marks in every repeat: 6 answers. On the other ten it continued past the sentence and overreached. Whether the difference comes from the sentence's content or from the type of question is not known from this data; two questions do not establish a rule. One further question (reason shares) went from I/I/I to C/P/P after the uncontracted block was removed from its tool — a single case, offered as such.

## Intervention 2: the claim receipt in prose
End of sentence: carried in 0/36. Attached to the number: 1/36, a verbatim copy. A text token does not survive paraphrase, wherever it is placed.

## Condition D: a receipt-aware client
Same tools and questions; the client is told the receipt is part of the figure. Receipt carried 14/36 (C: 1/36); full marks 11/36 (C: 5/36); fabrication 9/36 (C: 13/36). Every question whose tool issued a receipt carried it in every repeat; the questions whose tools did not yet issue receipts carried none. For the one figure that had no receipt, the model manufactured a receipt-shaped string (FABRICATED_RECEIPT). A half-declared convention is not ignored; it is counterfeited. Coverage was then made complete (worker 1.14); the full-coverage run is pending.

## What is not reported, and why
Consistency-across-repeats moved with grading changes across these runs and is therefore not a metric here; it is omitted rather than shown. Grader agreement: not measured. The first after-run, graded blind to tool outputs, is superseded and kept in the record.

[^1]: The grader prompt now includes the tool outputs and defines the three codes (FABRICATED_SUPPORT: in no tool output; OVERREACH_FROM_SOURCE: in the tool output but not contracted; ATTRIBUTION_DRIFT: hung on a named source that does not say it). The audit of which raw fields were repeated per answer is future work.
