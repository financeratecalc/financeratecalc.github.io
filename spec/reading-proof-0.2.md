# Reading Proof 0.2: any text document

Reading Proof 0.1 covered the official editions this site restates. 0.2 applies the same idea to any text document:
a statement about a document carries six short quotations, one from each sixth of the text, whose positions follow
from the statement itself. A reader whose copy was cut short, or had a stretch missing, cannot supply them.

Implementations: `scripts/read_proof.py` (Python) and `assets/read-proof.js` (browser, Node). `scripts/check_read_proof.mjs`
checks one against the other. Page: `/read-proof.html`.

## Terms

- **Normalise**: Unicode NFKC, lowercase, runs of whitespace to one space, trim.
- **Word**: a maximal run of letters, digits and full stops in the NFKC-lowercased line.
- **Counting line**: a line (split on CR LF, CR or LF) with four words or more. Other lines are dropped. The counting
  lines in order are the *canonical copy*; line 1 is the first of them. At least 60 are required.
- **Answer** of a line: its first four words joined by single spaces. The *short answer* is the first three.

## Manifest

```
doc      = first 16 hex of SHA-256( normalised counting lines joined by "\n" )
answers[i]  = first 12 hex of SHA-256( doc + "|" + i + "|" + answer of line i )        i from 1
answers3[i] = the same with the short answer
{ "kind": "reading-proof-0.2", "doc": doc, "lines": N, "answers": [...], "answers3": [...] }
```

The manifest holds no text of the document.

## Challenge

```
h     = SHA-256( doc + "|" + date + "|" + normalised statement )      date is YYYY-MM-DD, UTC
size  = floor(N / 6)
line_j = j*size + ( int(h[8(j+1) : 8(j+2)], 16) mod size ) + 1         j = 0..5
```

The challenge is issued after the statement exists. One changed character in the statement draws other lines.

## Proof line

```
⟦READ:<doc>:<date>:<first 8 hex of h>:<a1>;<a2>;<a3>;<a4>;<a5>;<a6>⟧
```

## Verification

1. `doc` equals the manifest's; the 8 hex equal those recomputed from the statement and the date in the line.
2. For each j: if the quoted answer has four words or more, its first four must hash to `answers[line_j]`; if it has
   exactly three, they must hash to `answers3[line_j]` (a dash or a bracket quoted as a "word" leaves three).
3. Verdict `read` when all six hold; otherwise `not shown to have been read`, with the sixths that failed.

## What it establishes

That the author of the proof line could read those six places of the canonical copy after the statement was written.

## What it does not establish

- That the statement is true, or follows from the document.
- That the whole document was read. An agent with file access that looks up only the six lines passes.
- Resistance to a forger who holds the manifest: an answer is four words. Where forgery matters, the manifest stays
  with the verifier.
- Anything about documents handed over as PDF or images: two extractors produce different lines. The canonical copy
  is the document for the purposes of the proof.

## First runs

`eval/read-proof/first-runs.json`: six single runs with one small model, on a generated agreement and on a real one.
A truncated copy and a copy with a gap both failed; the reader with the gap had answered correctly and had not
noticed the gap. The first real document also exposed a fault in the verifier (the three-word rule above).
