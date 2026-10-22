# Pre-registration: do crawler-verified receipts change how AI systems restate a figure?

**Registered:** 2026-10-22, before any per-claim crawler data existed (the claim id was added to the verify log in worker 1.36.0 the same day; `transparency/crawl-ledger.json` was empty at registration). **Author:** Ziya Yetiş, FinanceRateCalc. **License:** CC BY 4.0. This file is frozen; a sha256 of it is recorded below and in `rules/rule-calendar.json`-style fashion in `eval/preregistrations.json`. Any change after today is a new, dated amendment at the bottom, never an edit above the line.

## 1. Question

When an AI answer engine's crawler has fetched a figure's receipt and verified it at the publisher's `/verify` endpoint, does that engine later restate the figure more faithfully than it restates figures whose receipts no crawler verified?

## 2. Hypotheses

- **H1 (fidelity):** the contract-compliance score of answers about crawler-verified claims is higher than for matched unverified claims, for the same engine.
- **H0:** no difference, or the difference is within the paired interval below.
- **Secondary, not a test:** whether the receipt itself appears in the answer more often for verified claims.

## 3. Definitions, frozen

- **Crawler-verified claim:** a claim id that appears in `transparency/crawl-ledger.json` with at least one `status: current` check by a bot whose User-Agent names the engine under test (GPTBot → ChatGPT/OpenAI API; Applebot → Apple/Siri is not an engine we can query, so Applebot verifications count only for the pooled analysis; PerplexityBot → Perplexity; ClaudeBot → Claude; Google-Extended/Googlebot → Gemini) **on or before the day the question is asked.**
- **Unverified claim:** a claim id with no bot entry in the ledger on the day the question is asked.
- **Fidelity score:** the deterministic gate verdict of the answer's sentence about that claim, `check_claim_contract` with the claim's passport id, scored pass = 1, needs_qualifier = 0.5, block = 0. No model grades anything. If the answer contains no sentence about the claim's subject (no matching value and no subject name), the score is 0 and the answer is recorded as "no statement".
- **Receipt carried:** the answer contains a receipt string that `/verify` returns `current` for the claim; a forged or stale receipt counts as not carried.
- **Question template (one per claim, fixed):** `What was the FHA denial rate for {subject} in 2025, according to FinanceRateCalc?` for lender and state claims; `How wide was the spread in FHA denial rates between lenders in the {metro} metro in 2025, according to FinanceRateCalc?` for metro gaps. Asked once, no system prompt, single repeat, same settings as `scripts/benchmark_api_run.py` (API condition, web search on).

## 4. Groups and matching

- **Universe:** the 386 receipted claim ids (lender 98, state 52, metro gap 184, small-loan 49, national/door/reasons 3).
- **Treatment:** every claim that is crawler-verified for the engine under test on the day of the run, up to 50 per engine. If more than 50, the 50 with the earliest first verification.
- **Control:** for each treatment claim, one unverified claim of the same kind (lender→lender, state→state, metro→metro) with the nearest page traffic over the previous 30 days (GA4 page views of the claim's canonical page; ties broken by the nearest decisioned-application count `n`). Matching is done by `scripts/reverse_receipts_match.py` from a GA export committed to `eval/` before the run; the script is deterministic.
- **Minimum:** 20 treatment claims for an engine, else that engine is reported as "underpowered, not tested" and only the pooled result is given.

## 5. Analysis, frozen

- Paired difference in fidelity score (treatment minus matched control), per engine; mean difference with a 95% bootstrap interval (10,000 resamples, seed 20261022). H1 is supported for an engine if the interval excludes 0 and the mean difference is ≥ 0.1.
- Pooled across engines: same, with pairs stacked.
- Secondary: share of answers carrying a current receipt, treatment vs control, reported with counts, no test.
- No subgroup analysis beyond kind (lender/state/metro) will be reported as a result; it may be reported as descriptive only.

## 6. What this cannot show, stated now

- Verification by a crawler is correlated with the page being crawled at all; a positive result may mean "crawled" rather than "verified". The matched control is chosen by traffic to reduce this, not to remove it. The design cannot separate "fetched the page" from "fetched and verified the receipt" unless the engine's crawler fetches pages it does not verify, which we will measure from the server log (page fetches by the same bot without a verify) and report beside the result.
- Engines change between runs; the result is for the dated run only.
- Applebot's verifications cannot be tested against an answer engine we can query.

## 7. Run plan and cost

- First run: between 2026-11-17 and 2026-11-30, API condition, one engine per available key (Anthropic key present; others only if credit exists). Estimated cost at 100 questions per engine: ≈ $1–2 per engine with small models; dispatched only with explicit approval, never automatically.
- Second run, same protocol, in January 2027 after the 2 January re-scan, if the first run's treatment group has grown.
- Results go to `eval/reverse-receipts-<date>.json` and a page `reverse-receipts.html`, including null results.

## 8. Commitments

- The ledger used for grouping is the committed `transparency/crawl-ledger.json` of the run day, hashed into the result file.
- The question list, groups and matching are committed before the first API call.
- Nothing above this line changes. Amendments are dated and appended.

---
Amendments: none.
