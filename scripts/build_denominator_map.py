#!/usr/bin/env python3
"""denominator-map.html: one program, one year, one set of denials — and every 'denial rate' that follows from choosing
a loan purpose, a denominator and a scope. Generated from data/purpose/*-2025.json and the claim documents; --check
exits 1 when stale; writes nothing when no data file exists. No number is typed here.

The page also lets a reader place a figure met elsewhere: type a percentage, see which cells produce it. A match is a
match, not an attribution; the page says so."""
import glob
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "denominator-map.html")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_official_page import shell  # noqa: E402

E = html.escape
ROWS = [("all", "All loan purposes"), ("purchase", "Home purchase"), ("refinance_all", "Refinance, including cash-out"), ("refinance", "&nbsp;&nbsp;refinance (not cash-out)"),
        ("cash_out_refinance", "&nbsp;&nbsp;cash-out refinance"), ("home_improvement", "Home improvement"), ("other", "Other purpose"), ("not_applicable", "Purpose not applicable")]
BASES = [("decisioned", "decisioned"), ("acted_on", "acted on"), ("denied_plus_originated", "denied + originated")]
ORDER = {"fha": 0, "va": 1, "usda": 2, "conv": 3}


def claim(cid):
    p = os.path.join(ROOT, "claims", cid + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "data", "purpose", "*-2025.json")), key=lambda f: ORDER.get(os.path.basename(f)[:-10], 9))
    if not files:
        print("denominator map: no data yet; page not written"); sys.exit(0)
    style, nav = shell()
    progs = [json.load(open(f, encoding="utf-8")) for f in files]
    blocks, lookup = [], []
    pct = lambda v: "&ndash;" if v is None else f"{v:.1f}%"
    for d in progs:
        pid, P = d["program_id"], d["program"]
        rc = {"all": claim("national-fha-denial-rate-2025" if pid == "fha" else f"{pid}-national-denial-rate-2025"),
              "purchase": claim(f"purpose-{pid}-purchase-denial-rate-2025"), "refinance_all": claim(f"purpose-{pid}-refinance-denial-rate-2025")}
        rows = ""
        for key, label in ROWS:
            c = d["cells"].get(key + "|all")
            if not c or not c["acted_on"]:
                continue
            s = d["cells"].get(key + "|standard")
            r = rc.get(key)
            rec = f'<br><span class="r small" style="word-break:break-all"><a href="/claims/{r["id"]}.json">{E(r["receipt"])}</a></span>' if r else ""
            rows += (f'<tr><td>{"<b>" + label + "</b>" if key in rc else label}{rec}</td><td class=n>{c["decisioned"]:,}</td><td class=n>{c["denied"]:,}</td>'
                     f'<td class=n><b>{pct(c["rate_pct"]["decisioned"])}</b></td><td class=n>{pct(c["rate_pct"]["acted_on"])}</td><td class=n>{pct(c["rate_pct"]["denied_plus_originated"])}</td>'
                     f'<td class=n>{pct(s["rate_pct"]["decisioned"]) if s else "&ndash;"}</td></tr>')
        for ck, c in d["cells"].items():
            purpose, scope = ck.split("|")
            for bk, bl in BASES:
                v = c["rate_pct"][bk]
                if v is not None and c["decisioned"] >= 1000:
                    lookup.append([P, dict(ROWS)[purpose].replace("&nbsp;", "").strip(), "first-lien, owner-occupied, site-built 1-4 unit" if scope == "standard" else "no further filter", bl, v])
        blocks.append(
            f'<h2>{E(P)} applications, 2025</h2>\n'
            f'<p class="small">{d["cells"]["all|all"]["acted_on"]:,} applications acted on; {d["cells"]["all|all"]["decisioned"]:,} reached a credit decision (the published {E(d["base_universe_id"])} count, reproduced by this run); reverse mortgages excluded. Input SHA-256 <code>{E((d["input"].get("sha256") or "")[:16])}&hellip;</code>.</p>\n'
            '<div style="overflow-x:auto"><table><thead><tr><th>Loan purpose</th><th>Decisioned</th><th>Denied</th><th>Denied / decisioned</th><th>Denied / acted on</th><th>Denied / (denied + originated)</th><th>Denied / decisioned, standard scope</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>\n')
    low = min(x[4] for x in lookup); high = max(x[4] for x in lookup)
    page = (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>The denominator map: why one year has many mortgage denial rates | FinanceRateCalc</title>\n'
        f'<meta name="description" content="One program, one year, one set of denials: the 2025 denial rate by loan purpose (purchase, refinance), by denominator (decisioned, acted on, denied plus originated) and by scope, for {", ".join(d["program"] for d in progs)}. Purchase and refinance rates carry receipts. Type a percentage to see which definition produces it.">\n'
        '<link rel="canonical" href="https://financeratecalc.com/denominator-map.html">\n'
        '<link rel="license" type="application/rsl+xml" href="https://financeratecalc.com/rsl.xml">\n'
        f'{style}\n<body>\n{nav}\n<div class="wrap">\n'
        f'<div class="kicker">FinanceRateCalc &middot; denominator map &middot; 2025 &middot; generated {progs[0]["generated"][:10]}</div>\n'
        '<h1>The denominator map: one year, many &ldquo;denial rates&rdquo;</h1>\n'
        f'<p><b>Short answer.</b> There is no single mortgage denial rate for a program and a year. The same public file gives figures from {low:.1f}% to {high:.1f}% for the programs below, depending on three choices: which <b>loan purpose</b> is counted, which applications are in the <b>denominator</b>, and whether a <b>scope filter</b> is applied. A figure quoted without those three is not wrong so much as unplaceable. This page shows every cell, so any figure can be placed.</p>\n'
        '<p class="small"><b>The three denominators.</b> <i>Decisioned</i>: originated, approved but not accepted, or denied (this site&rsquo;s published definition). <i>Acted on</i>: decisioned plus withdrawn and closed-for-incompleteness files. <i>Denied + originated</i>: approvals the applicant did not accept are left out. <b>Standard scope</b>: first lien, owner-occupied principal residence, site-built, 1&ndash;4 units. Bold rows carry receipts; the other cells are a reference table from the same run.</p>\n'
        + "".join(blocks) +
        '<h2>Place a figure</h2>\n'
        '<p class="small">Met a denial rate somewhere and cannot tell what it measures? Type it. The cells within 0.15 points are listed. <b>A match is a match, not an attribution:</b> it shows which definition <i>can</i> produce the number from the 2025 file, not which one its publisher used. No match means the figure comes from another year, another filter, or cannot be reproduced from this file.</p>\n'
        '<p><label for="pf">Percentage</label> <input id="pf" type="number" step="0.01" min="0" max="100" inputmode="decimal" style="width:7em;padding:6px 8px;background:transparent;color:inherit;border:1px solid rgba(255,255,255,.3);border-radius:4px"> <button id="pb" type="button" style="padding:6px 12px;cursor:pointer">Find cells</button></p>\n'
        '<div id="po" class="small" aria-live="polite" style="overflow-x:auto"></div>\n'
        f'<script>const CELLS={json.dumps(lookup, separators=(",", ":"))};\n'
        'function place(){const v=parseFloat(document.getElementById("pf").value),o=document.getElementById("po");if(isNaN(v)){o.textContent="Type a percentage, for example 12.2.";return}\n'
        'const h=CELLS.filter(c=>Math.abs(c[4]-v)<=0.15).sort((a,b)=>Math.abs(a[4]-v)-Math.abs(b[4]-v));\n'
        'if(!h.length){o.textContent="No cell of the 2025 file within 0.15 points of "+v+"%. The figure may come from another year or another filter.";return}\n'
        'const t=document.createElement("table");t.innerHTML="<thead><tr><th>Program</th><th>Loan purpose</th><th>Scope</th><th>Denominator</th><th>Rate</th></tr></thead>";const b=document.createElement("tbody");\n'
        'h.forEach(c=>{const r=document.createElement("tr");c.forEach((x,i)=>{const d=document.createElement("td");d.textContent=i==4?x.toFixed(2)+"%":x;r.appendChild(d)});b.appendChild(r)});t.appendChild(b);o.textContent="";o.appendChild(t)}\n'
        'document.getElementById("pb").addEventListener("click",place);document.getElementById("pf").addEventListener("keydown",e=>{if(e.key==="Enter")place()});</script>\n'
        '<h2>What this page does not establish</h2>\n'
        '<ul class="small"><li>Which denominator any other publisher used.</li><li>That purchase loans are easier to obtain than refinances, or one program easier than another: the applicant populations differ by eligibility and composition.</li>'
        '<li>Any individual&rsquo;s chance of denial, or any lender-level figure.</li></ul>\n'
        '<p class="small">Method: <code>scripts/denominator_grid.py</code>; data: <a href="/data/purpose/">data/purpose/</a>; universes declared before the figures in <a href="https://github.com/financeratecalc/financeratecalc.github.io/blob/main/provenance/universe-purpose-split-2025.md">provenance/universe-purpose-split-2025.md</a>. Verify any receipt at <a href="/verify.html">verify.html</a>. Source: FinanceRateCalc analysis of the public CFPB HMDA 2025 record; historical aggregate only. CC BY 4.0. Not advice about any loan.</p>\n'
        '</div>\n</body></html>\n')
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        print("denominator map:", "current" if cur == page else "STALE"); sys.exit(0 if cur == page else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote denominator-map.html: {len(progs)} programs, {len(lookup)} placeable cells")


if __name__ == "__main__":
    main()
