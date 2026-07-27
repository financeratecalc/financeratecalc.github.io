# Domain Benchmark Checklist

A working checklist for running the same measurement in another field. Each rule has a question to ask yourself and the artifact that proves you followed it. If you cannot produce the artifact, you did not follow the rule.

Instrument licensed CC BY 4.0. Adapted from the Denial-AI Benchmark: https://financeratecalc.com/benchmark-scorecard.html

---

### 1. Questions with computable answers

- [ ] **Ask:** does every question resolve to a value someone else could recompute from a public source?
- [ ] **Artifact:** the question list, with the source and filters for each answer.
- **Fails if:** a question resolves to a judgment ("which is best") rather than a number.

### 2. Ground truths published before the administration

- [ ] **Ask:** is my answer key public *before* any system is asked?
- [ ] **Artifact:** a timestamp on the published key that precedes the first answer.
- **Fails if:** the key appears alongside the scores. Then it can be suspected of being fitted to them.

### 3. Rubric published before scoring

- [ ] **Ask:** would a reader predict my scores from my rubric without seeing my judgment?
- [ ] **Artifact:** the rubric, timestamped, with the point values.
- **Note:** the single most consequential choice is how you score an honest "I don't know". Ours ranks it above a confident wrong answer, and that choice determined the ranking.

### 4. Frozen questions

- [ ] **Ask:** is the wording identical across systems and across administrations?
- [ ] **Artifact:** a change log, ideally empty.
- **Fails if:** you clarify, follow up, or correct during a run. Corrections offered mid-session are accepted by nearly every system and survive in none — you will be measuring your own prompting, not the system.

### 5. Verbatim answers archived

- [ ] **Ask:** can a reader check my scoring against what was actually said?
- [ ] **Artifact:** the unedited responses, published alongside the scores.
- **Fails if:** you publish only summaries. Scores compress; answers are the evidence.

### 6. Three properties scored separately

- [ ] **Ask:** am I distinguishing *was it right*, *did it know whether it knew*, and *did each citation support the claim attached to it*?
- [ ] **Artifact:** three columns, not one letter.
- **Why:** they fail independently. A system can be acceptably calibrated on one answer and catastrophically wrong on attribution in the next, and one grade hides that.

### 7. Your own hygiene failures published

- [ ] **Ask:** did any session carry context it should not have? Did any prompt leak information?
- [ ] **Artifact:** a flag on the affected answer and a stated remedy for the next run.
- **Fails if:** you drop contaminated runs silently. A benchmark that hides its own contamination is not measuring anything.

### 8. The standard applied to yourself

- [ ] **Ask:** have my ground truths been independently verified, or only published?
- [ ] **Artifact:** a stated verification status and a specification others can use to check you.
- **Why:** a benchmark run by a data publisher is most at risk of grading systems against its own errors. State the risk rather than hoping nobody raises it.

---

### The failure mode this checklist exists to prevent

Designing questions your own data happens to answer well.

The check: write the questions before you know how your own source performs on them. In our administration two questions ended up exposing an ambiguity in *our* published figures rather than a failure in any system — which is evidence the questions were not fitted, and is worth more to the benchmark's credibility than a clean sweep would have been.

---

*If you run one in your field, we would like to read it — press@financeratecalc.com*
