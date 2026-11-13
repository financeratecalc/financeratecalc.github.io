#!/usr/bin/env python3
"""<program>-loan-denial-rates-2025.html for VA / USDA / conventional: national figure, five outcomes, all states — every
number from data/programs/<program>-2025.json and its claim documents, every figure with its receipt.

    python3 scripts/build_program_page.py va [--check]

Generated, idempotent, no number typed. The page states the universe, the declaration document, the receipts and what
the figures do not establish (above all: no cross-program comparison as a judgement of programs or lenders)."""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = {"va": ("VA", "VA-guaranteed", "va-loan-denial-rates-2025.html"), "usda": ("USDA", "USDA (Rural Housing Service / FSA)", "usda-loan-denial-rates-2025.html"),
         "conv": ("conventional", "conventional closed-end", "conventional-loan-denial-rates-2025.html")}
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}


def shell():
    src = open(os.path.join(ROOT, "scripts", "build_outcomes_page.py"), encoding="utf-8").read().splitlines()
    style = next(l for l in src if l.startswith("<style>")).replace("{{", "{").replace("}}", "}")
    nav = next(l for l in src if l.startswith("<nav data-frc-nav"))
    return style, nav


def claim(cid):
    return json.load(open(os.path.join(ROOT, "claims", cid + ".json"), encoding="utf-8"))


