# Readers — twelve first-time readers of this site

Each file describes one person who has never seen financeratecalc.com, what they are looking for in fifteen minutes, and what breaks their trust. They exist to be handed to a fresh agent (no memory of the project) with one page and the instruction: *read as this person, report in the first person, be blunt.* Three of them read the site on 2026-10-20 and found 54 pages carrying two values for one figure, 1,753 pages still selling a product withdrawn on 4 September, and a methodology section describing a rule no figure used (corrections log, #2026-10-20-fresh-eyes).

Rules for a reading:
- The agent gets the page files, not our notes. It must not know what we think the page says.
- One reader per agent. Mixed readers average out; the point is the edge of each.
- Report format is fixed (see `_template.md`): landing, what I wanted, three moments I was lost or lost trust (quote the text), one moment the site earned trust, did I understand what the site is not, would I come back.
- Every concrete finding is verified against the files before it is acted on; a reader can be wrong.
- Findings that change a published figure or sentence go through the corrections log like any other error.

Run: `python3 scripts/run_readers.py --page index.html --readers 01,03,08` prints the prompts to hand to agents; results are kept in `eval/readers/<date>-<page>.md`.

| # | Reader | The question they carry |
|---|---|---|
| 01 | Denied borrower, Akron OH | What does this do for me today? |
| 02 | Lender chief compliance officer | Is this accurate, actionable, or a risk? |
| 03 | Mortgage trade reporter | Is there a story, and who signs it? |
| 04 | Fed / Urban Institute economist | Can I reproduce it; where is the error? |
| 05 | CFPB / HUD staffer | What are they getting wrong or leaving out? |
| 06 | Loan officer at a small lender | Is my employer named, and is it fair? |
| 07 | Bank credit manager in Türkiye | What would this be worth at home? |
| 08 | Sixteen-year-old | Say it in one sentence. |
| 09 | Blind reader with a screen reader | Can I use this at all? |
| 10 | Owner of a competing data site | What would I copy; where would I hit? |
| 11 | An answer engine's crawler | What am I indexing; what am I verifying? |
| 12 | Grant regrantor (Manifund) | Why should money go here? |
