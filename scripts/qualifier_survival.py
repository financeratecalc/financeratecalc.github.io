#!/usr/bin/env python3
"""Qualifier Survival Index (QSI): when an answer engine restates a FinanceRateCalc figure, how much of what
belongs next to the number survives?

A hallucination rate asks whether the number is right. QSI asks whether the sentence is. For every answer in
eval/answer-engine-log/*.json (field answer_text) the grader finds the site's figures that the answer quotes and
scores, with fixed patterns and no model:

  value        the figure is a current published value; a superseded value is a miss unless the text marks it as
               corrected/earlier/previous within a few words (restating a correction correctly is not a miss)
  period       the year 2025 is stated
  population   the denominator is named (decisioned / actions 1-3 / applications acted on / purchase-only …)
  program      FHA is named as the program
  universe     reverse mortgages (HECM) are mentioned as excluded (national figure) or the top-100 scope is stated (lender figures)
  no_drift     no causal, second-person, lender-advice or legal wording around the figures
  attribution  FinanceRateCalc or financeratecalc.com is named as the source

QSI for one answer = survived qualifiers / qualifiers required; the instrument's QSI is the mean over answers.
Published at eval/qsi/qsi.json and qualifier-survival.html. The grader is public so anyone can rerun it; the
answers themselves are archived verbatim, so a disputed score can be re-read.

    python3 scripts/qualifier_survival.py            # grade every archived answer, write eval/qsi/qsi.json
    python3 scripts/qualifier_survival.py --check    # exit 1 if qsi.json is stale
"""
import datetime as dt
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "eval", "answer-engine-log")
OUT = os.path.join(ROOT, "eval", "qsi", "qsi.json")

# current published values the instrument asks about (kept in sync with the claim documents by the check below)
def current_values():
    v = {}
    nat = json.load(open(os.path.join(ROOT, "claims", "national-fha-denial-rate-2025.json")))
    v["national"] = {"value": nat["display_value"], "n": "1,187,606", "denials": "262,250", "kind": "national"}
    for slug in ("amerisave-mortgage", "american-financing", "carrington-mortgage-services", "newrez", "better-mortgage", "lakeview-loan-servicing",
                 "wells-fargo-bank", "jpmorgan-chase-bank", "mutual-of-omaha-mortgage", "envoy-mortgage"):
        c = json.load(open(os.path.join(ROOT, "claims", f"lender-{slug}-2025.json")))
        v[slug] = {"value": c["display_value"], "n": f"{c['claim']['n']:,}", "name": c["claim"]["lender"], "kind": "lender"}
    return v

SUPERSEDED = {"21.7%": "national value before the 2026-07-26 HECM correction", "1,217,297": "universe before the 2026-07-26 HECM correction",
              "53.3%": "NewRez value before the 2026-07-26 correction (hub page, fixed 2026-11-01)", "52.3%": "NewRez pre-correction table value"}
CAUSAL = re.compile(r"\b(caus(?:e|es|ed|ing)|because (?:of )?(?:the )?lender|leads? to|results? in|thresholds? that caused|drives?)\b", re.I)
SECOND_PERSON = re.compile(r"\b(you will|you'll|your (?:odds|chances|application)|will (?:be )?(?:approve|den(?:y|ied)) you)\b", re.I)
ADVICE = re.compile(r"\b(avoid (?:applying|this lender|these lenders|them)|should avoid|choose (?:a|the) lender|best lender|apply (?:with|to) (?:a|the|this)|recommend)\b", re.I)
LEGAL = re.compile(r"\b(discriminat|violat|unlawful|illegal|redlin)\w*", re.I)
PERIOD = re.compile(r"\b2025\b")
POPULATION = re.compile(r"(decision(?:ed)?|action[_ ]taken|actions? 1,? ?2,? ?(?:or |and )?3|applications? (?:acted on|that reached)|purchase[- ]only|purchase-mortgage applications|denominator)", re.I)
PROGRAM = re.compile(r"\bFHA\b")
HECM = re.compile(r"(reverse[- ]mortgage|HECM)", re.I)
TOP100 = re.compile(r"(100 largest|top[- ]100|largest FHA lenders)", re.I)
ATTRIB = re.compile(r"financeratecalc", re.I)


CORRECTED = re.compile(r"(correct|earlier|previous|superseded|before the|removed|revised|old)", re.I)


