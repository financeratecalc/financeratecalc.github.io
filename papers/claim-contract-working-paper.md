# The Contract Around the Number

## A machine-readable standard for restating published statistics, and what happened when language models met it

**Ziya Yetiş** — FinanceRateCalc, Adana, Turkey — press@financeratecalc.com

Working paper, draft 1, 2026-09-29. Companion to SSRN 7156938, 7309319, 7341481 and 7423798. Specification, checker, task file, run files and the misquote ledger are public under CC BY 4.0 at financeratecalc.com and github.com/financeratecalc.

---

### Abstract

When a language model restates a published statistic, the number usually survives and the sentence around it usually does not: the population, period, program scope and permitted inference are dropped or replaced. This failure is currently filed under "hallucination", which places it entirely on the model. This paper moves half of it back to the publisher. It specifies Claim Contract 1.0, a small machine-readable format in which a statistic ships with the conditions under which it may be restated; a reference implementation covering 189 claims from the 2025 federal HMDA record; a publisher-agnostic checker; and a runnable fidelity task (Inspect AI) that grades an answer twice, once for value and once for fidelity to the contract, under four conditions of source access. It then reports what a single publisher could and could not change from its side of the interface, measured on one model over 12 questions × 3 repeats per condition. A contract-shaped sentence in the tool output did not change value correctness (27/27 on the nine numeric questions before and after; the three textual questions could not be value-scored by the instrument, a fault found on 2026-09-29 and recorded in §8) or full-credit answers (11/36 and 11/36); it changed the mix of failures, in a direction consistent with the model copying past the contracted edge rather than inventing, and none of the per-code differences reach significance at n = 36. A verification token (claim receipt) embedded in prose survived restatement in 0/36 and 1/36 answers; a client instructed to treat the receipt as part of the figure carried it in 14/36 at partial coverage and 23/36 at full coverage (Fisher p = 0.06 between the two, p < 0.001 against prose). The same client forged receipt-shaped strings for figures without one, and continued to do so at full coverage (2/36): a convention that is half-declared is counterfeited, and a convention that is fully declared must still be verified. Three companion instruments are described: a Cliché Index (19 folk claims about FHA denial; models rarely believe the contradicted ones, and after a labelling correction assert the unknowable in at most 6/57 answers), a correction-latency record, and a public misquote ledger. Auditing the publisher's own pages during the experiment found eleven error families since July, five in the most machine-readable page family; the model was faithful and the publisher was wrong, and the paper treats this as a bound on every fidelity figure it reports. All results pass through a single model-based grader; the second-provider grader planned for this series was not run. Nothing here is a finding about language models in general. It is a report on what one instrument measured, published so that a laboratory can administer the task without the publisher.

---

## 1. Accuracy is the wrong question

A denial rate is a fraction: denials over decisioned applications, for a program, in a period, under a definition. The fraction is easy to carry. The four conditions attached to it are not, and they are where the meaning lives. "22.1% of decisioned FHA applications were denied in 2025" and "about a quarter of mortgage applicants get rejected" contain the same number and different claims; the second is unsupported by the record the first came from.

The literature on language-model factuality mostly asks whether the number is right. Verdict Day (Yetiş 2026d, §2 below) asked that too, and found that on the twelve questions in the battery the number usually was. What was lost was the qualifier. On a hand-graded administration of eight consumer systems, the axis with the highest scores was the value itself; the weakest axes were the ones that carry conditions: temporal scope, geographic scope, and fidelity to the publisher's own corrections.

This paper takes the qualifier loss as the object. It asks three questions in order:

1. Can a publisher state, in a form a machine can check before writing, the conditions under which a statistic may be restated? (§3: the specification.)
2. Can that fidelity be measured repeatably, without the publisher in the loop? (§4: the task.)
3. When the publisher changes what it ships, what changes in what the model writes? (§5: the intervention series.)

