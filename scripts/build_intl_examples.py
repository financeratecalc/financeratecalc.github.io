#!/usr/bin/env python3
"""Demonstration Subjects for the Figure Receipt profile, from publishers outside the United States and outside mortgage
finance. Each is read from a response captured by .github/workflows/intl-fetch.yml (data/intl/raw, hashed in
data/intl/manifest.json). Nothing is computed: the one observation in the captured response is copied as printed, with
the publisher's own labels and flags. Output: spec/ietf/examples/<id>.json, in the shape the statement service signs.
These are not the site's figures and are not counted among them."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com"
LIMITS = {
 "eurostat-prc-hpi-q-eu27-2026q2": [
  "a price level in euros: this is an index, 2015 = 100",
  "the index for any one member state, region or city",
  "a change adjusted for inflation or for incomes",
  "that the publisher has not revised the observation since the time of retrieval",
  "that another retrieval returns the same bytes: the digest is of one API response as retrieved, archived at the address given, not of a document the publisher keeps unchanged"],
 "eurostat-demo-mlexpec-eu27-2024": [
  "a final value: the publisher flags this observation as estimated and provisional",
  "how long any one person will live: this is period life expectancy at birth for an aggregate",
  "the value for any one member state, or for men or women separately",
  "healthy life years, or anything about cause of death",
  "that another retrieval returns the same bytes: the digest is of one API response as retrieved, archived at the address given, not of a document the publisher keeps unchanged"]}
src = {s["id"]: s for s in json.load(open(os.path.join(ROOT, "data/intl/sources.json")))["sources"]}
man = json.load(open(os.path.join(ROOT, "data/intl/manifest.json")))["captures"]
os.makedirs(os.path.join(ROOT, "spec/ietf/examples"), exist_ok=True)
for sid, s in src.items():
    caps = [c for c in man if c["id"] == sid]; assert caps, sid
    out_path = os.path.join(ROOT, "spec/ietf/examples", "example-" + sid + ".json")
    old = json.load(open(out_path)) if os.path.exists(out_path) else None
    revs = old["revisions"] if old else []
    for c in caps[len(revs):]:   # one revision per capture, in order; an existing revision is never rewritten
        d = json.loads(open(os.path.join(ROOT, c["file"])).read(), parse_float=str, parse_int=str)
        assert len(d["value"]) == 1, "the captured response must hold exactly one observation"
        k = next(iter(d["value"])); value = d["value"][k]
        dims = {i: {"code": next(iter(v["category"]["index"])), "label": next(iter(v["category"]["label"].values()))} for i, v in d["dimension"].items()}
        flag = (d.get("status") or {}).get(k)
        flags = (((d.get("extension") or {}).get("status") or {}).get("label") or {})
        source = {"publisher": s["publisher"], "dataset": s["dataset"], "dataset_title": d["label"], "doi": s["doi"], "retrieved_from": c["url"], "retrieved_at": c["retrieved_at"],
                  "sha256": c["sha256"], "archived_copy": BASE + "/" + c["file"], "publisher_updated": d.get("updated"), "dimensions": dims}
        if flag: source["publisher_flag"] = {"code": flag, "meaning": flags.get(flag)}
        claim = {"metric": s["dataset"].lower(), "value": value, "unit": dims["unit"]["label"], "period": dims["time"]["code"], "geography": dims["geo"]["label"], "level": "attested restatement"}
        st = {"id": "example-" + sid, "value": value, "kind": "restated", "claim": claim, "source": source, "limits": LIMITS[sid],
              "test": "Demonstration Subject, not one of this site's figures: a figure of another publisher, in another jurisdiction, restated under the same profile.", "issued": c["retrieved_at"]}
        if revs and revs[-1]["value"] != value: st["source_revision"] = {"value": value, "edition": d.get("updated"), "marked_by_source": bool(flag)}
        revs.append(st)
    doc = {"what": "A demonstration Subject: a figure published by " + s["publisher"] + ", restated under the Figure Receipt profile from a response captured as retrieved. It shows the profile applied outside the United States and outside the publisher's own figures.",
           "not_a_published_figure": True, "demonstration": True, "iss": BASE, "sub": BASE + "/spec/ietf/examples/example-" + sid + ".json",
           "fetch": {"in_force": "https://frc-mcp.ziyetis.workers.dev/statement/example-" + sid, "check": "https://frc-mcp.ziyetis.workers.dev/statement/example-" + sid + "?digest=<64 hex>"},
           "reuse": "Source: Eurostat. Reuse of Eurostat data is authorised with acknowledgement of the source; the figure is copied unchanged.", "revisions": revs}
    json.dump(doc, open(out_path, "w"), indent=1, ensure_ascii=False); open(out_path, "a").write("\n")
    print(out_path, revs[-1]["value"], len(revs))