def main():
    prog = sys.argv[1]
    short, longname, out_name = NAMES[prog]
    OUT = os.path.join(ROOT, out_name)
    d = json.load(open(os.path.join(ROOT, "data", "programs", f"{prog}-2025.json"), encoding="utf-8"))
    style, nav = shell()
    n = d["national"]; o = d["outcomes_national"]
    fmt = lambda x: f"{x:,}"
    nat = claim(f"{prog}-national-denial-rate-2025")
    ends = [("originated", "Originated"), ("approved_not_accepted", "Approved, not accepted"), ("denied", "Denied"), ("withdrawn", "Withdrawn"), ("closed_incomplete", "Closed for incompleteness")]
    rc = {k: claim(f"outcome-{prog}-{k.replace('_', '-')}-2025")["receipt"] for k, _ in ends}
    rows = ""
    for s in sorted(d["states"], key=lambda x: -x["decisioned_applications"]):
        c = claim(f"{prog}-state-{s['state'].lower()}-denial-rate-2025")
        rows += (f'<tr><td>{html.escape(STATES.get(s["state"], s["state"]))}</td><td class=n>{fmt(s["decisioned_applications"])}</td><td class=n>{fmt(s["denials"])}</td>'
                 f'<td class=n><b>{s["denial_rate_pct"]}%</b></td><td class="r"><a href="/claims/{c["id"]}.json">{html.escape(c["receipt"])}</a></td></tr>')
    closed_end = " and open-end lines of credit" if prog == "conv" else ""
    page = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{short} loan denial rates in 2025: national, five outcomes, every state | FinanceRateCalc</title>\n'
        f'<meta name="description" content="In 2025, {n["denial_rate_pct"]:.1f}% of decisioned {short} applications in the US were denied ({fmt(n["denials"])} of {fmt(n["decisioned_applications"])}; actions 1-3, reverse mortgages excluded). Of the {fmt(o["applications_acted_on"])} applications acted on, {o["outcomes"]["withdrawn"]["share_of_acted_pct"]}% were withdrawn and {o["outcomes"]["denied"]["share_of_acted_pct"]}% denied. All 52 jurisdictions, every figure with a receipt. Not comparable with FHA rates as a judgement of programs.">\n'
        f'<link rel="canonical" href="https://financeratecalc.com/{out_name}">\n'
        '<link rel="license" type="application/rsl+xml" href="https://financeratecalc.com/rsl.xml">\n'
        f'{style}\n<body>\n{nav}\n<div class="wrap">\n'
        f'<div class="kicker">FinanceRateCalc &middot; {html.escape(longname)} loans &middot; 2025 &middot; first release {d["generated"][:10]}</div>\n'
        f'<h1>{short} loan denial rates in 2025: the national figure, the five outcomes, every state</h1>\n'
        f'<p><b>Short answer.</b> In 2025, <b>{n["denial_rate_pct"]:.1f}%</b> of decisioned {short} applications in the United States were denied: {fmt(n["denials"])} denials out of {fmt(n["decisioned_applications"])} applications that reached a credit decision (originated, approved but not accepted, or denied; reverse mortgages{closed_end} excluded). Receipt: <span class="r"><a href="/claims/{nat["id"]}.json">{html.escape(nat["receipt"])}</a></span>.</p>\n'
        f'<p class="small"><b>Read before comparing with FHA.</b> The published FHA rate (22.1%) and this {short} rate measure different applicant populations, defined by eligibility and composition. The difference is a fact about who applies for which program, not about which program or lender is easier. Every use contract on this page prohibits that inference. Purchase-only and refinance-only rates, and every denominator, are on the <a href="/denominator-map.html">denominator map</a>. Universe: <code>{html.escape(d["universe_id"])}</code>, declared before any figure was computed in <a href="https://github.com/financeratecalc/financeratecalc.github.io/blob/main/provenance/universe-expansion-2025.md">provenance/universe-expansion-2025.md</a>.</p>\n'
        '<h2>Where the applications ended, 2025</h2>\n'
        f'<p class="small">Of the <b>{fmt(o["applications_acted_on"])}</b> {short} applications lenders acted on (actions 1&ndash;5; purchased loans and preapproval requests excluded):</p>\n'
        '<table><thead><tr><th>End</th><th>Applications</th><th>Share of acted on</th><th>Receipt</th></tr></thead><tbody>'
        + "".join(f'<tr><td><b>{lab}</b></td><td class=n>{fmt(o["outcomes"][k]["n"])}</td><td class=n><b>{o["outcomes"][k]["share_of_acted_pct"]}%</b></td><td class="r"><a href="/claims/outcome-{prog}-{k.replace("_", "-")}-2025.json">{html.escape(rc[k])}</a></td></tr>' for k, lab in ends)
        + '</tbody></table>\n'
        f'<p class="small">The denied share above ({o["outcomes"]["denied"]["share_of_acted_pct"]}%) and the denial rate ({n["denial_rate_pct"]:.1f}%) are the same denials over two denominators; state the denominator with either.</p>\n'
        '<h2>By state, 2025</h2>\n'
        '<table><thead><tr><th>State</th><th>Decisioned</th><th>Denials</th><th>Denial rate</th><th>Receipt</th></tr></thead><tbody>' + rows + '</tbody></table>\n'
        '<h2>Definitions and build</h2>\n'
        f'<ul class="small"><li><b>Universe:</b> loan_type {d["loan_type"]} ({html.escape(d["program"])}); decisioned = action_taken 1, 2, 3; denial = 3; reverse mortgages excluded ({fmt(n["reverse_mortgage_excluded"])} rows){"; open-end lines of credit excluded" if prog == "conv" else f"; open-end rows seen: {n["open_end_rows_seen"]}"}.</li>\n'
        f'<li><b>Source and build:</b> CFPB HMDA 2025 public LAR extract ({html.escape(d["input"]["url"] or "")}), input sha256 <code>{(d["input"]["sha256"] or "")[:16]}&hellip;</code>, code <code>scripts/reference_implementation.py --loan-type {d["loan_type"]}</code> and <code>scripts/application_outcomes.py</code> at <code>{(d.get("code_commit") or "")[:10]}</code>; data file <a href="/data/programs/{prog}-2025.json">data/programs/{prog}-2025.json</a>.</li>\n'
        f'<li><b>Does not establish:</b> {html.escape(d["contract_note"])} Nor any individual\'s chance of denial, any lender-level figure, or any legal conclusion.</li>\n'
        '<li><b>Status:</b> first release (national, outcomes, states). Lender tables for this program follow only after a rebuild reproduces these files field for field, as for FHA. Verify any receipt at <a href="/verify.html">verify.html</a>.</li></ul>\n'
        '<p class="small">Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only. CC BY 4.0. Nothing on this page is advice about any loan.</p>\n'
        '</div>\n</body></html>\n')
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        print(f"{prog} page:", "current" if cur == page else "STALE"); sys.exit(0 if cur == page else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote {out_name}: {len(d['states'])} states")


if __name__ == "__main__":
    main()
