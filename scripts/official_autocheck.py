#!/usr/bin/env python3
"""Daily look for the next edition of every official source already restated (data/official/index.json).

For each source: next period = latest restated month + 1. scripts/official_restate.py is run for it; when the publisher
has not posted that edition the run exits non-zero and nothing changes, which is the normal case. When an edition is
found it is restated, compared with the previous one, and summarised in /tmp/official_new.md for the workflow to post.
Exit code is always 0; the file exists only when something new was restated."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
idx = json.load(open(os.path.join(ROOT, "data", "official", "index.json"), encoding="utf-8"))
lines = []
for source, latest in sorted(idx.get("latest", {}).items()):
    y, m = int(latest[:4]), int(latest[5:7])
    nxt = f"{y + m // 12}-{m % 12 + 1:02d}"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "official_restate.py"), source, nxt], capture_output=True, text=True)
    p = os.path.join(ROOT, "data", "official", f"{source}-{nxt}.json")
    if r.returncode != 0 or not os.path.exists(p):
        print(f"{source} {nxt}: not published yet (or not readable): {(r.stdout + r.stderr).strip().splitlines()[-1][:160] if (r.stdout + r.stderr).strip() else 'no output'}")
        continue
    d = json.load(open(p, encoding="utf-8"))
    rv = d.get("prior_edition_check", {}).get("revisions", [])
    changed = [x for x in rv if x.get("revised")]
    lines.append(f"**{d['document']['title']} — {d['document']['edition']}** restated ({len(d['figures'])} receipts). "
                 f"Compared with the {d['prior_edition_check'].get('edition_compared')}: {len(rv)} figures, {len(changed)} changed.")
    for x in changed:
        lines.append(f"- {x['figure']} for {x['period']}: {x['first_printed']} -> {x['restated_value']}")
    print(lines[-1 - len(changed)])
if lines:
    open("/tmp/official_new.md", "w", encoding="utf-8").write("\n".join(lines) + "\n\nLedger: https://financeratecalc.com/revision-ledger.html\n")
