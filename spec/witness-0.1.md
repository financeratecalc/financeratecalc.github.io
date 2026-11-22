# Witness 0.1: a third party for a reading proof

A reading proof (spec/reading-proof-0.2.md) can be checked by anyone who holds the manifest. If the party that checks
is the reader itself, or its operator, nobody else has a reason to believe the result. A witness is a party that is
neither: it holds the manifest, draws the lines, checks the answers, and signs what happened.

Implementation: `worker/index.js` (the block beginning "Witness"), served at `https://financeratecalc.com/witness/`.
Test: `scripts/check_witness.mjs`. Page: `/witness.html`.

## Flow

1. `POST /witness/register {manifest}`. A Reading Proof 0.2 manifest: one hash per line in two readings, no text.
   The witness never returns it. A second, different manifest under the same document id is refused.
2. `POST /witness/challenge {doc, statement}`. The witness computes
   `h = SHA-256(doc | nonce | SHA-256(normalised statement))` with a fresh 128-bit nonce and returns six line numbers,
   one in each sixth of the document, as in Reading Proof 0.2. The challenge lives fifteen minutes.
3. `POST /witness/answer {challenge_id, answers[6]}`. One answer per challenge. An answer holds under either reading
   of "the first four words". The word MISSING is an answer that does not hold.
4. The witness returns and stores an attestation, whatever the outcome.

## Attestation

`payload` is a JSON string; the signature is over its UTF-8 bytes exactly as returned.

| field | meaning |
| --- | --- |
| `kind` | `frc-witness-0.1` |
| `id` | the challenge id, 16 hex |
| `seq`, `prev` | position in the witness's chain, and the SHA-256 of the previous payload (`null` for the first) |
| `doc`, `lines_in_document` | the registered document |
| `statement_sha256` | hash of the normalised statement; the statement is not stored |
| `nonce` | the number the lines were drawn from |
| `challenge_issued_at`, `answered_at`, `seconds_taken` | the witness's clock |
| `lines_asked`, `held`, `line_offsets` | the six lines, whether each was shown, and whether the quotation was of the line itself (0) or its neighbour (-1, 1) |
| `draw_number_for_this_statement` | how many times lines have been drawn for this document and statement |
| `verdict` | `read` when all six held, else `not shown to have been read` |
| `witness`, `key_id` | who signed |

`signature`: ECDSA P-256 with SHA-256, IEEE P1363 (r then s), base64url. Public key: `GET /witness/key`.
Line for a report: `⟦WITNESS:<id>:<shown>/6:<first 16 hex of SHA-256(payload)>⟧`.

## Why each field is there

- **The nonce**: without it the lines follow from the document and the statement alone, and a reader could work them
  out before stating anything.
- **One answer per challenge**: otherwise the witness becomes an oracle that confirms guesses.
- **The draw number**: six lines miss a small gap in a copy some of the time. A reader could ask again until they do.
  It cannot hide that it asked: the count is signed.
- **Seconds taken**: a reader holding the text answers in seconds. The number is recorded, not judged.
- **The chain**: the witness cannot quietly remove a failed reading or insert one with an earlier date without
  breaking every later `prev`. `GET /witness/status` gives the head.
- **Failures are signed too**: a witness that only records successes is an advertisement.

## What it does not establish

That the statement is true; that the document was understood; that every line was read; that the registered manifest
belongs to the document a relying party has in mind (compare the document id). A stolen or misused signing key voids
what is signed after the theft. The chain head is not yet anchored anywhere outside the witness.

## Price

Three witnessed readings per document are free. After that one prepaid credit per reading; a call without credit
gets HTTP 402 with a checkout link that a person has to confirm. Reading an attestation is free.
