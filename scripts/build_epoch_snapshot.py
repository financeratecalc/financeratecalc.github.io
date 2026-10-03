#!/usr/bin/env python3
"""Write rl-env/frc_citation/fixtures/epoch-snapshot.json: for every epoch in epochs.json,
the (value, hash8) of every claim id the temporal environment can reward, computed by
the same code the reward uses. Signed by claims-transparency.yml, so the dated ground
truth of the temporal rewards is itself tamper-evident."""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rl-env"))
from frc_citation.temporal import epoch_snapshot, load_epochs

snap = json.load(open(ROOT / "rl-env/frc_citation/receipts-snapshot.json", encoding="utf-8"))
ids = sorted(snap["receipts"].keys())
out = {"generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "note": "Dated ground truth of the frc-citation-temporal rewards: per epoch, value and hash8 per claim id. Superseded epochs are reconstructions from the corrections log (see epochs.json); their receipts were never issued live.",
       "epochs": {e["id"]: {"date": e["date"], "label": e["label"], "overrides": sorted(e.get("overrides", {}).keys())} for e in load_epochs()},
       "snapshot": epoch_snapshot(str(ROOT), ids)}
p = ROOT / "rl-env/frc_citation/fixtures/epoch-snapshot.json"
p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
changed = {eid: [c for c, r in v["claims"].items() if r != out["snapshot"]["E2"]["claims"].get(c)] for eid, v in out["snapshot"].items()}
print(f"wrote {p.name}: {len(ids)} claim ids x {len(out['snapshot'])} epochs; differing from current: { {k: len(v) for k, v in changed.items()} }")
