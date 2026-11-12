#!/usr/bin/env python3
"""Regenerate rl-env/frc_citation/receipts-snapshot.json: every claim id the publisher issues
receipts for, with its current value and hash8, computed from the data files exactly as the
worker's /verify does. This file is what gets signed into the Sigstore transparency log
(.github/workflows/claims-transparency.yml), so a receipt can be verified without the publisher.
"""
import sys, os, json, glob, datetime, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8, sha8_legacy

v = Verifier(ROOT)
ids = ["national-fha-denial-rate-2025", "door-effect-38pct-2026", "small-loan-penalty-range-2025", "denial-reason-shares-top100-2025"]
ids += [f"lender-{os.path.basename(f)[:-5]}-2025" for f in sorted(glob.glob(os.path.join(ROOT, "api/lender/*.json")))]
ids += [f"state-{os.path.basename(f)[:-5]}-2025" for f in sorted(glob.glob(os.path.join(ROOT, "api/state/*.json")))]
ids += [os.path.basename(f)[:-5] for f in sorted(glob.glob(os.path.join(ROOT, "claims/metro-gap-*.json"))) if not f.endswith(".contract.json")]
d = json.load(open(os.path.join(ROOT, "api/small-loan-penalty.json")))
ids += [f"small-loan-penalty-{r['state'].lower()}-2025" for r in d["ranked"]]
op = os.path.join(ROOT, "data/application-outcomes-2025.json")
if os.path.exists(op):
    ids += [f"outcome-{k}-2025" for k in ("originated", "approved-not-accepted", "denied", "withdrawn", "closed-incomplete", "ana-share")]
    ids += [f"outcome-{l['slug']}-2025" for l in json.load(open(op))["lenders"] if l.get("slug")]
for f in sorted(glob.glob(os.path.join(ROOT, "data/programs/*-2025.json"))):
    d = json.load(open(f, encoding="utf-8")); prog = os.path.basename(f)[:-10]
    ids += [f"{prog}-national-denial-rate-2025"] + [f"{prog}-state-{s['state'].lower()}-denial-rate-2025" for s in d["states"]]
    ids += [f"outcome-{prog}-{k}-2025" for k in ("originated", "approved-not-accepted", "denied", "withdrawn", "closed-incomplete")]
for f in sorted(glob.glob(os.path.join(ROOT, "data/purpose/*-2025.json"))):
    prog = os.path.basename(f)[:-10]
    ids += [f"purpose-{prog}-purchase-denial-rate-2025", f"purpose-{prog}-refinance-denial-rate-2025"]
for f in sorted(glob.glob(os.path.join(ROOT, "data/official/*.json"))):
    if os.path.basename(f) == "index.json":
        continue
    d = json.load(open(f, encoding="utf-8"))
    ids += [f"official-{d['source_id']}-{d['period']}-{fid}" for fid in d["figures"]]
snap, bad = {}, []
for cid in ids:
    try:
        cur, obj = v.claim_object(cid); snap[cid] = {"value": cur, "hash8": sha8(obj), "hash8_legacy": sha8_legacy(obj)}
    except Exception as e:
        bad.append([cid, str(e)[:80]])
out_path = os.path.join(ROOT, "rl-env/frc_citation/receipts-snapshot.json")
prev = {}
if os.path.exists(out_path):
    try: prev = json.load(open(out_path)).get("receipts", {})
    except Exception: prev = {}
changed = sorted(k for k in snap if k in prev and prev[k] != snap[k])
added = sorted(k for k in snap if k not in prev); removed = sorted(k for k in prev if k not in snap)
out = {"generated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
       "source": "financeratecalc.github.io main; claim objects = the claim block of /claims/<id>.json; hash8 = first 8 hex of SHA-256 of the RFC 8785 canonical claim block (Receipt 1.0, hash rule jcs-sha256-8)", "hash_rule": "jcs-sha256-8",
       "count": len(snap), "unresolved": bad, "receipts": snap}
body = json.dumps(out, indent=0, ensure_ascii=False, sort_keys=False)
open(out_path, "w", encoding="utf-8").write(body)
digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
print(json.dumps({"count": len(snap), "unresolved": len(bad), "changed": changed, "added": added, "removed": removed, "sha256": digest}))