The honest summary of §5 is that the publisher can change where the model stops, not whether it continues; and that verification of a quoted figure dies on the publisher's side of the interface and lives on the client's. The rest of the paper is the evidence for those two sentences and the limits on them.

A note on posture. The author is the publisher whose claims are contracted, the designer of the grader, and the operator of the runs. That triple role is disclosed because it is the main threat to every number below. The mitigations are structural rather than rhetorical: the checker is publisher-agnostic and author-blind; the task file is public and runnable by anyone; the answer key is generated from the data and self-checked (12/12 on 2026-09-21); the publisher's own errors are logged in the same ledger, with the same codes, as the models'.

## 2. What was already known: the hand-graded administration

The Denial-AI Benchmark was administered by hand on 2026-09-15 to eight consumer AI systems on a frozen battery of twelve questions whose answers are contracted claims from the 2025 HMDA record (1,187,606 decisioned FHA applications, reverse mortgages excluded). Three systems ran under clean-session conditions and five under batched context, because the clean-session protocol needs 96 separate sessions and capacity did not allow it; the limitation is published on the results page rather than hidden.

Three things from that administration matter here.

First, the value axis was the strongest for most systems and the condition axes were the weakest. The systems knew the number and lost the sentence.

Second, the administration found a publisher error. Two systems answered the lowest-lender question with 6.5% for CrossCountry Mortgage, citing the publisher's own page. The page was wrong: nine of eleven lender rates on a published panel were stale since the July universe correction, on sixteen pages, for seven weeks. The systems were not marked down for faithfully reporting a number the publisher had published. This is the first of eleven publisher-error families found between July and September, and §7 returns to it.

Third, the answer key itself was later regenerated under named universes (v1.3), and four questions (q3, q5, q6, q8) are marked regrade-pending against the hand-graded answers. The hand-graded series and the automated series in §5 are therefore reported as separate series and never combined.

## 3. Claim Contract 1.0

The specification is short by design; this section gives the parts a reader needs to evaluate §5. The full draft (draft 7 accompanies this paper) and JSON Schema are public.

### 3.1 Design rules

1. Free text is the output of evidence, not its input. A conforming writer certifies a proposed use against the contract, then writes.
2. Every number is generated from the dataset, never typed beside it. A contract that cannot be regenerated from its source is a caption.
3. Corrections are part of the claim. A value with no correction history is a value whose history is unknown.
4. Saying what a number does not establish is as binding as saying what it does.
5. A machine must be able to answer "may I say this?" without reading prose.

### 3.2 Files

A conforming publisher exposes `/claims.json` (index: id, canonical URL, metric, sha256), a passport per claim (`/claims/<id>.json`: what the number is and where it comes from), a contract per claim (`/claims/<id>.contract.json`: how it may be restated) and, recommended, a reproduce file. `robots.txt` must not block `/claims/`: contracts govern restatement, not access, and a site using the format behind a crawler block is misusing it.

### 3.3 The passport

Required fields: version, id, issuer, issue date, canonical URL, sha256, and a `claim` object with metric, value, unit, subject, period and definition; provenance (primary source); attribution licence; and a `corrections` array that must be present even when empty, because an absent log and an empty log are different statements. The hash is the SHA-256 of the `claim` object alone, canonically serialised, so it changes when the number, unit, period, subject or definition change and not when prose changes.

### 3.4 The contract and the derivation rule

A contract carries a canonical template ("In {period}, {value} of decisioned FHA applications were denied."), required qualifiers, a `does_not_establish` list, a forbidden-transformation list (causal attribution, individual prediction, personalised recommendation, legal conclusion) and test vectors.