def grade(text, cur, sources=""):
    t = text
    found = []
    for key, c in cur.items():
        if c["value"] in t or (c["kind"] == "national" and c["n"] in t):
            found.append(key)
    if not found:
        return None
    required = ["value", "period", "population", "program", "universe", "no_drift", "attribution"]
    stale = []
    for sv in SUPERSEDED:
        for m in re.finditer(re.escape(sv), t):
            win = t[max(0, m.start() - 140): m.end() + 140]
            if not CORRECTED.search(win):
                stale.append(sv); break
    s = {
        "value": not stale,
        "period": bool(PERIOD.search(t)),
        "population": bool(POPULATION.search(t)),
        "program": bool(PROGRAM.search(t)),
        "universe": bool(HECM.search(t)) if "national" in found else bool(TOP100.search(t)),
        "no_drift": not (CAUSAL.search(t) or SECOND_PERSON.search(t) or ADVICE.search(t) or LEGAL.search(t)),
        "attribution": bool(ATTRIB.search(t) or ATTRIB.search(sources)),
    }
    drift = [m.group(0) for rx in (CAUSAL, SECOND_PERSON, ADVICE, LEGAL) for m in [rx.search(t)] if m]
    return {"figures_found": found, "survived": s, "qsi": round(sum(s.values()) / len(required), 3), "superseded_values_quoted": stale, "drift_phrases": drift}


def main():
    check = "--check" in sys.argv
    cur = current_values()
    rows = []
    for f in sorted(glob.glob(os.path.join(LOG, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("answer_text") or str(d.get("kind", "")).startswith("discovery probe"):
            continue   # discovery probes ask other questions; they are archived but not part of the instrument
        g = grade(d["answer_text"], cur, " ".join(u for q in d.get("questions", []) for u in q.get("sources", [])))
        if g is None:
            continue
        rows.append({"log": os.path.relpath(f, ROOT), "date": d["date"], "engine": d["engine"], **g})
    by_engine = {}
    for r in rows:
        by_engine.setdefault(r["engine"], []).append(r["qsi"])
    out = {
        "metric": "Qualifier Survival Index (QSI)",
        "definition": "For an answer that quotes a FinanceRateCalc figure: the share of seven qualifiers that survive — current value, period, population/denominator, program, universe (HECM exclusion or top-100 scope), no causal/second-person/advice/legal drift, attribution. Deterministic patterns, no model; the grader is scripts/qualifier_survival.py and every graded answer is archived verbatim.",
        "instrument": ["What was the FHA denial rate in the US in 2025, and what is the denominator?", "Which lenders had the highest FHA denial rates in 2025?", "What is AmeriSave Mortgage's FHA denial rate in 2025?"],
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "answers_graded": len(rows), "qsi_mean": round(sum(r["qsi"] for r in rows) / len(rows), 3) if rows else None,
        "by_engine": {e: {"answers": len(v), "qsi": round(sum(v) / len(v), 3)} for e, v in by_engine.items()},
        "qualifier_survival_rates": {q: round(sum(1 for r in rows if r["survived"][q]) / len(rows), 3) for q in rows[0]["survived"]} if rows else {},
        "rows": rows,
        "caveats": ["Answers were obtained by the site owner from his own accounts and pasted; the engines' identity for one answer is the owner's report.",
                    "A pattern grader can miss a qualifier phrased unusually and can flag an innocent word; the archived text is the record, the score is a reading of it.",
                    "Three questions, four engines, one week: a baseline, not a trend."],
    }
    if check:
        try:
            old = json.load(open(OUT))
        except FileNotFoundError:
            old = {}
        same = {k: v for k, v in old.items() if k != "generated"} == {k: v for k, v in out.items() if k != "generated"}
        print("qsi:", "current" if same else "STALE"); sys.exit(0 if same else 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    # directory index for GitHub Pages (a bare directory URL is a 404 there)
    graded = {r["log"]: r for r in rows}
    items = ""
    for f in sorted(glob.glob(os.path.join(LOG, "*.json"))):
        rel = os.path.relpath(f, ROOT); d = json.load(open(f, encoding="utf-8"))
        tail = f'QSI {graded[rel]["qsi"]}' if rel in graded else f'not graded ({html.escape(str(d.get("summary") or d.get("kind") or "")[:160])})'
        items += f'<li><a href="/{rel}">{rel.split("/")[-1]}</a> — {html.escape(str(d.get("engine", ""))[:60])} — {tail}</li>'
    open(os.path.join(LOG, "index.html"), "w", encoding="utf-8").write(
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Answer-engine log | FinanceRateCalc</title>'
        '<style>body{background:#08090c;color:#e8e4da;font-family:system-ui,sans-serif;max-width:900px;margin:36px auto;padding:0 18px;line-height:1.6}a{color:#C8A84B}</style></head><body>'
        '<h1>Answer-engine log</h1><p>Every answer archived verbatim: those quoting a FinanceRateCalc figure are graded for the <a href="/qualifier-survival.html">Qualifier Survival Index</a>, with its sources and verdicts; discovery probes (our pages not found, or no figure quoted) are listed as not graded.</p><ul>' + items + '</ul></body></html>\n')
    print(f"QSI mean {out['qsi_mean']} over {len(rows)} answers; by engine {out['by_engine']}; survival {out['qualifier_survival_rates']}")


if __name__ == "__main__":
    main()
