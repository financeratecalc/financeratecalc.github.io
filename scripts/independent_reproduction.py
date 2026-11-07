#!/usr/bin/env python3
"""Independent reproduction: recompute the published figures with somebody else's code.

    python3 scripts/independent_reproduction.py /tmp/hmda.csv [provenance/independent-reproduction.json]

The arithmetic here is NOT ours. National, state and lender figures are computed by `hmda-analyzer`
(PyPI, Jay Patel, https://github.com/Jaypatel1511/hmda-analyzer), a third-party HMDA package that defines
"actionable" applications as action_taken in (1, 2, 3) and denial as action 3 within them
(hmdaanalyzer.analysis.lender.lender_summary, hmdaanalyzer.analysis.geographic.lending_by_state), and the
results are compared number by number with the committed api/ files.

What stays ours, stated plainly: the universe. hmda-analyzer has no FHA or reverse-mortgage filter, so this
script first writes a copy of the CFPB file restricted to loan_type == 2 and reverse_mortgage != 1 (every column
kept) and hands that file to the package's own loader. Everything after that line is their code.

This is a computational reproduction by an independent implementation, run by us. It is not a reproduction
commissioned from, or performed by, a third party. The report says so.
"""
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv.field_size_limit(1 << 28)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_universe(src, dst):
    """Our one contribution to the computation: FHA (loan_type 2), forward mortgages only."""
    kept = dropped_type = dropped_reverse = 0
    with open(src, newline="", encoding="utf-8") as fi, open(dst, "w", newline="", encoding="utf-8") as fo:
        r = csv.DictReader(fi)
        w = csv.DictWriter(fo, fieldnames=r.fieldnames)
        w.writeheader()
        for row in r:
            if row.get("loan_type") != "2":
                dropped_type += 1
                continue
            if row.get("reverse_mortgage") == "1":
                dropped_reverse += 1
                continue
            w.writerow(row)
            kept += 1
    return {"rows_kept": kept, "rows_not_fha": dropped_type, "rows_reverse_mortgage": dropped_reverse}


def main():
    src = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "provenance", "independent-reproduction.json")
    from hmdaanalyzer.analysis.geographic import lending_by_state
    from hmdaanalyzer.analysis.lender import lender_summary
    from hmdaanalyzer.data.loader import load_from_file

    universe = os.path.join(os.path.dirname(os.path.abspath(src)), "hmda_fha_forward.csv")
    uni = write_universe(src, universe)
    df = load_from_file(universe)   # their loader, their cleaning, their is_denied

    rep = {"method": "independent implementation", "implementation": {
               "package": "hmda-analyzer", "version": importlib.metadata.version("hmda-analyzer"),
               "author": "Jay Patel", "repository": "https://github.com/Jaypatel1511/hmda-analyzer",
               "functions": ["hmdaanalyzer.data.loader.load_from_file", "hmdaanalyzer.analysis.lender.lender_summary",
                             "hmdaanalyzer.analysis.geographic.lending_by_state"],
               "denominator_in_their_code": "action_taken in (1, 2, 3); denial = action 3 within it"},
           "our_contribution": {"universe_prefilter": "loan_type == 2 and reverse_mortgage != 1, all columns kept", **uni},
           "input": {"sha256": sha256(src)}, "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "status": "computational reproduction by an independent implementation, run by the publisher; not a third-party-performed reproduction",
           "national": {}, "states": {"compared": 0, "equal": 0, "diffs": []}, "lenders": {"compared": 0, "equal": 0, "diffs": []}}

    # ---- national
    nat = lender_summary(df)
    idx = json.load(open(os.path.join(ROOT, "api", "index.json"), encoding="utf-8"))["national"]
    theirs = {"apps": int(nat["total_applications"]), "denials": int(nat["denials"]), "rate_pct": float(nat["denial_rate"])}
    ours = {"apps": idx["apps"], "denials": idx["denials"], "rate_pct": idx["rate_pct"]}
    rep["national"] = {"hmda_analyzer": theirs, "published": ours, "equal": theirs == ours}

    # ---- states (published rate is rounded to 1 decimal; counts compared exactly)
    st = lending_by_state(df)
    for _, row in st.iterrows():
        p = os.path.join(ROOT, "api", "state", str(row["state_code"]).lower() + ".json")
        if not os.path.exists(p):
            continue
        S = json.load(open(p, encoding="utf-8"))
        t = {"apps": int(row["applications"]), "denials": int(row["denials"]), "rate_pct": round(100 * float(row["denial_rate"]), 1)}
        o = {"apps": S["decisioned_applications"], "denials": S["denials"], "rate_pct": S["denial_rate_pct"]}
        rep["states"]["compared"] += 1
        if t == o:
            rep["states"]["equal"] += 1
        else:
            rep["states"]["diffs"].append({"state": row["state_code"], "hmda_analyzer": t, "published": o})

    # ---- lenders (the published panel; their lender_summary per LEI)
    for p in sorted(os.listdir(os.path.join(ROOT, "api", "lender"))):
        L = json.load(open(os.path.join(ROOT, "api", "lender", p), encoding="utf-8"))
        s = lender_summary(df, lei=L["lei"])
        if not s:
            rep["lenders"]["diffs"].append({"lei": L["lei"], "lender": L["lender"], "hmda_analyzer": None, "published": L["decisioned_applications"]})
            rep["lenders"]["compared"] += 1
            continue
        t = {"apps": int(s["total_applications"]), "denials": int(s["denials"]), "rate_pct": round(float(s["denial_rate"]), 1)}
        o = {"apps": L["decisioned_applications"], "denials": L["denials"], "rate_pct": L["denial_rate_pct"]}
        rep["lenders"]["compared"] += 1
        if t == o:
            rep["lenders"]["equal"] += 1
        else:
            rep["lenders"]["diffs"].append({"lei": L["lei"], "lender": L["lender"], "hmda_analyzer": t, "published": o})

    rep["verdict"] = "IDENTICAL" if rep["national"]["equal"] and not rep["states"]["diffs"] and not rep["lenders"]["diffs"] else "DIFFERENCES"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(rep, open(out_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{rep['verdict']}: national {theirs} vs {ours}; states {rep['states']['equal']}/{rep['states']['compared']}; "
          f"lenders {rep['lenders']['equal']}/{rep['lenders']['compared']} -> {os.path.relpath(out_path, ROOT)}")


if __name__ == "__main__":
    main()