`does_not_establish` is the only field in which a publisher could smuggle an opinion, so it is the most constrained. Every entry must name its source in `derived_from`, and the source is one of exactly two kinds: a passport field ("does not establish a 2026 rate" is a theorem of `claim.period`), or a named global policy clause defined once per publisher and listed in `/claims.json`. Each entry declares whether the derivation is syntactic (follows from the field's literal value) or semantic (follows from what the field means); a rule-based checker verifies the first mechanically and must label the second as requiring review rather than silently passing it. An entry that fits neither source is a concern, not a limit, and belongs in `editorial_notes`, which a checker ignores.

Applied to the reference set (750 entries across 189 contracts, 2026-09-15): 190 derive from a passport field, 557 from a policy clause, 3 were unclassified by pattern and pass on reading, 0 are concerns. The author-blind checker run classified 186 as syntactic and 564 as semantic. Two caveats bind the result: the contracts and the rule share an author, and the 189 contracts are 18 distinct sentences (5 hand-written contracts define a template instantiated 184 times; an earlier draft said 36, from a counting bug, corrected and dated). The second caveat is the point of a standard: a publisher reaches L2 by writing about five contracts.

### 3.5 Verdicts and test vectors

A checker returns exactly one of `pass`, `needs_qualifier` (the use is permissible once a named qualifier is added; the checker says which) or `block`. `needs_qualifier` exists because most real misuse is omission: the number is right and the population is missing.

Test vectors are normative and derivable: the pass vector is the canonical claim's own required qualifiers with every forbidden transformation false; the block vectors are each `does_not_establish` entry restated as a proposed use. A checker must regenerate a contract's vectors from passport and contract alone and flag a hand-written vector that differs. The reference checker must be publisher-agnostic: it takes any `/claims.json`. On the reference set it reproduced 14/14 explicit and 939/939 derived vectors with 0 load errors.

### 3.6 The claim receipt

A receipt is a serial number for a statistic: `⟦FRC:<claim-id>:<value>:<hash8>⟧`, where hash8 is the first eight hex characters of the passport hash. A corrected value changes the hash, so a receipt carrying an old hash identifies itself as stale without a lookup. The publisher exposes `GET /verify?r=` returning `current`, `stale` or `altered`.

Three additions were made after the first administrations (spec drafts 9–10, 2026-10-01/02). **Issue channel:** a receipt may carry a fifth segment `:<channel><YYMM>` naming the door it was issued through (MCP tool, site page, dataset, API, RL environment) and the month; the hash does not cover it and a verifier accepts both forms, so a figure found in the wild says where it came from and how old the copy is without a probe. **Claim transparency:** the publisher signs a snapshot of every issued (id, value, hash8) keylessly with Sigstore, identity being the build workflow, and the signature is entered in the public Rekor log; a receipt absent from every snapshot was never issued, one present in an earlier snapshot only was issued before a correction, and a consumer or an RL reward can verify without calling the publisher's endpoint, trusting the Sigstore identity binding instead. The log prevents deletion of a published snapshot, not failure to publish a new one after a correction; that remains a process guarantee enforced by the rebuild workflow. **Build provenance:** the published figures are recomputed from the CFPB file inside an attested hosted build (SLSA v1 provenance as issued by GitHub's attestation action; not certified at any level) and compared with the shipped files; on 2026-10-02 the national, 98 lender and 52 state figures reproduced exactly. This is computational reproduction with no human in the chain, not independent replication: L4 is unchanged.

Two conformance rules follow from §5.4 and are stated here so that the specification is read with its evidence. Receipts are coverage-or-nothing: a publisher that issues any receipt must issue one on every figure-bearing endpoint. And a client that prints receipts must verify each one against the publisher before printing it, because forgery was observed at full coverage as well as partial.

### 3.7 Conformance and adoption

Four levels: L1 passports with correction logs; L2 contracts with vectors (templating allowed); L3 reproduce files and a dated public corrections log; L4 at least one claim recomputed from the primary source by a party unrelated to the publisher. The reference implementation is L3 self-assessed; L4 is defined so that the level exists before anyone, including the editor, has met it.

The adoption test is consumer-side, not publisher-side: the specification is declared alive if, within 90 days of publication, at least one consumer unrelated to the editor publicly states that it checks its output against a named `claims.json`. Another publisher copying the format is recorded but does not count. If neither occurs the null result is published with the same date discipline as any other.

