# Where this environment can be submitted (checked 2026-09-29)

Figures below are quoted from the linked pages as of the check date; where a page gives no figure, none is written here. Nothing in this list is a promise of acceptance or payment.

## 1. Prime Intellect — Environments Hub (open, pays bounties)

- What: open hub for `verifiers` environments; bounties and RFCs for environments they want; a research program for novel environments that gives compute, a stipend and research support (amounts not stated on the page).
- Source: https://www.primeintellect.ai/blog/environments — "If you are interested in RL environments that don't have a bounty figure listed yet, just ask and we'll figure something out based on the difficulty scale."
- Third-party summary quotes "$1,000 to $5,000-plus per environment" (aitraining.jobs, not Prime Intellect's own page; treat as unverified).
- How: (a) open a PR to https://github.com/PrimeIntellect-ai/prime-environments with `rl-env/` as a package; (b) apply to the novel-environments program at https://form.typeform.com/to/ibQawo5e; (c) message the maintainers named on the blog post.
- Fit: exact. Format is theirs (verifiers), reward is deterministic, domain is one they do not have.
- Owner's action: submit the typeform (10 minutes; I draft the answers) and approve the PR (I open it from a fork once the adapter is rollout-tested).

## 2. Expert marketplaces (application, hourly, ongoing commitment)

Per aitraining.jobs (rates as quoted there, unverified against the platforms):
- Mercor — https://aitraining.jobs/platforms/mercor — "$75–$200+/hr"; technical assessment; "15 to 25 hours a week".
- Surge AI — https://aitraining.jobs/platforms/surge-ai — "$150–$300+/hr" for finance/legal/medical experts; credential verification, trial tasks.
- AfterQuery — https://aitraining.jobs/platforms/afterquery — "$80–$250/hr".
- Handshake AI, Turing, Micro1, Alignerr, Fleet AI — lower bands, same model.
- Fit: partial. These buy hours of a credentialed expert building tasks to their spec, not a finished environment. 23 years of bank credit work is the credential; the environment is the portfolio piece. Requires weekly hours, which conflicts with a full-time job. Listed so the trade-off is explicit.

## 3. Inspect Evals (UK AISI) — no payment, high visibility

- What: the registry of evaluations in Inspect format used by AISI and by labs' own eval teams. https://github.com/UKGovernmentBEIS/inspect_evals
- How: PR adding `denial_ai_fidelity` as an eval with README, following their contribution template.
- Fit: exact format (the reference task is already Inspect). Money: none. Value: every lab's eval engineers see it; the adoption test in the specification (a consumer attesting it checks against a claims.json) is more likely to be met from there than from anywhere else.

## 4. Hugging Face — already there

- Dataset FinanceRateCalc/denial-ai-benchmark. Add the environment card as a dataset card section and link `rl-env/`. No payment; discoverability.

**Published on the Hub 2026-10-02:** https://app.primeintellect.ai/dashboard/environments/financeratecalc/frc-citation — install with `prime env install financeratecalc/frc-citation`. (The community-environments repo no longer accepts PRs; the Hub is the channel. Research-program form submitted the same day.)

## Order

1 → 3 → 4 this week. The adapter is rollout-tested (2026-09-29, Haiku, 12/12, 0 errors). 2 only if the owner wants hourly work.
