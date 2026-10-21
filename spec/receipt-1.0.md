# Receipt 1.0 — receipts for published figures

Status: draft 1, 2026-10-21. License: CC BY 4.0. Reference implementation: FinanceRateCalc
(`https://financeratecalc.com/.well-known/receipt.json`). Conformance suite: `spec/receipt-conformance.mjs`.

## 1. The problem in one paragraph

A published number travels without its publisher. When it is restated — by a person, a page, or
a model — the reader cannot tell which version of the figure they are looking at, whether it has
since been corrected, or whether the publisher ever issued it at all. Receipt 1.0 gives a figure a
serial number that any reader can check: a short token next to the number, a public claim document
behind it, and one question the publisher answers for any token — *is this still current, and if
not, what replaced it?*

## 2. Design rules

1. **The claim is a document.** Every receipted figure has a public JSON document. The receipt is a
   hash of the document's claim block, so a verifier can recompute it without asking the publisher.
2. **Four answers, no more.** A verify request answers `current`, `stale`, `hash-current-value-mismatch`
   or `unrecognized`. There is no "valid"; a figure the publisher never issued is not stale, it is
   unrecognized.
3. **Corrections are data.** A stale receipt points to the correction that superseded it, from a
   machine-readable feed; the reader is routed to the fix, not to a search box.
4. **No model in the loop.** Hashing, verification and the corrections feed are deterministic.
5. **Nothing about the reader is recorded.** A verify request is answered without identifying who asked.

## 3. The manifest — `/.well-known/receipt.json`

A publisher declares itself in one file at the root of its canonical host.

```json
{
  "receipt": "1.0",
  "publisher": "FinanceRateCalc",
  "prefix": "FRC",
  "claims_index": "https://financeratecalc.com/claims/index.json",
  "claim_url_template": "https://financeratecalc.com/claims/{id}.json",
  "verify": "https://frc-mcp.ziyetis.workers.dev/verify?r={receipt}",
  "corrections": "https://financeratecalc.com/corrections.json",
  "hash_history": "https://financeratecalc.com/transparency/receipt-hash-history.json",
  "hash_rules": [
    {"id": "jcs-sha256-8", "current": true},
    {"id": "frc-0.1", "until": "2026-10-21", "note": "JSON.stringify(claim, sortedTopLevelKeys)"}
  ],
  "license": "CC BY 4.0"
}
```

| field | required | meaning |
|---|---|---|
| `receipt` | yes | spec version, `"1.0"` |
| `prefix` | yes | 2–8 uppercase letters or digits; the first segment of every receipt this publisher issues |
| `claims_index` | yes | JSON listing every receipted claim id (section 4) |
| `claim_url_template` | yes | where `{id}` resolves to the claim document |
| `verify` | yes | URL template; `{receipt}` is replaced by the URL-encoded receipt |
| `corrections` | yes | the corrections feed (section 7) |
| `hash_history` | no | every hash ever issued per id (section 8); without it a verifier cannot distinguish `stale` from `unrecognized` offline |
| `hash_rules` | yes | the rules under which receipts were issued; exactly one is `current` |

## 4. The claims index

`claims_index` is a JSON object with a `claims` array. Each entry carries at least `id` (the bare
claim id, without prefix) and `url` (the claim document). Entries may carry the publisher's own
prefixed id as well; a verifier uses `id`.

## 5. The claim document — `claim_url_template` with `{id}`

```json
{
  "receipt_document": "1.0",
  "id": "national-fha-denial-rate-2025",
  "display_value": "22.1%",
  "claim": {
    "metric": "fha_denial_rate",
    "value": 0.221,
    "unit": "share_of_decisioned_applications",
    "subject": "United States, all reporting lenders",
    "period": "2025",
    "definition": "denials (action 3) / decisioned applications (actions 1,2,3), FHA (loan_type 2)"
  },
  "hash_rule": "jcs-sha256-8",
  "hash8": "ebf6b00b",
  "receipt": "⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧",
  "issued_at": "2026-08-12T00:00:00Z",
  "provenance": {"primary_source": "CFPB/FFIEC HMDA public record, 2025"},
  "corrections_url": "https://financeratecalc.com/corrections.json",
  "license": "CC BY 4.0"
}
```

Required: `receipt_document`, `id`, `display_value`, `claim`, `hash_rule`, `hash8`, `receipt`.
Recommended: `issued_at`, `provenance` (what the figure was computed from), `use_boundary` (what it
must not be used for), `license`.

**The hashed block is `claim` and only `claim`.** Everything the figure means — value, unit,
population, period, definition — belongs inside it, because a change to any of them must change the
receipt. Everything about the document — dates, provenance, display string, the receipt itself —
stays outside, so it can be edited without re-issuing. `display_value` is the exact string that
appears in the receipt's value segment; a verifier compares strings, never numbers.

## 6. The receipt

```
⟦PREFIX:id:value:hash8⟧            minimal form
⟦PREFIX:id:value:hash8:channel⟧    with provenance segment
```

