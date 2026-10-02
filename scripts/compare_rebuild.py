#!/usr/bin/env python3
"""Compare a fresh rebuild (frc_rebuild.json from scripts/reference_implementation.py, run in CI
on the CFPB file) against the published data files. Writes provenance/rebuild-report.json.
Exit 0 whether or not they match: a mismatch is a finding to publish, not a build failure."""
import json, sys, os, glob, datetime, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rb = json.load(open(sys.argv[1])); input_sha = sys.argv[2] if len(sys.argv) > 2 else None
rep = {"generated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "input_sha256": input_sha, "national": {}, "lenders": {}, "states": {}}
idx = json.load(open(os.path.join(ROOT, "api/index.json")))["national"]
n = rb["national"]
rep["national"] = {"rebuilt": {"apps": n["apps"], "denials": n["denials"], "rate_pct": n["rate_pct"]},
                   "published": {"apps": idx["apps"], "denials": idx["denials"], "rate_pct": idx["rate_pct"]},
                   "match": n["apps"] == idx["apps"] and n["denials"] == idx["denials"]}
def slugify(s): import re; return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
pub = {}; by_lei = {}
for f in glob.glob(os.path.join(ROOT, "api/lender/*.json")):
    d = json.load(open(f)); pub[os.path.basename(f)[:-5]] = d
    if d.get("lei"): by_lei[d["lei"]] = (os.path.basename(f)[:-5], d)
L = rb.get("lenders") or []
rows = L if isinstance(L, list) else list(L.values())
matched = mism = missing = 0; mismatches = []
for r in rows:
    hit = by_lei.get(r.get("lei"))
    slug = hit[0] if hit else (r.get("slug") or slugify(r.get("lender") or r.get("name") or ""))
    p = hit[1] if hit else pub.get(slug)
    if not p: missing += 1; continue
    rate = float(r.get("rate", r.get("denial_rate_pct", r.get("rate_pct", -1)))); apps = int(r.get("apps", r.get("decisioned_applications", -1)))
    ok = abs(rate - float(p["denial_rate_pct"])) < 0.05 and apps == int(p["decisioned_applications"])
    matched += ok; mism += (not ok)
    if not ok and len(mismatches) < 20: mismatches.append({"slug": slug, "rebuilt": {"rate": rate, "apps": apps}, "published": {k: p[k] for k in ("denial_rate_pct", "decisioned_applications")}})
rep["lenders"] = {"rebuilt_rows": len(rows), "published_files": len(pub), "matched": matched, "mismatched": mism, "not_in_published": missing, "examples": mismatches}
S = rb.get("states") or {}
srows = S if isinstance(S, dict) else {x.get("state"): x for x in S}
sm = smm = 0; sex = []
for st, r in srows.items():
    f = os.path.join(ROOT, f"api/state/{str(st).lower()}.json")
    if not os.path.exists(f): continue
    p = json.load(open(f))
    ok = int(r.get("apps", r.get("decisioned_applications", -1))) == int(p["decisioned_applications"])
    sm += ok; smm += (not ok)
    if not ok and len(sex) < 10: sex.append({"state": st, "rebuilt": r, "published": p["decisioned_applications"]})
rep["states"] = {"matched": sm, "mismatched": smm, "examples": sex}
rep["verdict"] = "MATCH" if rep["national"]["match"] and mism == 0 and smm == 0 else "MISMATCH"
os.makedirs(os.path.join(ROOT, "provenance"), exist_ok=True)
out = os.path.join(ROOT, "provenance/rebuild-report.json")
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("verdict", "national")}, indent=1)); print("lenders", {k: rep["lenders"][k] for k in ("rebuilt_rows", "matched", "mismatched", "not_in_published")}, "states", {k: rep["states"][k] for k in ("matched", "mismatched")})
