#!/usr/bin/env python3
"""claims/index.json: one entry per claim document, derived from claims/*.json (never hand-edited again).
Top-level fields of the existing index are kept; entries are regenerated. --check exits 1 on drift."""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com"
P = os.path.join(ROOT, "claims", "index.json")


def main():
    idx = json.load(open(P, encoding="utf-8"))
    old = {e["id"]: e for e in idx["claims"]}
    entries = []
    for f in sorted(glob.glob(os.path.join(ROOT, "claims", "*.json"))):
        b = os.path.basename(f)
        if b.endswith(".contract.json") or b == "index.json":
            continue
        cid = b[:-5]
        d = json.load(open(f, encoding="utf-8"))
        c = d.get("claim") or {}
        e = {"id": cid, "passport_id": d.get("passport_id", "frc:claim:" + cid), "metric": c.get("metric") or old.get(cid, {}).get("metric"),
             "url": f"{BASE}/claims/{cid}.json"}
        if os.path.exists(os.path.join(ROOT, "claims", cid + ".contract.json")):
            e["contract_url"] = f"{BASE}/claims/{cid}.contract.json"
        if d.get("receipt"):
            e["display_value"] = d.get("display_value"); e["receipt"] = d["receipt"]
        else:
            e["receipted"] = False
        entries.append(e)
    # keep the historical order for ids already indexed; new ids follow in path order
    order = {cid: i for i, cid in enumerate(old)}
    entries.sort(key=lambda e: (order.get(e["id"], 10**9), e["id"]))
    new = dict(idx); new["claims"] = entries
    cur = json.dumps(idx, ensure_ascii=False, sort_keys=True); nxt = json.dumps(new, ensure_ascii=False, sort_keys=True)
    if "--check" in sys.argv:
        print("claims index:", "current" if cur == nxt else f"STALE ({len(entries)} vs {len(old)})"); sys.exit(0 if cur == nxt else 1)
    json.dump(new, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"claims/index.json: {len(entries)} entries ({len(entries) - len(old):+d})")


if __name__ == "__main__":
    main()
