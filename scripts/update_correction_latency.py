#!/usr/bin/env python3
"""Append STALE_VALUE observations from automated eval runs to eval/correction-latency.json."""
import json, glob
lat = json.load(open("eval/correction-latency.json")); corr = lat["corrections"][0]
seen = {(o.get("system"), o.get("observed"), o.get("question")) for o in corr["observations"]}
added = 0
for f in sorted(glob.glob("eval/runs/2*.json")):
    d = json.load(open(f)); s = d.get("summary")
    if not s: continue
    for r in s.get("samples", []):
        if "STALE_VALUE" in r.get("failure_codes", []):
            key = (s["model"], s["run"][:10], r["id"])
            if key in seen: continue
            corr["observations"].append({"system": s["model"], "condition": s.get("condition"), "question": r["id"], "observed": s["run"][:10], "stale": True, "codes": r["failure_codes"], "note": (r.get("fidelity_explanation") or "")[:160]})
            seen.add(key); added += 1
json.dump(lat, open("eval/correction-latency.json", "w"), indent=1); print("added", added)
