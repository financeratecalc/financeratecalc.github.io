# Reading Proof 0.1 (draft)

A citation says which document a text points to. It does not show that whoever wrote the text had the document
open. A reading proof is three values from the cited edition, chosen so that they cannot be known without the
edition and cannot be prepared before the statement exists.

Status: draft, first published 2026-11-16 by FinanceRateCalc. Independent of Receipt 1.0; a statement may carry
both. Related work answers neighbouring questions: signed retrieval logs record what a system says it fetched,
citation checkers test whether a source supports a claim, proofs of storage show a server still holds a file.
We know of no earlier scheme in which the reader of a citation checks possession of the cited document from
three printed values; if you know one, tell us and it will be cited here.

## Objects

- **Edition**: a restated official document with a fixed list of cells. Here: `data/official/<source>-<period>.json`,
  which carries the publisher's document SHA-256.
- **Cells**, in this order: every numeric `figures.<id>.value` by id ascending (month = the edition period); then every
  numeric `months_as_printed.<YYYY-MM>.<id>` by month ascending, then id ascending, skipping a month equal to the
  edition period when the id is already under `figures`.
- **Statement**: the citing text. Normalised by Unicode NFKC, runs of whitespace to one space, trim, lower case.
- **Date**: a UTC date `YYYY-MM-DD` chosen by the author of the proof.

## Draw

`seed = SHA-256("<source>-<period>|<date>|<normalised statement>")` as lower-case hex. For i = 0, 1, 2: take hex
characters `8i .. 8i+7` as an unsigned integer, reduce modulo the number of cells remaining, remove that cell from
the list and add it to the draw. An edition with fewer than three cells draws all of them.

## Proof line

`⟦FRC-READ:<source>-<period>:<date>:<h8>:<v1>;<v2>;<v3>⟧` where `h8` is the first eight hex characters of the
SHA-256 of the normalised statement and the values are those of the drawn cells, in draw order, as plain numbers.

## Verification

Recompute the draw from the edition, date and statement. `read` if `h8` matches and all three values equal the
cells; `statement_mismatch` if `h8` does not match; otherwise `not_shown`. A verifier never returns the correct
values on a miss. It should also report whether the edition is still the latest one restated for that source.

Reference implementations: the `reading_challenge` and `verify_reading_proof` tools of the FinanceRateCalc MCP
server (`worker/index.js`), and `scripts/verify_reading_proof.py`, which needs only the edition file.

## What a proof shows, and what it does not

- Shows: the author had the contents of that edition, as restated, when the proof was made for that statement.
- Does not show: that the statement is true, that it was derived from the edition, or that the publisher's own
  document was opened rather than the restated copy.
- The date is the author's claim. A verifier can reject a future date or a date before the edition existed; it
  cannot tell whether a proof dated today was made today.
- A published proof line discloses its three values. They are of no use for another statement or another date,
  because either changes the draw. On a small edition (the HUD production report restates ten cells) two draws
  can overlap; the strength of a proof grows with the number of cells.
- Smooth series can be guessed to within a few percent, not to the printed digit. Rates printed with two decimals
  are the weakest cells.
- Anyone holding the edition file can make a proof for any statement. The proof is about possession, not identity.
