#!/usr/bin/env python3
"""Every hash8 this publisher has ever published for each claim id: the dated epochs of
rl-env/frc_citation/fixtures/epoch-snapshot.json plus the current value. /verify and the
offline verifiers use it to tell a superseded receipt (hash in this history -> "stale",
with the correction) from one we never issued (hash nowhere -> "unrecognized": forged,
mistyped or truncated). Rerun after every data rebuild, before the current hash changes.
"""
import datetime, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8  # noqa: E402

snap = json.load(open(os.path.join(ROOT, "rl-env/frc_citation/fixtures/epoch-snapshot.json"), encoding="utf-8"))
out_path = os.path.join(ROOT, "transparency/receipt-hash-history.json")
prev = json.load(open(out_path, encoding="utf-8"))["hashes"] if os.path.exists(out_path) else {}
hist = {k: list(v) for k, v in prev.items()}
for ep, e in sorted(snap["snapshot"].items()):
    for cid, row in e["claims"].items():
        hist.setdefault(cid, [])
        if row["hash8"] not in hist[cid]:
            hist[cid].append(row["hash8"])
V = Verifier(ROOT)
for cid in list(hist):
    try:
        cur, obj = V.claim_object(cid)
        h = sha8(obj)
        if h not in hist[cid]:
            hist[cid].append(h)
    except Exception:
        pass
json.dump({"generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rule": "A hash8 listed here was published for that claim id at some date (epochs E0-E2 and the current value). A receipt whose hash is not listed was never issued by this publisher as written.",
           "epochs": {k: v["date"] for k, v in snap["snapshot"].items()}, "hashes": hist},
          open(out_path, "w", encoding="utf-8"), indent=0, ensure_ascii=False)
print(len(hist), "claim ids,", sum(len(v) for v in hist.values()), "hashes")