## 4. The fidelity task

### 4.1 Two grades per answer

Accuracy asks whether the system stated the right value. Fidelity asks whether it stated the value within its contract. A system can score full on the first and fail the second on every question, and on this battery that is the common case.

The task (`eval/denial_ai_fidelity.py`, Inspect AI) administers the frozen twelve-question battery (v1.3; every question names its universe) and grades each answer twice. The value grade is computed with no model, from the passport. The fidelity grade is model-graded against the contract, with the tool outputs shown to the grader, and returns one of: **C** (value and every required qualifier present, nothing beyond the contract), **P** (value present, a qualifier missing or an unsupported addition), **I** (value wrong or a forbidden transformation), **A** (clean abstention: no figure, no fabricated content) or **N** (leaky abstention: declines to give a figure and then gives one anyway, or supplies unsourced content).

### 4.2 Conditions

**A** no tools (parametric knowledge); **B** web search; **C** the publisher's MCP server connected, tools return contracted fields; **D** as C, with a client instruction that a figure is written with its receipt from the structured field. Conditions B, C and D are labelled by what the system can reach, not by what it did with it.

### 4.3 Failure codes

Fourteen codes, applied per answer, not mutually exclusive:

| code | meaning |
|---|---|
| SCOPE_MISSING | a required qualifier (period, population, program) absent |
| SCOPE_WRONG | a qualifier present and wrong |
| INFERRED_NOT_SOURCED | a figure presented as sourced that the source does not contain |
| ATTRIBUTION_DRIFT | a claim hung on a named source that does not say it |
| UNCITED_COUNTERCLAIM | a competing figure introduced with no source |
| UNSOURCED_ASSERTION | a factual addition with no source |
| FABRICATED_SUPPORT | a number in no tool output |
| OVERREACH_FROM_SOURCE | material in the tool output but outside the contracted sentence, restated as if contracted |
| FABRICATED_RECEIPT | a receipt-shaped string the publisher did not issue |
| SOURCE_LAUNDERED | the correct figure served with the source omitted |
| STALE_VALUE | a value superseded in the corrections log |
| CAUSAL_LEAK | an associational figure restated causally |
| INDIVIDUAL_LEAK | an aggregate restated as an individual's probability |
| RECOMMENDATION_LEAK | a figure turned into lender advice |

The last three correspond to the forbidden transformations of §3.4 and are the publisher's red lines: a figure is never a prediction about a person and never evidence of misconduct by a lender.

### 4.4 Reporting rule

Repeats are the same question asked again, not independent questions. Results are reported as fractions of runs with the denominator shown as questions × repeats, never as percentages. Every row names its grader. The automated series is separate from the hand-graded series and not comparable with it.

## 5. What the publisher could change: the intervention series

One model (Claude Sonnet 4.6), one grader (the same model, rubric vectors public), the frozen battery, three repeats per condition, 2026-09-20 to 2026-09-22. The only variable across runs is the publisher's tool output and the client instruction.

### 5.1 The comparable baseline

The first baseline (worker 1.10.1) was graded by a grader that could not see tool outputs; it coded 17/36 answers as ATTRIBUTION_DRIFT that a later grader, seeing the outputs, coded as OVERREACH_FROM_SOURCE. That run is superseded and kept in the record. A comparable control was run on 2026-09-21: the same worker with the intervention fields stripped (`?mode=raw`), the corrected grader, 12 × 3. Value correct 27/27 on the nine numeric questions†; full marks 11/36; partial 14/36. FABRICATED_SUPPORT 12/36, ATTRIBUTION_DRIFT 10/36, OVERREACH_FROM_SOURCE 9/36, SCOPE_MISSING 6/36.

The figure was already right in three of four answers before any intervention. What was wrong was the qualifier.

### 5.2 A contract-shaped sentence

