#!/usr/bin/env python3
"""Check a proof-of-reading line offline, from the edition file alone (spec/reading-proof-0.1.md).

    python3 scripts/verify_reading_proof.py "FRC-READ:hud-fhaprod-2026-08:2026-11-16:1a2b3c4d:78925;24676;12" "the statement"

Exit 0 if the three values are the ones the edition holds in the cells this (edition, date, statement) draws.
Reads data/official/<source>-<period>.json from this repository; pass --base URL to read a published copy instead.
"""
import hashlib, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(t))).strip().lower()


def cells(d, period):
    out = []
    for fid in sorted(d["figures"]):
        v = d["figures"][fid].get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append((fid, period, v))
    hist = d.get("months_as_printed") or {}
    for m in sorted(hist):
        for fid in sorted(hist[m]):
            if m == period and fid in d["figures"]:
                continue
            v = hist[m][fid]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out.append((fid, m, v))
    return out


def draw(d, src, period, date, statement):
    n = norm(statement)
    seed = hashlib.sha256(f"{src}-{period}|{date}|{n}".encode()).hexdigest()
    pool, picked = cells(d, period), []
    for i in range(3):
        if not pool:
            break
        picked.append(pool.pop(int(seed[i * 8:i * 8 + 8], 16) % len(pool)))
    return picked, hashlib.sha256(n.encode()).hexdigest()[:8]


def check(proof, statement, base=None):
    m = re.match(r"^FRC-READ:([a-z0-9-]+)-(\d{4}-\d{2}):(\d{4}-\d{2}-\d{2}):([0-9a-f]{8}):(.+)$", proof.strip().strip("⟦⟧"))
    if not m:
        return {"verdict": "malformed"}
    src, period, date, h, vals = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5).split(";")
    name = f"data/official/{src}-{period}.json"
    d = json.load(urllib.request.urlopen(base.rstrip("/") + "/" + name)) if base else json.load(open(os.path.join(ROOT, name), encoding="utf-8"))
    picked, sh = draw(d, src, period, date, statement)
    if sh != h:
        return {"verdict": "statement_mismatch"}
    if len(vals) != len(picked):
        return {"verdict": "not_shown", "matched": 0, "of": len(picked)}
    hits = []
    for v, (_, _, truth) in zip(vals, picked):
        t = re.sub(r"[,$%\s]", "", v)
        hits.append(bool(re.match(r"^-?\d+(\.\d+)?$", t)) and abs(float(t) - truth) <= 1e-9 * max(1, abs(truth)))
    return {"verdict": "read" if all(hits) else "not_shown", "matched": sum(hits), "of": len(picked), "edition": f"{src}-{period}", "document_sha256": d["document"]["sha256"],
            "cells": [{"figure": f, "month": mth} for f, mth, _ in picked]}


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    base = next((sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == "--base"), None)
    if base in a:
        a.remove(base)
    if len(a) != 2:
        print(__doc__); sys.exit(2)
    r = check(a[0], a[1], base)
    print(json.dumps(r, indent=1)); sys.exit(0 if r["verdict"] == "read" else 1)
