#!/usr/bin/env python3
"""Writes sample-evidence-brief.html: one complete Evidence Brief, worked on a real AI answer.

The input is the answer logged in eval/answer-engine-log/2026-11-12-gemini.json (three questions put to Gemini, figures
recorded as given). Every verdict is computed: a quoted denial rate is placed on the published denominator map
(data/purpose/*.json, 0.15-point tolerance, the same rule as the locate_denominator tool); the HUD count is compared
with the two editions restated under data/official/. Nothing is typed in by hand except the wording.

    python3 scripts/build_sample_brief.py            # write the page
    python3 scripts/build_sample_brief.py --check    # exit 1 if the page on disk is stale
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: json.load(open(os.path.join(ROOT, *p), encoding="utf-8"))
LOG = J("eval", "answer-engine-log", "2026-11-12-gemini.json")
MAP = {p: J("data", "purpose", f"{p}-2025.json") for p in ("fha", "va")}
TOL = 0.15
PW = {"all": "all loan purposes", "purchase": "home purchase", "refinance_all": "refinance (incl. cash-out)", "refinance": "refinance", "cash_out_refinance": "cash-out refinance",
      "home_improvement": "home improvement", "other": "other purpose", "not_applicable": "purpose not applicable"}
BW = {"decisioned": "decisioned applications", "acted_on": "all applications acted on", "denied_plus_originated": "denied plus originated"}


def place(v, progs=("fha", "va")):
    hits = []
    for p in progs:
        d = MAP[p]
        for key, c in d["cells"].items():
            purpose, scope = key.split("|")
            for base, r in c["rate_pct"].items():
                if r is not None and abs(r - v) <= TOL:
                    den = {"decisioned": c["decisioned"], "acted_on": c["acted_on"], "denied_plus_originated": c["originated"] + c["denied"]}[base]
                    hits.append({"program": d["program"], "purpose": purpose, "scope": scope, "base": base, "rate": r, "denied": c["denied"], "den": den})
    return sorted(hits, key=lambda h: abs(h["rate"] - v))


def cell(p, key, base="decisioned"):
    c = MAP[p]["cells"][key]
    return c["rate_pct"][base], c["denied"], c[base] if base in c else c["originated"] + c["denied"]


def rec(cid):
    d = J("claims", cid + ".json")
    return d["receipt"], d["display_value"]


def describe(h):
    return f"{h['program']}, {PW.get(h['purpose'], h['purpose'])}, {'all rows' if h['scope'] == 'all' else 'first-lien owner-occupied site-built 1&ndash;4 unit'}, {BW[h['base']]}: {h['denied']:,} / {h['den']:,} = {h['rate']}%"


def build():
    q1, q2, q3 = LOG["questions"]
    assert "22.0%" in q1["figures_quoted"]["all_fha"] and "14.4%" in q1["figures_quoted"]["purchase"] and "12.23%" in q2["figures_quoted"]["fha"] and "7.89%" in q2["figures_quoted"]["va"] and "65,328" in q3["figures_quoted"]["purchase_count"]
    aug = J("data", "official", "hud-fhaprod-2026-08.json")
    rv = next(r for r in aug["prior_edition_check"]["revisions"] if r["figure"] == "purchase-count")
    r_fha, v_fha = rec("national-fha-denial-rate-2025")
    r_va, v_va = rec("va-national-denial-rate-2025")
    r_fp, v_fp = rec("purpose-fha-purchase-denial-rate-2025")
    r_hud, v_hud = rec("official-hud-fhaprod-2026-07-purchase-count")
    fa, fad, fan = cell("fha", "all|all")
    fp, fpd, fpn = cell("fha", "purchase|all")
    va, vad, van = cell("va", "all|all")
    claims = []

    def add(n, stated, attributed, v, progs, verdict_if_hit, body_hit, body_miss, rewrite):
        hits = place(v, progs)
        verdict = verdict_if_hit if hits else "OUT_OF_SCOPE"
        placed = "<br>".join(describe(h) for h in hits[:3]) if hits else f"No cell of the 2025 file within {TOL} points of {v}% ({sum(len(MAP[p]['cells']) * 3 for p in progs)} cells searched)."
        claims.append({"n": n, "stated": stated, "attr": attributed, "verdict": verdict, "placed": placed, "body": body_hit if hits else body_miss, "rewrite": rewrite, "hits": len(hits)})

    add(1, "22.0% of FHA applications were denied in 2025; the answer describes the base as applications that reached a decision.", "Inside Mortgage Finance (named, no link)", 22.0, ("fha",), "PASS",
        f"The figure sits on the published definition to within a tenth ({fa}%). Universe, denominator and year are all stated in the answer. The source is a trade publication behind a paywall, so the match is to the federal file, not to that article's method.",
        "", f"In 2025, {v_fha} of decisioned FHA applications were denied ({fad:,} of {fan:,}). {r_fha}")
    add(2, "14.4% of FHA purchase applications were denied in 2025.", "a consumer finance page that names no source", 14.4, ("fha",), "NEEDS_QUALIFIER", "",
        f"No definition of an FHA purchase denial rate in the 2025 file produces 14.4%. Among decisioned FHA purchase applications the rate is {fp}% ({fpd:,} of {fpn:,}). The page the answer relied on gives no source, year file or denominator, so the figure cannot be traced. That is not proof it is wrong; it is unverifiable as stated.",
        f"In 2025, {v_fp} of decisioned FHA home-purchase applications were denied ({fpd:,} of {fpn:,}). {r_fp}")
    add(3, "12.23% is the &lsquo;overall&rsquo; FHA denial rate for 2025.", "LendingTree (named, no link)", 12.23, ("fha",), "NEEDS_QUALIFIER", "",
        f"No cell reproduces 12.23%, and &lsquo;overall&rsquo; contradicts claim 1 from the same engine minutes earlier (22.0% for all FHA applications). The page it traces to states the figure &lsquo;based on 2025 HMDA data&rsquo; with no denominator or method. The all-purpose rate among decisioned applications is {fa}%.",
        "Drop the figure, or attribute it to its publisher as a number whose definition is not published. Do not call it the overall FHA denial rate.")
    add(4, "7.89% of VA applications were denied in 2025 &lsquo;across all loan purposes&rsquo;.", "LendingTree (named, no link)", 7.89, ("va",), "NEEDS_QUALIFIER", "",
        f"No cell reproduces 7.89%. Across all loan purposes the VA rate among decisioned applications is {va}% ({vad:,} of {van:,}), about twice the stated figure. The answer's separate &lsquo;8.0% home purchase&rsquo; does have a home in the file ({describe(place(8.0, ('va',))[0]) if place(8.0, ('va',)) else 'no match'}), which suggests a purchase-only figure was relabelled as all purposes. That is an inference, not a finding.",
        f"In 2025, {v_va} of decisioned VA applications were denied ({vad:,} of {van:,}). {r_va}")
    hud_verdict = "NEEDS_QUALIFIER" if rv["revised"] else "PASS"
    claims.append({"n": 5, "stated": "HUD endorsed 65,328 FHA purchase loans in July 2026; later editions &lsquo;are not publicly available&rsquo;, so a revision cannot be confirmed.", "attr": "HUD FHA Single Family Production Report, July 2026 edition",
                   "verdict": hud_verdict, "placed": f"July 2026 report prints {rv['first_printed']:,}. {html.escape(rv['restated_in'])} prints {rv['restated_value']:,} for the same month (document SHA-256 {aug['document']['sha256'][:12]}&hellip;).",
                   "body": f"The count is correct as first printed. The statement about availability is not: the next edition is public and restates July as {rv['restated_value']:,}, without marking the change. A figure from a monthly report needs its edition next to it.",
                   "rewrite": f"HUD&rsquo;s July 2026 production report printed {v_hud} FHA purchase endorsements for July; the August 2026 report restated the month as {rv['restated_value']:,}. {r_hud}", "hits": None})
    tally = {k: sum(c["verdict"] == k for c in claims) for k in ("PASS", "NEEDS_QUALIFIER", "OUT_OF_SCOPE")}
    pill = {"PASS": "p-pass", "NEEDS_QUALIFIER": "p-q", "OUT_OF_SCOPE": "p-o"}
    cards = "\n".join(
        f'<div class="card"><span class="pill {pill[c["verdict"]]}">{c["verdict"]}</span><b>Claim {c["n"]}.</b> {c["stated"]}<br><span class="small">Attributed in the answer to: {c["attr"]}</span>'
        f'<table><tr><th>Placed on the record</th></tr><tr><td class="mono">{c["placed"]}</td></tr></table>{c["body"]}<br><br><b>Safe rewrite:</b> {c["rewrite"]}</div>' for c in claims)
    src = open(os.path.join(ROOT, "claim-audit.html"), encoding="utf-8").read()
    style = src[src.index("<style>"):src.index("</style>") + 8].replace("</style>", ".small{font-size:13px;color:#a5a094}</style>")
    nav = src[src.index("<nav data-frc-nav"):src.index("</nav>") + 6]
    title = "Sample Evidence Brief: five claims from one AI answer, checked against the federal record"
    desc = "A complete worked Evidence Brief: five figures from a Gemini answer about 2025 FHA and VA denial rates and a HUD monthly count, each placed on the public record with a verdict and a safe rewrite."
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | FinanceRateCalc</title><meta name="description" content="{desc}">
<link rel="canonical" href="https://financeratecalc.com/sample-evidence-brief.html">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,900&family=DM+Sans:wght@300;400;600;700&family=DM+Mono&display=swap" rel="stylesheet">
{style}</head><body>
{nav}
<div class="wrap">
<div class="kicker">Sample · Evidence Brief · five-claim audit</div>
<h1>Five claims from one AI answer, checked against the federal record</h1>
<p class="sub">This is what a <a href="/claim-audit.html">Claim Audit</a> returns, worked in full on a real case. On {LOG["date"]} three questions about 2025 mortgage denial rates and a HUD monthly count were put to {LOG["engine"]}. The figures it gave are below as it gave them. The site was not named in the questions and was not cited in the answers.</p>
<div class="card"><b>Result:</b> {tally["PASS"]} PASS &middot; {tally["NEEDS_QUALIFIER"]} NEEDS_QUALIFIER &middot; {tally["OUT_OF_SCOPE"]} OUT_OF_SCOPE.<br>One figure is right and fully stated. Three denial rates cannot be reproduced from the 2025 file under any published definition. One official count is right as first printed and missing its later restatement.</div>
<h2>How each claim was checked</h2>
<p class="sub" style="font-size:14.5px">A quoted denial rate is placed on the <a href="/denominator-map.html">denominator map</a>: every combination of program, loan purpose, scope and base computed from the 2025 HMDA file, {sum(len(MAP[p]["cells"]) * 3 for p in MAP)} cells for FHA and VA. A cell within {TOL} points is a match. A match shows which definition <i>can</i> produce the number, not which one its publisher used. No match means another year, another filter, or a figure this file does not reproduce. The HUD count is compared with the editions restated on the <a href="/revision-ledger.html">revision ledger</a>. OUT_OF_SCOPE here means the sentence goes past what the public file can support as stated; it is a statement about the sentence, not about its author.</p>
{cards}
<h2>What this brief does not say</h2>
<div class="limit">It does not say the engine or the pages it relied on acted in bad faith, and it does not say an unplaceable figure is false: only that it cannot be traced to the public file as stated. It says nothing about any applicant, and it does not rank programs or lenders. The inference in claim 4 is marked as an inference.</div>
<p class="sub" style="font-size:14px">The logged answer, with what was checked and how: <a href="/eval/answer-engine-log/2026-11-12-gemini.json">eval/answer-engine-log/2026-11-12-gemini.json</a>. Receipts in the rewrites verify at <a href="/verify.html">/verify</a>. This page is generated by <span class="mono">scripts/build_sample_brief.py</span> from those files.</p>
<div style="margin-top:40px;border-top:1px solid #23262e;padding-top:14px;font-size:13px;color:#a5a094">FinanceRateCalc &middot; Measured, not assumed. &middot; <a href="/claim-audit.html">Request an audit</a> &middot; <a href="/corrections.html">Corrections</a></div>
</div></body></html>
'''


if __name__ == "__main__":
    page = build()
    p = os.path.join(ROOT, "sample-evidence-brief.html")
    if "--check" in sys.argv:
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != page:
            print("sample-evidence-brief.html is STALE; run scripts/build_sample_brief.py"); sys.exit(1)
        print("sample-evidence-brief.html is current")
    else:
        open(p, "w", encoding="utf-8").write(page); print("wrote", p, len(page), "bytes")