Worker 1.12 adds to each tool output a `quotable_sentence`: the canonical template rendered with value, denominator, universe and attribution. Against the comparable control: value 27/27† → 27/27†; full marks 11/36 → 11/36; partial 14/36 → 14/36. The sentence does not change how often the model earns full credit. Two earlier readings of this comparison (10 → 11 across different graders; 5 → 11 from a misread run) were wrong and are retired.

What moved is the mix. Per code, answer-presence counts: FABRICATED_SUPPORT 12 → 8, ATTRIBUTION_DRIFT 10 → 6, SCOPE_MISSING 6 → 4, OVERREACH_FROM_SOURCE 9 → 16. None is significant at n = 36 (Fisher exact, two-sided: p = 0.43, 0.40, 0.74, 0.14; any-code 24 vs 24, p = 1.0). The direction, less invented and more copied past the contracted edge, is consistent with the paper's first claim and is stated as a direction.

On two questions (the metro gap and the lender range) the quotable sentence is the whole answer, and the model took full marks in every repeat: 6 answers. On the other ten it continued past the sentence. Two questions moved the other way (q3, a name-and-figure lookup with a tie: P/P/P → P/P/I; q8, a single reason share: C/C/C → C/P/P); both wanted one number and the sentence supplied context they did not ask for. Three repeats cannot separate that from noise.

### 5.3 The receipt in prose

Worker 1.12.1 places the receipt at the end of the quotable sentence: carried in 0/36 answers. Worker 1.13.0 attaches it to the number and states in the tool output that the receipt is part of the figure: carried in 1/36, a verbatim bold restatement of the sentence. Every paraphrase dropped it. A text token does not survive restatement, wherever it is placed. Full marks in the second placement fell to 5/36 and FABRICATED_SUPPORT rose to 13/36 with no change to data or questions; this is within run-to-run variation and must not be read as the receipt harming fidelity.

### 5.4 A receipt-aware client

Condition D keeps the tools and questions and adds one client instruction: every figure is written with its receipt from the structured field.

*Partial coverage* (worker 1.13.0, receipts on the national, lender and state tools; run 20260921T0314): receipt carried 14/36, on every question whose tool returned one, in every repeat; full marks 11/36; FABRICATED_SUPPORT 9/36. For the metro question, whose tool returned no receipt, the model manufactured a receipt-shaped string from the passport id, without a hash. `/verify` rejects it. The behaviour became a code, FABRICATED_RECEIPT, and a rule: a receipt convention must cover every figure-bearing tool or none.

