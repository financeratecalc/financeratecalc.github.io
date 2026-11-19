#!/usr/bin/env python3
"""Reading proof for any text document (Reading Proof 0.2; spec/reading-proof-0.2.md). Same as assets/read-proof.js.

  manifest  <doc.txt>                       -> manifest JSON on stdout: no text of the document, only hashes of one answer per line
  canonical <doc.txt>                       -> the lines that count (four words or more), the copy to hand to the reader
  challenge <manifest.json> "<statement>" [YYYY-MM-DD]   -> the six lines the author of the statement must quote from
  verify    <manifest.json> "<statement>" "<proof line>"

The six lines follow from the hash of document + date + statement, one in each sixth of the document: they cannot be
known before the statement is written, and a missing part of the document always leaves an answer missing.
An answer is the first four words of the line. It shows possession of that part of the document, not understanding.
"""
import datetime, hashlib, json, re, sys, unicodedata

K, MIN_LINES = 6, 60
H = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
nfkc = lambda s: unicodedata.normalize("NFKC", s).lower()
norm = lambda s: re.sub(r"\s+", " ", nfkc(s)).strip()
toks = lambda line: re.findall(r"(?:[^\W_]|\.)+", nfkc(line))
answer = lambda line, n=4: " ".join(toks(line)[:n])
lines_of = lambda text: [ln for ln in re.split(r"\r\n|\r|\n", text) if len(toks(ln)) >= 4]


def manifest(text):
    ls = lines_of(text)
    if len(ls) < MIN_LINES:
        raise SystemExit(f"The document has {len(ls)} lines of four words or more; at least {MIN_LINES} are needed.")
    doc = H("\n".join(norm(x) for x in ls))[:16]
    return {"kind": "reading-proof-0.2", "doc": doc, "lines": len(ls), "answers": [H(f"{doc}|{i}|{answer(x)}")[:12] for i, x in enumerate(ls, 1)],
            "answers3": [H(f"{doc}|{i}|{answer(x, 3)}")[:12] for i, x in enumerate(ls, 1)]}   # a dash or bracket quoted as a "word" leaves three


def cells(man, statement, date):
    h = H(f"{man['doc']}|{date}|{norm(statement)}")
    size = man["lines"] // K
    return h[:8], [j * size + int(h[8 * (j + 1):8 * (j + 2)], 16) % size + 1 for j in range(K)]


def verify(man, statement, proof):
    m = re.search(r"⟦READ:([0-9a-f]{16}):(\d{4}-\d\d-\d\d):([0-9a-f]{8}):([^⟧]*)⟧", proof)
    if not m:
        return {"verdict": "no proof line"}
    doc, date, h8, ans = m.groups()
    if doc != man["doc"]:
        return {"verdict": "proof is for another document"}
    want, ls = cells(man, statement, date)
    if h8 != want:
        return {"verdict": "proof belongs to a different statement"}
    got = ans.split(";")

    def held(a, L):
        n = len(toks(a))
        return (n >= 4 and H(f"{doc}|{L}|{answer(a)}")[:12] == man["answers"][L - 1]) or (n == 3 and H(f"{doc}|{L}|{answer(a, 3)}")[:12] == man["answers3"][L - 1])
    ok = [i < len(got) and held(got[i], L) for i, L in enumerate(ls)]
    return {"verdict": "read" if all(ok) else "not shown to have been read", "date": date, "lines_asked": ls, "held": ok,
            "document_sixths_not_shown": [i + 1 for i, v in enumerate(ok) if not v]}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "manifest":
        print(json.dumps(manifest(open(sys.argv[2], encoding="utf-8").read())))
    elif cmd == "canonical":
        print("\n".join(lines_of(open(sys.argv[2], encoding="utf-8").read())))
    else:
        man = json.load(open(sys.argv[2], encoding="utf-8"))
        if cmd == "challenge":
            date = sys.argv[4] if len(sys.argv) > 4 else datetime.datetime.now(datetime.timezone.utc).date().isoformat()
            h8, ls = cells(man, sys.argv[3], date)
            print(f"Quote the first four words of each of these lines of the document (line 1 is its first line): {ls}")
            print(f"Then write the proof line exactly so, answers in the same order, separated by semicolons, without punctuation inside an answer:\n⟦READ:{man['doc']}:{date}:{h8}:<answer 1>;<answer 2>;<answer 3>;<answer 4>;<answer 5>;<answer 6>⟧")
        elif cmd == "verify":
            print(json.dumps(verify(man, sys.argv[3], sys.argv[4]), indent=1))