- `PREFIX` — from the manifest.
- `id` — `[a-z0-9-]+`, the bare claim id.
- `value` — the display value, verbatim, no colons.
- `hash8` — first 8 lowercase hex characters of SHA-256 over the canonical claim block.
- `channel` — optional, one letter and four digits (`f2610` = channel f, 2026-10); publisher-defined
  letters; not part of the hash. Says which door the receipt left through and when.

The brackets are U+27E6 and U+27E7. A verifier MUST also accept the bare form `PREFIX:id:value:hash8`,
because restatements drop the brackets.

**Hash rule `jcs-sha256-8`:** serialise the `claim` object per RFC 8785 (JSON Canonicalization
Scheme: members sorted by code point at every depth, no whitespace, numbers in ES6 shortest form,
UTF-8), hash with SHA-256, keep the first 8 hex characters. Eight characters identify a version of a
figure, not a signature; integrity against a hostile publisher is out of scope (section 9).

A publisher MAY list earlier rules in `hash_rules` with an `until` date. A receipt whose hash matches
the current claim block under any listed rule is **current**; the verify answer names the rule.

## 7. Verify

`GET` the manifest's `verify` URL with the receipt. The answer is JSON:

```json
{
  "receipt": "⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧",
  "id": "national-fha-denial-rate-2025",
  "quoted_value": "22.1%",
  "current_value": "22.1%",
  "status": "current",
  "hash_rule": "jcs-sha256-8",
  "claim_url": "https://financeratecalc.com/claims/national-fha-denial-rate-2025.json",
  "correction": null
}
```

| status | condition | reader's action |
|---|---|---|
| `current` | hash matches the current claim block (under any listed rule) and `quoted_value == display_value` | none |
| `hash-current-value-mismatch` | hash matches but the value segment differs | the copy was edited; use `current_value` |
| `stale` | hash matches none, but is listed in the publisher's hash history for this id | the figure was corrected; `correction` carries `date`, `title`, `old_value`, `new_value`, `url` |
| `unrecognized` | hash matches none and was never issued for this id | this publisher never issued the receipt as written; treat as unverified |

Other answers: a malformed receipt → HTTP 400 `{"valid": false, "reason": "not a receipt"}`; an id
with no claim document → HTTP 200 `{"valid": false, "reason": "unknown claim id"}`. A verifier MUST
NOT infer anything from an unknown id beyond "not this publisher's".

The answer MUST NOT set cookies or require authentication, and the publisher MUST NOT record who
asked beyond coarse aggregates (status, channel, requester class).

## 8. Corrections feed and hash history

`corrections` is JSON with `items`, each at least `{id, date, title, claim_ids[], url}` and, where a
value changed, `claim_values: {"<claim id>": {"old": "...", "new": "..."}}`. A verify answer for a
`stale` receipt selects the item whose `claim_values[id].old` equals the quoted value, else the
latest item naming the id.

`hash_history` is JSON `{"hashes": {"<id>": ["<hash8>", ...]}}` listing every hash the publisher has
issued for each id, under every rule. It is what makes `unrecognized` possible: a hash absent from it
was never issued. Publishers SHOULD regenerate it before every change to a claim block.

## 9. What this specification does not do

It does not prove the publisher is right: a receipt says *which* figure, from *whom*, and whether
it has *changed*; correctness is the publisher's method and other people's replication. It does not
sign anything; a publisher who wants non-repudiation signs the claims index or hash history (the
reference implementation timestamps its snapshot in a public transparency log). It does not define
the sentence a figure may appear in; that is a separate contract (`claim-contract-1.0-draft`).

## 10. Conformance

A publisher conforms when `spec/receipt-conformance.mjs <manifest-url>` passes every test:

1. manifest reachable, required fields present, exactly one current hash rule
2. claims index lists ≥ 1 claim; a sample of claim documents resolves
3. each sampled document carries the required fields and its `hash8` equals the recomputed `jcs-sha256-8` of its `claim`
4. each sampled document's `receipt` verifies `current`
5. a receipt with the value segment altered verifies `hash-current-value-mismatch`
6. a receipt with a never-issued hash verifies `unrecognized` and carries no correction
7. an unknown id answers HTTP 200 with `valid: false`
8. a malformed receipt answers HTTP 400
9. the bare (bracketless) form verifies the same as the bracketed form
10. the corrections feed parses and every item has `id`, `date`, `claim_ids`
11. if `hash_history` is declared: every sampled document's current hash is listed, and a hash from the history that is not current verifies `stale` with a correction object
12. the verify answer sets no cookie

The suite is deterministic and needs only `fetch`. Run it against your own host; publish the result.

## Appendix: changes from the FinanceRateCalc reference implementation

- Hash rule changed from `frc-0.1` (top-level-only key sort, which dropped nested keys) to RFC 8785 on
  2026-10-21; earlier receipts remain current via `hash_rules`.
- Every receipted id now has a claim document; before 2026-10-21 half were built on the fly.
- `display_value`, `hash_rule`, `hash8`, `receipt`, `receipt_document` added at the top level of
  existing passport documents (passport 0.1 fields retained).