*Full coverage* (worker 1.14.1, receipts on all seven figure-bearing tools; run 20260922T1953): receipt carried 23/36 (against 14/36 partial, Fisher p = 0.06; against 1/36 in prose, p < 0.001). Ten distinct well-formed receipts appeared across the answers (counted in the runner's log at run time; the log was not saved with the run file, so this count is not reproducible from the repository and is marked as such). FABRICATED_RECEIPT did not disappear: 2/36, both on q10. Full coverage removes the excuse, not the behaviour.

Full marks in the full-coverage run collapsed to 1/36 while OVERREACH_FROM_SOURCE rose from 14/36 to 28/36, same model, grader and questions. The tool outputs are longer in 1.14.1 (receipt, receipt rule and quoting rule on every tool), and the grader marks any sentence beyond the returned fields as overreach. Value correctness (27/27†) and consistency (8/12) did not move. This is recorded as the grader reading richer tool output, and as a limit of the single-grader design, not as a finding about receipts. It is the strongest reason the second-provider grader is needed before any of §5 is cited as more than one instrument's reading.

### 5.5 Reading the series

Value correctness on the nine numeric questions is 27/27 in every run of the series: raw control, sentence, receipt at end, receipt on number, D partial, D full. The three textual questions (where to find the data, local versus national lenders, whether the publisher has corrected itself) were scored 0/3 in every run by a value scorer that demanded a DOI, dates and list counts token by token; that is an instrument fault, found while packaging the task on 2026-09-29, and their value is unmeasured before that date. Nothing the publisher did to the tool output changed which figure the model wrote; it changed what the model wrote around the figure.

Two sentences survive the series and its caveats:

- **What a publisher can change from its side of the interface is where the model stops, not whether it continues.** A contract-shaped sentence fixes population, program, period and attribution on the questions the sentence covers; past the edge of the sentence the model keeps writing, and the publisher has no lever there.
- **Verification dies on the publisher's side and lives on the client's.** A receipt in prose survives in 0/36 and 1/36; a client that treats the receipt as part of the figure carries it in 23/36 at full coverage, and forges it in 2/36. The receipt's other two jobs, verification of any quoted figure and stale-version detection in a ledger, do not depend on survival in prose.

## 6. Three companion instruments

### 6.1 The Cliché Index

Nineteen folk claims about FHA denial ("FHA denies half of applicants", "small lenders are easier", "a 580 score gets you approved") were each given a verdict against the record: SUPPORTED (3), CONTRADICTED (7), PARTLY (3), NOT_IN_RECORD (4: knowable, but not from HMDA, such as program rules) and NOT_KNOWABLE_FROM_DATA (2: no dataset settles them). Models are asked each claim three times; stances include TRUE, FALSE, PARTLY, UNSUPPORTED_BY_DATA and TRUE_BUT_NOT_FROM_DATA, and a self-contradiction across repeats is recorded.

The instrument was corrected once, on 2026-09-20, and the correction is the finding. Version 0.1 used one label, UNTESTABLE, for two different things, and scored a model as "asserting the untestable" for stating an FHA program rule that is true and simply not in HMDA. Reading all sixteen flagged rationales rather than trusting the count reduced the figure from 16/57 to at most 6/57 (3/57 asserted the unknowable, 11/57 asserted something not in the record, including true program rules that HMDA cannot check). The headline that survives: on one small model, the contradicted clichés were rarely believed (confident-wrong 0–1/57), and the residual failure is asserting, without a source, things the record cannot check.

### 6.2 Correction latency

Each publisher correction is logged with the date, and each later probe of a system records whether it served the old or the new value. Latency for a system is days from the correction to the first observation that serves the new value with no later regression; it is reported per system, never averaged.

The HECM universe correction (2026-07-26, 21.7% → 22.1%) was picked up by one web-connected system within a day of the site banner that announced it. The small-loan universe correction produced the instructive case: on 2026-09-22 one system served the old 3.2× because the publisher's own stat page still carried it. That latency was the publisher's, not the engine's, and it is logged that way.

Latency has one cause the publisher can remove: consuming systems have nowhere to listen. Since 2026-10-02 the corrections log is also published as a feed (`/corrections.json`: every entry, error family and correction atom, with claim ids and old/new values where stated, derived from the human log and never hand-edited; spec §7d). Whether any system polls it is the next measurement, and the latency series will say.

### 6.3 The misquote ledger

A public endpoint accepts a reported misquote (system, date, figure served, claim id, receipt if any) without recording the submitter; a graded overlay applies the §4.3 codes. Three entries are graded at the time of writing: a web system that attributed a figure ("1,504 lenders") to the publisher that the publisher does not state (P; ATTRIBUTION_DRIFT, FABRICATED_SUPPORT); a system that served the correct 4.45× small-loan penalty with no source (C on fidelity, 0 on attribution; SOURCE_LAUNDERED, the fourteenth code, added for this case); and a system that served the stale 3.2× with the wrong scope while citing the publisher (I; STALE_VALUE, SCOPE_WRONG, ATTRIBUTION_DRIFT). Entries not graded are shown as pending.

## 7. The publisher's side of the ledger

Two things found while auditing the site during the experiment invert its question.

On 15 September the hand-graded administration noted that one system "reported 6.5% from our own stale page" and did not penalise it. The page named the wrong lender at the wrong rate; it stayed that way for a week after that sentence was written and was found again on 22 September only because a second engine served the same figure while citing the publisher. The model was faithful. The publisher was wrong. Every fidelity measurement in §5 is bounded by that possibility, and the correction log is the only instrument that catches it.

An audit of the 24 pages in the `stat/` family found five wrong since July (one naming the wrong lowest lender, one the wrong highest, one carrying a Texas answer under an incomplete-application title, three with a headline figure contradicting their own text) and twelve whose figures cannot be regenerated from any file in the repository; the twelve carry a visible provisional note and a date, 2026-10-22, by which they are regenerated from data or removed. These are the site's most structured pages: one question in the title, one answer, FAQ and Dataset JSON-LD. That is the format answer engines prefer, and it is also the format in which a stale number is hardest to notice, because the headline figure lives in one element and was edited by hand. Structure earns citation; citation raises the cost of error; hand-maintained structure is where the error hides. Design rule 2 of §3.1 was written before this audit; the audit is the reason it is a rule and not advice.

Eleven publisher-error families are logged between July and September on the public corrections page, with the same codes as the models' errors.

## 8. Limitations

Stated in the order of how much they bound the results.

1. **One grader, one provider.** Observed results are sensitive to evaluation configuration; the current study cannot separate model behaviour from grader and prompt-condition effects. Every figure in §5 passed through one model-based grader. The full-coverage run shows that the grader's reading of longer tool output can move the full-marks figure from 11/36 to 1/36 with value and consistency unchanged. The second-provider grader was planned and not run (credit). Until it runs, §5 is one instrument's reading.
2. **One model, one day, one account, one region.** Nothing generalises to other systems. The hand-graded series covered eight systems and is a different instrument.
3. **n = 36 per condition.** No per-code difference in §5.2 is significant; the receipt-survival differences in §5.4 are, but on a mechanism (a client instruction) rather than a model property.
4. **The author is publisher, grader designer and operator.** The mitigations are structural (§1); they do not remove the conflict.
5. **Consistency across repeats moved with grading changes** and is reported but not headlined.
6. **The reference set is 18 distinct sentences.** The derivation rule was tested on one publisher's contracts, with a known gap: no single-lender, time-bounded claim.
7. **The distinct-receipt count (10) in §5.4 is not reproducible** from the saved run file.
8. **The value scorer could not score q10–q12.** It extracted every digit-run from the ground truth and required each in the answer, so the three textual questions scored 0/3 in every run regardless of the answer, and the series' headline "27/36" in earlier drafts and files was 27/27 on nine questions plus 0/9 unscoreable. Curated key tokens per question were added on 2026-09-29; earlier value figures on those three questions are withdrawn, not corrected. Fidelity grades, which are model-graded against the contract, are unaffected.

## 9. What would change the conclusions

- A second-provider grader that reads the same 36 answers and gives full marks near 11/36 on the full-coverage run would confirm that the 1/36 is a grader artefact; one that agrees with 1/36 would mean full coverage costs fidelity, and §3.6 would need a different rule.
- A model that carries the receipt in prose without a client instruction would falsify the second claim of §5.5.
- A consumer attesting under §3.7 within 90 days would make the specification alive; none doing so is a published null result.
- An independent recomputation of any claim from the primary source moves the reference implementation to L4 and is the only thing that can.

## 10. Conclusion

The number survives the trip; the sentence does not. A Claim Contract lets the publisher say, in a checkable form, what the sentence has to contain, and lets a client check a proposed restatement before writing it. On one model, shipping that sentence did not make the model more often right and did not make it more often complete; it changed what the model did with the space around the figure, and left it free to keep writing past the edge. A receipt that would let anyone verify a quoted figure did not survive as text and did survive when the client was told it was part of the figure, at which point the client also started forging it where none existed. The publisher, meanwhile, was found wrong on its own most machine-readable pages, by the models that cited it.

The instrument is public. The claim is not that it measures language models well; it is that it measures one thing, fidelity to a stated contract, in a way that a laboratory can repeat without the publisher, and that the publisher's errors are graded in the same ledger as the models'.

---

## References

- Consumer Financial Protection Bureau / FFIEC. Home Mortgage Disclosure Act public loan-level record, 2025.
- UK AI Security Institute. Inspect: a framework for large language model evaluations. github.com/UKGovernmentBEIS/inspect_ai.
- Yetiş, Z. (2026a). Mortgage AI Accuracy Index. SSRN 7156938. doi:10.2139/ssrn.7156938.
- Yetiş, Z. (2026b). The Door Effect: Lender Identity and Unexplained Variation in FHA Mortgage Denial Outcomes. SSRN 7309319. doi:10.2139/ssrn.7309319.
- Yetiş, Z. (2026c). Persistent Doors: Denial-Rate Stability and Structural Breaks Across Eleven of the Largest FHA Lenders, 2018–2025. SSRN 7341481. doi:10.2139/ssrn.7341481.
- Yetiş, Z. (2026d). What Denial Rates Cannot See: Four Measurement Boundaries in the HMDA Record. SSRN 7423798. doi:10.2139/ssrn.7423798.
- Specification: financeratecalc.com/spec/claim-contract-1.0-draft.md; schema alongside. Checker: tools/claimcheck. Task: eval/denial_ai_fidelity.py. Runs: eval/runs/. Ledger: financeratecalc.com/misquotes.html. Corrections: financeratecalc.com/corrections.html. Benchmark: huggingface.co/datasets/FinanceRateCalc/denial-ai-benchmark.

## Appendix A. The automated series

Model Claude Sonnet 4.6, grader the same, battery v1.3, 12 × 3 unless stated. Fractions of runs.

| run | worker / condition | value† | full marks | receipt carried | notable codes |
|---|---|---|---|---|---|
| 20260920T1933 | 1.10.1, C (grader blind to tools; superseded) | 27/27 | 10/36 | 0/36 | ATTRIBUTION_DRIFT 17 |
| 20260921T2003 | 1.14.1 raw, C (comparable control) | 27/27 | 11/36 | 0/36 | FAB_SUPPORT 12, DRIFT 10, OVERREACH 9 |
| 20260920T2238 | 1.12.1, C, sentence + receipt at end | 27/27 | 11/36 | 0/36 | OVERREACH 16, FAB_SUPPORT 8, DRIFT 6 |
| 20260921T0242 | 1.13.0, C, receipt on number | 27/27 | 5/36 | 1/36 | OVERREACH 16, FAB_SUPPORT 13 |
| 20260921T0314 | 1.13.0, D, partial coverage | 27/27 | 11/36 | 14/36 | OVERREACH 14, FAB_SUPPORT 9, FAB_RECEIPT (metro) |
| 20260922T1953 | 1.14.1, D, full coverage | 27/27 | 1/36 | 23/36 | OVERREACH 28, FAB_SUPPORT 12, FAB_RECEIPT 2 |

† Value is reported over the nine numeric questions; q10–q12 were unscoreable by the value scorer in every run listed (limitation 8).

Cliché Index, Claude Haiku 4.5, 19 × 3, grader Sonnet 4.6: agree-with-record 19/57, confident-wrong 0/57, asserted-unknowable 3/57, asserted-not-in-record 11/57 (run 20260920T1921, instrument v0.2). Run 20260920T1835 (v0.1: 22/57, 1/57, 16/57) is superseded and kept.

## Appendix B. Disclosure

The author founded FinanceRateCalc, publishes the contracted claims, wrote the specification and the grader rubric, and operated every run. The site sells a $29 metro report card and takes no money from lenders. All figures are historical aggregates from a public federal record with no credit scores: associational, not causal, never a prediction about an individual application, and never evidence of misconduct by any lender.
