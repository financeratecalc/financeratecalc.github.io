#!/usr/bin/env python3
"""Release-day step 3 (dry run): compare a materialized api/ tree with the committed one, number by number.

    python3 scripts/compare_tree.py <materialized_dir> [report.json]

Every numeric field in every api/*.json is compared; strings (names, URLs, meta text) are compared too but reported
separately, since a renamed lender is not a changed figure. Exit 0 always: a difference is a finding to publish, not a
build failure. The report lists files only in one tree, fields that differ, and the totals.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def flat(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from flat(v, f"{p}.{k}" if p else k)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            yield from flat(v, f"{p}[{i}]")
    else:
        yield p, d


def main():
    new = sys.argv[1]
    rep_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "provenance", "release-day-dryrun.json")
    rep = {"files_only_committed": [], "files_only_rebuilt": [], "numeric_diffs": [], "string_diffs": [], "files_compared": 0, "numeric_fields": 0, "numeric_equal": 0}
    rels = set()
    for base in (os.path.join(ROOT, "api"), os.path.join(new, "api")):
        for f in glob.glob(os.path.join(base, "**", "*.json"), recursive=True):
            rels.add(os.path.relpath(f, base))
    for rel in sorted(rels):
        a, b = os.path.join(ROOT, "api", rel), os.path.join(new, "api", rel)
        if not os.path.exists(a):
            rep["files_only_rebuilt"].append(rel); continue
        if not os.path.exists(b):
            rep["files_only_committed"].append(rel); continue
        A, B = dict(flat(json.load(open(a)))), dict(flat(json.load(open(b))))
        rep["files_compared"] += 1
        for k in sorted(set(A) | set(B)):
            va, vb = A.get(k, "<absent>"), B.get(k, "<absent>")
            if isinstance(va, (int, float)) and not isinstance(va, bool) and isinstance(vb, (int, float)) and not isinstance(vb, bool):
                rep["numeric_fields"] += 1
                if abs(va - vb) < 1e-9:
                    rep["numeric_equal"] += 1
                elif len(rep["numeric_diffs"]) < 400:
                    rep["numeric_diffs"].append({"file": rel, "field": k, "committed": va, "rebuilt": vb})
            elif va != vb and len(rep["string_diffs"]) < 200:
                rep["string_diffs"].append({"file": rel, "field": k, "committed": str(va)[:80], "rebuilt": str(vb)[:80]})
    rep["numeric_match_rate"] = round(rep["numeric_equal"] / rep["numeric_fields"], 4) if rep["numeric_fields"] else None
    rep["verdict"] = "IDENTICAL" if not rep["numeric_diffs"] and not rep["files_only_committed"] and not rep["files_only_rebuilt"] else "DIFFERENCES"
    os.makedirs(os.path.dirname(rep_path), exist_ok=True)
    json.dump(rep, open(rep_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{rep['verdict']}: {rep['files_compared']} files, numeric {rep['numeric_equal']}/{rep['numeric_fields']} equal, "
          f"{len(rep['numeric_diffs'])} numeric diffs, {len(rep['string_diffs'])} string diffs, only-committed {len(rep['files_only_committed'])}, only-rebuilt {len(rep['files_only_rebuilt'])} -> {os.path.relpath(rep_path, ROOT)}")


if __name__ == "__main__":
    main()
