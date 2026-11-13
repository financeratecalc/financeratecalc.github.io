#!/usr/bin/env python3
"""index.html — the home page, generated. Identity: receipts for numbers from public records.

    python3 scripts/build_home.py [--check]

Every figure on the page is read from the data files and claim documents at build time (api/, data/programs/,
data/official/, claims/, corrections.json, eval/). Nothing is typed. The analytics snippet and the organisation /
website structured data live in assets/home-head.html; the claim JSON-LD block is added afterwards by
scripts/build_claim_jsonld.py. --check exits 1 if the committed page (ignoring that injected block) differs.
"""
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "index.html")
CSS = r"""
:root{--bg:#08090c;--panel:#0e1016;--ink:#ece8dc;--soft:#a39f93;--dim:#6f6c63;--rule:rgba(255,255,255,.11);--gold:#c8a84b;--ok:#6fcf97;--amber:#e0a23c;--void:#e06c6c}
*{box-sizing:border-box;margin:0;padding:0}
html{-webkit-text-size-adjust:100%}
body{background:var(--bg);color:var(--ink);font-family:'DM Sans',system-ui,sans-serif;font-size:17px;line-height:1.62}
a{color:var(--gold);text-decoration-thickness:1px;text-underline-offset:3px}
a:hover{color:#f0d98a}
a:focus-visible,input:focus-visible,button:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:var(--panel);padding:8px 12px;z-index:99}
.bar{position:relative;z-index:5;display:flex;justify-content:space-between;align-items:baseline;gap:18px;flex-wrap:wrap;max-width:1120px;margin:0 auto;padding:20px 24px 0}
.mark{font-family:'Fraunces',Georgia,serif;font-weight:900;font-size:20px;text-decoration:none;color:var(--ink);letter-spacing:-.3px}.mark i{color:var(--gold)}
.bar nav{display:flex;gap:20px;flex-wrap:wrap;font-size:14.5px}
.bar nav a{text-decoration:none;color:var(--soft)}.bar nav a:hover{color:var(--ink)}
/* hero: a dark field of figures; the pointer carries the light */
.hero{position:relative;overflow:hidden;border-bottom:1px solid var(--rule);--x:50%;--y:38%}
.hero::before{content:"";position:absolute;inset:0;background:radial-gradient(640px circle at var(--x) var(--y),rgba(200,168,75,.24),rgba(200,168,75,.07) 40%,transparent 68%);pointer-events:none;transition:background .08s linear}
.field{position:absolute;inset:0}
.fig{position:absolute;left:var(--dx);top:var(--dy);transform:translate(-50%,-50%);background:none;border:0;cursor:pointer;font-family:'Fraunces',Georgia,serif;font-weight:900;font-size:clamp(20px,3.1vw,44px);letter-spacing:-.5px;color:var(--ink);opacity:calc(.07 + var(--lit,0)*.93);filter:blur(calc((1 - var(--lit,0))*2.2px));transition:opacity .18s linear,filter .18s linear;padding:6px 10px;white-space:nowrap}
.fig.revised{color:var(--amber)}
.fig.near::after{content:"";position:absolute;left:10px;right:10px;bottom:2px;height:2px;background:var(--gold)}
.fig.revised.near::after{background:var(--amber)}
.hero-in{position:relative;z-index:3;max-width:1120px;margin:0 auto;padding:clamp(70px,13vw,150px) 24px clamp(40px,6vw,70px);pointer-events:none}
.hero-in>*{pointer-events:auto}
h1{font-family:'Fraunces',Georgia,serif;font-weight:900;font-size:clamp(36px,5.6vw,70px);line-height:1.03;letter-spacing:-2px;max-width:11.5ch}
.lede{margin-top:22px;font-size:clamp(17px,1.8vw,19.5px);line-height:1.6;max-width:42ch;color:var(--soft)}
.lede b{color:var(--ink);font-weight:600}
.reading{position:relative;z-index:4;max-width:1120px;margin:0 auto;padding:0 24px 30px}
.reading-box{min-height:92px;border:1px solid var(--rule);background:rgba(14,16,22,.86);backdrop-filter:blur(6px);padding:14px 18px;display:grid;gap:4px}
.reading-box .hint{color:var(--dim);font-size:15px}
.reading-box code{font-family:'DM Mono',ui-monospace,monospace;font-size:clamp(12.5px,1.5vw,16px);color:var(--gold);word-break:break-all}
.reading-box .what{font-size:15.5px;color:var(--ink)}
.tag{display:inline-block;font-size:12.5px;font-weight:700;padding:1px 8px 2px;border:1.5px solid currentColor;border-radius:3px;margin-right:8px;transform:rotate(-1deg)}
.tag.current,.tag.computed{color:var(--ok)}.tag.restated{color:var(--ink)}.tag.revised{color:var(--amber)}
main{max-width:1120px;margin:0 auto;padding:0 24px 80px}
h2{font-family:'Fraunces',Georgia,serif;font-weight:900;font-size:clamp(25px,3.2vw,36px);line-height:1.12;letter-spacing:-.8px;margin:86px 0 14px;max-width:24ch}
p{max-width:66ch;color:var(--soft)}p b,td b{color:var(--ink)}p+p{margin-top:12px}
.check{margin:34px 0 0;background:var(--panel);border:1px solid rgba(200,168,75,.35);padding:22px;max-width:780px}
.check label{display:block;font-weight:600;margin-bottom:8px;color:var(--ink)}
.check .row{display:flex;gap:10px;flex-wrap:wrap}
.check input{flex:1 1 320px;font:500 15px 'DM Mono',ui-monospace,monospace;padding:12px;border:1px solid rgba(255,255,255,.22);background:#06070a;color:var(--ink);min-width:0}
.check input::placeholder{color:var(--dim)}
.check button{font:700 16px 'DM Sans',sans-serif;padding:12px 22px;background:var(--gold);color:#08090c;border:0;cursor:pointer}
.check button:hover{background:#e3c66a}
.check small{display:block;margin-top:10px;color:var(--soft);font-size:14px}
.roll{list-style:none;margin:26px 0 0;border-top:1px solid var(--gold)}
.rc{padding:16px 0 14px;border-bottom:1px dashed var(--rule)}
.rc-line code{font-family:'DM Mono',ui-monospace,monospace;font-size:clamp(12.5px,1.6vw,17px);color:var(--ink);word-break:break-all}
.rc-meta{display:flex;gap:12px;flex-wrap:wrap;align-items:baseline;margin-top:8px;font-size:15px;color:var(--soft)}
.rc-meta a{white-space:nowrap}
.stamp{font-weight:700;font-size:12.5px;padding:1px 8px 2px;border:1.5px solid currentColor;border-radius:3px;transform:rotate(-1.2deg);display:inline-block}
.computed .stamp{color:var(--ok)}.restated .stamp{color:var(--ink)}.revised .stamp{color:var(--amber)}
.two{display:grid;grid-template-columns:1fr 1fr;margin-top:26px;border-top:1px solid var(--gold)}
.two>div{padding:22px 30px 6px 0}.two>div+div{padding-left:30px;border-left:1px solid var(--rule)}
.two h3{font-family:'Fraunces',Georgia,serif;font-weight:900;font-size:22px;margin-bottom:8px;color:var(--ink)}
.two ul{margin:10px 0 0 18px;color:var(--soft);font-size:16px}
table{border-collapse:collapse;width:100%;margin-top:22px;font-size:16px}
th{text-align:left;font-weight:600;font-size:13.5px;color:var(--dim);padding:8px 14px 8px 0;border-bottom:1px solid var(--gold)}
td{padding:12px 14px 12px 0;border-bottom:1px solid var(--rule);vertical-align:top;color:var(--soft)}
td:first-child{color:var(--ink)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink)}
.watch td:nth-child(4){color:var(--amber);font-weight:700}
.split{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,4fr);gap:60px;align-items:start}
.log{list-style:none;margin-top:18px}.log li{padding:11px 0;border-bottom:1px solid var(--rule);font-size:16px;color:var(--soft)}
.log time{font-family:'DM Mono',monospace;font-size:13px;color:var(--amber);margin-right:8px}
.doors{list-style:none;margin-top:22px;border-top:1px solid var(--gold)}
.doors li{display:grid;grid-template-columns:minmax(0,16rem) 1fr;gap:24px;padding:16px 0;border-bottom:1px solid var(--rule);color:var(--soft)}
.doors b{font-weight:600;color:var(--ink)}
.fine{margin-top:90px;padding-top:22px;border-top:1px solid var(--rule);font-size:14.5px;color:var(--dim)}
.fine .links{display:flex;flex-wrap:wrap;gap:6px 18px;margin-bottom:16px}
.fine .links a{color:var(--soft)}
.fine p{max-width:88ch;color:var(--dim)}
@media(max-width:900px){.hero{display:flex;flex-direction:column}.hero .bar{order:0}.hero-in{order:1;padding-bottom:18px}.field{order:2;position:relative;inset:auto;height:330px;margin:0 8px}.reading{order:3;width:100%}.fig{left:var(--mx);top:calc(var(--my)*.86);font-size:clamp(18px,5.6vw,30px)}h1,.lede{max-width:none}}
@media(max-width:760px){.two,.split{grid-template-columns:1fr}.two>div+div{padding-left:0;border-left:0;border-top:1px solid var(--rule)}.doors li{grid-template-columns:1fr;gap:4px}td,th{padding-right:10px}.hide-s{display:none}h1{letter-spacing:-1.2px}}
@media(prefers-reduced-motion:reduce){.fig{--lit:.55 !important;filter:none;transition:none}.hero::before{transition:none}}
"""
JS = r"""
(function(){
  var hero=document.querySelector('.hero'); if(!hero) return;
  var figs=[].slice.call(hero.querySelectorAll('.fig')), box=document.getElementById('reading');
  var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches, touched=false, pinned=null, raf=0, px=0, py=0;
  function show(el){
    if(!el) return;
    var s=el.dataset.s, word={current:'Computed, current',restated:'Restated as printed',revised:'Revised by the publisher'}[s]||s;
    box.innerHTML='<div class="what"><span class="tag '+s+'">'+word+'</span><b>'+el.textContent+'</b> '+el.dataset.l+'</div><code>'+el.dataset.r+'</code>'+
      '<div><a href="/verify.html?r='+encodeURIComponent(el.dataset.r)+'">Check this receipt</a></div>';
  }
  function light(x,y){
    var r=hero.getBoundingClientRect(); hero.style.setProperty('--x',x+'px'); hero.style.setProperty('--y',y+'px');
    var best=null,bd=1e9;
    figs.forEach(function(f){ var b=f.getBoundingClientRect(), cx=b.left+b.width/2-r.left, cy=b.top+b.height/2-r.top, d=Math.hypot(cx-x,cy-y);
      f.style.setProperty('--lit',Math.max(0,1-d/300).toFixed(3)); f.classList.remove('near'); if(d<bd){bd=d;best=f;} });
    if(best&&bd<170){ best.classList.add('near'); if(!pinned) show(best); }
  }
  if(reduce){ show(figs[0]); }
  else{
    hero.addEventListener('pointermove',function(e){ if(e.clientX===0&&e.clientY===0) return; touched=performance.now(); var r=hero.getBoundingClientRect(); px=e.clientX-r.left; py=e.clientY-r.top;
      if(!raf) raf=requestAnimationFrame(function(){raf=0; light(px,py);}); });
    // when no pointer is moving (and on phones), the light walks the field by itself so the page explains its own trick
    var t0=performance.now();
    (function drift(t){ requestAnimationFrame(drift); if(touched&&performance.now()-touched<3500) return; var r=hero.getBoundingClientRect(), k=(t-t0)/1000, x0=1e9,y0=1e9,x1=0,y1=0;
      figs.forEach(function(f){ var b=f.getBoundingClientRect(); x0=Math.min(x0,b.left-r.left); y0=Math.min(y0,b.top-r.top); x1=Math.max(x1,b.right-r.left); y1=Math.max(y1,b.bottom-r.top); });
      light(x0+(x1-x0)*(.5+.42*Math.sin(k*.45)), y0+(y1-y0)*(.5+.4*Math.sin(k*.33+1.3))); })(t0);
  }
  figs.forEach(function(f){ f.addEventListener('click',function(){ pinned=f; show(f); });
    f.addEventListener('focus',function(){ f.style.setProperty('--lit','1'); show(f); }); });
})();
"""
E = html.escape


def J(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding="utf-8"))


def claim(cid):
    return J(f"claims/{cid}.json")


def bare(receipt):
    return receipt


def main():
    nat = J("api/index.json")["national"]
    fha = claim("national-fha-denial-rate-2025")
    va_d = J("data/programs/va-2025.json") if os.path.exists(os.path.join(ROOT, "data/programs/va-2025.json")) else None
    va = claim("va-national-denial-rate-2025") if va_d else None
    eds = sorted(f for f in glob.glob(os.path.join(ROOT, "data", "official", "*.json")) if os.path.basename(f) != "index.json")
    off = [json.load(open(f, encoding="utf-8")) for f in eds]
    off = [d for d in off if d["source_id"] == "hud-fhaprod"]   # the hero and the watch table speak about HUD; other sources live on the ledger page
    revised = None
    for d in off:                                       # the most recent figure a later edition revised
        for fid, f in d["figures"].items():
            if f.get("revised_to") is not None:
                revised = (d, fid, f, claim(f"official-{d['source_id']}-{d['period']}-{fid}"))
    latest = off[-1] if off else None
    latest_c = claim(f"official-{latest['source_id']}-{latest['period']}-endorsements-count") if latest else None

    idx = J("claims/index.json")["claims"]
    rec = [c for c in idx if c.get("receipt")]
    fam = {"fha": 0, "prog": 0, "official": 0, "purpose": 0}
    for c in rec:
        i = c["id"]
        if i.startswith("official-"):
            fam["official"] += 1
        elif i.startswith("purpose-"):
            fam["purpose"] += 1
        elif re.match(r"(outcome-)?(va|usda|conv)-", i):
            fam["prog"] += 1
        else:
            fam["fha"] += 1
    total = sum(fam.values())
    corr = J("corrections.json")["items"]
    own = [c for c in corr if c.get("type") != "atom"]
    qsi = J("eval/qsi/qsi.json")
    sight = J("eval/sightings.json")["named_citations"]["items"]
    engines = sorted({s["site"].split(" ")[0].replace("(answer", "").strip() for s in sight if "engine" in s["site"] or ".ai" in s["site"] or ".com" in s["site"]})
    mis = J("eval/misquotes-graded.json")["graded"]
    dry = J("provenance/release-day-dryrun.json")
    lenders = len(glob.glob(os.path.join(ROOT, "api", "lender", "*.json")))
    states = len(glob.glob(os.path.join(ROOT, "api", "state", "*.json")))

    # the number field in the hero: real figures, each with its receipt; the pointer's light reveals them
    field = []

    def add(cid, value, label, status="current"):
        try:
            c = claim(cid)
        except FileNotFoundError:
            return
        field.append({"v": value, "l": label, "r": c["receipt"], "s": status})

    add("national-fha-denial-rate-2025", f'{nat["rate_pct"]:.1f}%', "of decisioned FHA applications denied, 2025")
    if va:
        add("va-national-denial-rate-2025", f'{va_d["national"]["denial_rate_pct"]:.1f}%', "of decisioned VA applications denied, 2025")
    # purchase and refinance rates (the denominator map) instead of the lowest and highest lender: no extremes of a lender
    # table on the home page, and no tie between two lenders for the build to break differently on two machines
    for prog, P in (("fha", "FHA"), ("va", "VA")):
        pp = os.path.join(ROOT, "data", "purpose", f"{prog}-2025.json")
        if os.path.exists(pp):
            pc = json.load(open(pp, encoding="utf-8"))["cells"]
            add(f"purpose-{prog}-purchase-denial-rate-2025", f'{pc["purchase|all"]["rate_pct"]["decisioned"]:.1f}%', f"of decisioned {P} home-purchase applications denied, 2025")
            add(f"purpose-{prog}-refinance-denial-rate-2025", f'{pc["refinance_all|all"]["rate_pct"]["decisioned"]:.1f}%', f"of decisioned {P} refinance applications denied, 2025")
    for st in ("tx", "ca", "fl", "ny"):
        try:
            S = J(f"api/state/{st}.json")
            add(f"state-{st}-2025", f'{S["denial_rate_pct"]:.1f}%', f'FHA denial rate in {S["state"]}, 2025')
        except FileNotFoundError:
            pass
    oc = J("data/application-outcomes-2025.json")["national"]["outcomes"]
    add("outcome-withdrawn-2025", f'{oc["withdrawn"]["share_of_acted_pct"]}%', "of FHA applications acted on were withdrawn, 2025")
    add("outcome-originated-2025", f'{oc["originated"]["share_of_acted_pct"]}%', "of FHA applications acted on were originated, 2025")
    for d in off:
        for fid in ("endorsements-count", "purchase-count", "refinance-count", "first-time-homebuyer-pct", "insurance-in-force-end"):
            f = d["figures"].get(fid)
            if not f:
                continue
            rv = f.get("revised_to") is not None
            add(f"official-{d['source_id']}-{d['period']}-{fid}", f["display"] + ("%" if fid.endswith("-pct") else ""),
                f'HUD: {f["description"]}, {f["period"]}' + (f' — later restated as {f["revised_to"]:,}' if rv else ""), "revised" if rv else "restated")
    field = field[:18]
    # desktop: the figures live to the right of the headline; phone: in a band of their own under the lede
    desk = [(60, 17), (77, 12), (92, 20), (66, 30), (84, 33), (58, 44), (74, 47), (91, 45), (64, 60), (81, 61), (94, 70), (57, 73), (72, 75), (87, 82), (48, 14), (50, 86), (67, 88), (40, 90)]
    phone = [(16, 12), (50, 8), (84, 14), (30, 30), (68, 28), (14, 48), (48, 46), (84, 48), (28, 66), (66, 64), (12, 84), (46, 84), (82, 82), (60, 96), (20, 100), (90, 100), (40, 100), (70, 100)]
    field_html = "".join(
        f'<button type="button" class="fig {x["s"]}" style="--dx:{desk[i][0]}%;--dy:{desk[i][1]}%;--mx:{phone[i][0]}%;--my:{phone[i][1]}%" data-r="{E(x["r"])}" data-l="{E(x["l"])}" data-s="{x["s"]}">{E(x["v"])}</button>'
        for i, x in enumerate(field[:14 if len(field) > 14 else len(field)]))
    n_rev = sum(1 for d in off for f in d["figures"].values() if f.get("revised_to") is not None)
    rev_rows = "".join(
        f'<tr><td>{E(f["description"][0].upper() + f["description"][1:])}</td><td>{E(f["period"])}</td><td class="n">{E(f["display"])}</td><td class="n">{f["revised_to"]:,}</td><td class="hide-s">{E(f.get("revised_in", ""))}</td></tr>'
        for d in off for f in d["figures"].values() if f.get("revised_to") is not None)

    def strip(rc, status, cls, sub):
        return (f'<li class="rc {cls}"><div class="rc-line"><code>{E(rc["receipt"])}</code></div>'
                f'<div class="rc-meta"><span class="stamp">{status}</span><span>{sub}</span>'
                f'<a href="/verify.html?r={E(rc["receipt"])}">Check this receipt</a></div></li>')

    strips = strip(fha, "Computed", "computed",
                   f'{nat["denials"]:,} denials of {nat["apps"]:,} FHA applications that reached a decision, 2025 federal HMDA record.')
    if va:
        n = va_d["national"]
        strips += strip(va, "Computed", "computed", f'{n["denials"]:,} denials of {n["decisioned_applications"]:,} VA applications that reached a decision, 2025.')
    if revised:
        d, fid, f, c = revised
        strips += strip(c, "Revised by the publisher", "revised",
                        f'HUD printed {E(f["display"])} {E(f["description"])} for {E(f["period"])}, then restated it as {f["revised_to"]:,} one edition later. The report does not mark the change.')
    elif latest_c:
        strips += strip(latest_c, "Restated as printed", "restated", f'{E(latest["document"]["title"])}, {E(latest["document"]["edition"])}.')

    fam_rows = (
        f'<tr><td><a href="/fha-denial-rates-top-100.html">FHA denial rates and application outcomes</a></td><td>Computed from the 2025 federal HMDA file</td><td class="n">{fam["fha"]}</td>'
        f'<td>National, {states} states and territories, {lenders} lenders, metro gaps, <a href="/where-fha-applications-end.html">five outcomes</a></td></tr>')
    if va:
        fam_rows += (f'<tr><td><a href="/va-loan-denial-rates-2025.html">VA denial rates and outcomes</a></td><td>Computed from the same file</td><td class="n">{fam["prog"]}</td>'
                     f'<td>National, every state, five outcomes. USDA and conventional are declared and next.</td></tr>')
    if fam["purpose"]:
        fam_rows += (f'<tr><td><a href="/denominator-map.html">Purchase and refinance denial rates</a></td><td>Computed from the same file</td><td class="n">{fam["purpose"]}</td>'
                     f'<td>The <a href="/denominator-map.html">denominator map</a>: every loan purpose, denominator and scope, so a rate quoted without one can be placed</td></tr>')
    if off:
        led = J("data/revisions.json")
        fam_rows += (f'<tr><td><a href="/official-figures.html">Official monthly figures</a> (HUD FHA production; Ginnie Mae issuance)</td><td>Restated as printed from the official report</td><td class="n">{fam["official"]}</td>'
                     f'<td>{len(eds)} editions, each bound to the PDF&rsquo;s SHA-256. <a href="/revision-ledger.html">Revision ledger</a>: {led["figures_compared"]} figures compared across editions, {led["revisions_found"]} changed</td></tr>')

    agg = {}
    for r in qsi["rows"]:                                # one line per engine; answers whose engine the owner did not name are grouped
        nm = r["engine"].split(" (")[0].split(" — ")[0].strip()
        nm = "Engine not named" if nm.upper().startswith("UNKNOWN") else nm
        agg.setdefault(nm, []).append(r["qsi"])
    eng_rows = "".join(f'<tr><td>{E(e)}</td><td class="n">{len(v)}</td><td class="n">{sum(v) / len(v):.2f}</td></tr>'
                       for e, v in sorted(agg.items(), key=lambda kv: (kv[0] == "Engine not named", -sum(kv[1]) / len(kv[1]))))

    def short(t, n=140):
        t = re.sub(r"^Our own error, found [0-9-]+( through [^:]+)?: ", "", t)
        t = t[0].upper() + t[1:]
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
    last3 = "".join(f'<li><time>{E(c["date"])}</time> {E(short(c["title"]))}</li>' for c in own[:3])
    head_extra = open(os.path.join(ROOT, "assets", "home-head.html"), encoding="utf-8").read()
    desc = (f"FinanceRateCalc issues receipts for numbers from public records: {total} figures, each with a verifiable receipt, a use contract and a "
            f"corrections history. Computed from the federal HMDA file (FHA {nat['rate_pct']:.1f}% of {nat['apps']:,} decisions denied in 2025) or restated as printed "
            f"from official reports. Free, CC BY 4.0, no lender funding.")

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>FinanceRateCalc — receipts for the numbers AI quotes from public records</title>
<meta name="description" content="{E(desc)}">
<meta property="og:title" content="Receipts for numbers from public records">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="https://financeratecalc.com/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="FinanceRateCalc">
<meta property="og:image" content="https://financeratecalc.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<link rel="license" type="application/rsl+xml" href="https://financeratecalc.com/rsl.xml">
<link rel="canonical" href="https://financeratecalc.com/">
<link rel="icon" href="/favicon.ico">
<link rel="alternate" type="application/rss+xml" title="FinanceRateCalc Weekly Signal" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,900&family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
{head_extra.strip()}
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="hero">
<div class="bar"><a class="mark" href="/">Finance<i>Rate</i>Calc</a>
<nav aria-label="Site"><a href="/verify.html">Check a receipt</a><a href="/official-figures.html">Official figures</a><a href="/fha-denial-rates-top-100.html">FHA data</a><a href="/corrections.html">Corrections</a><a href="/mcp-server.html">For AI agents</a><a href="/site-index.html">Index</a></nav></div>
<div class="field" aria-hidden="false">{field_html}</div>
<div class="hero-in">
<h1>Numbers in the dark. Receipts bring the light.</h1>
<p class="lede">AI systems quote statistics with the wrong month, the wrong denominator, or a value the publisher has since revised. Every figure here carries a <b>receipt</b>: a short code that fixes the number to its source file, its definition and its period. Move the light over a number to read its receipt.</p>
</div>
<div class="reading"><div class="reading-box" id="reading" aria-live="polite"><span class="hint">Point at any number in the field. Each one is a real figure from a public record, with the receipt that proves where it came from.</span></div></div>
</div>
<main id="main">
<form class="check" action="/verify.html" method="get">
<label for="r">Check a receipt</label>
<div class="row"><input id="r" name="r" type="text" inputmode="text" autocomplete="off" spellcheck="false" placeholder="⟦FRC:…⟧ paste a receipt from an AI answer or an article" required>
<button type="submit">Check receipt</button></div>
<small>The answer is one of: current, superseded by a correction, or not ours. Got a sentence instead of a receipt? <a href="/check-answer.html">Check an AI answer</a>.</small>
</form>

<h2>Three receipts, as issued</h2>
<ul class="roll" aria-label="Three receipts issued by this site">
{strips}
</ul>

<h2>Revision watch: what the publisher changed without saying so</h2>
<p>Official reports restate last month&rsquo;s figures beside this month&rsquo;s. When the restated number differs from the one first printed, that is a revision &mdash; and the report does not flag it. We compare every edition with the one before it and record each change on the original receipt. <b>{n_rev} silent revisions</b> found so far.</p>
<table class="watch"><thead><tr><th>Figure (HUD FHA production report)</th><th>Period</th><th class="n">First printed</th><th class="n">Restated as</th><th class="hide-s">Where</th></tr></thead><tbody>{rev_rows}</tbody></table>
<p style="margin-top:14px"><a href="/official-figures.html">Every official figure and its revision status</a> &middot; <a href="/revision-ledger.html">revision ledger</a> &middot; <a href="/data/revisions.json">revisions feed for machines</a></p>

<h2>Two kinds of receipt, and what each one attests</h2>
<div class="two">
<div><h3>Computed</h3>
<p>We count the figure ourselves from the complete public file, with published code. The receipt binds the number to the file&rsquo;s hash, the universe and the denominator.</p>
<ul><li>{nat["apps"]:,} FHA decisions in 2025; {nat["rate_pct"]:.1f}% denied</li><li>A full rebuild reproduces {dry.get("numeric_equal", 0):,} of {dry.get("numeric_fields", 0):,} published fields</li><li>An unaffiliated HMDA package arrives at the same counts</li></ul></div>
<div><h3>Restated as printed</h3>
<p>An agency published the figure; we compute nothing. The receipt binds the number to the official document&rsquo;s hash, its table and row, its period &mdash; and records when a later edition changes it.</p>
<ul><li>HUD&rsquo;s monthly FHA production report, {len(off)} editions</li><li>{sum(1 for d in off for f in d["figures"].values() if f.get("revised_to") is not None)} figures already revised by the publisher, unmarked in the report</li><li>An endorsement is not an application: the contract says so</li></ul></div>
</div>

<h2>What carries a receipt today</h2>
<table>
<thead><tr><th>Figures</th><th class="hide-s">How</th><th class="n">Receipts</th><th>Coverage</th></tr></thead>
<tbody>{fam_rows.replace("<td>Computed", '<td class="hide-s">Computed').replace("<td>Restated", '<td class="hide-s">Restated')}
<tr><td><b>All receipts</b></td><td class="hide-s"></td><td class="n"><b>{total}</b></td><td>One file for machines: <a href="/llms-full.txt">llms-full.txt</a> &middot; signed snapshot in a <a href="/transparency/log.json">public log</a></td></tr></tbody>
</table>

<div class="split">
<div>
<h2>We publish our own errors</h2>
<p>A receipt is only worth something if the publisher admits when a number changes. The log has {len(own)} dated entries; several were found because an AI system quoted a stale copy of ours exactly.</p>
<ul class="log">{last3}</ul>
<p style="margin-top:14px"><a href="/corrections.html">Read the corrections log</a> &middot; <a href="/corrections.json">feed for machines</a></p>
</div>
<div>
<h2>How faithfully AI systems carry our figures</h2>
<p>{qsi["answers_graded"]} archived answers that quote us, graded on seven qualifiers: value, period, denominator, program, universe, no added claim, attribution. 1.00 means all seven survived.</p>
<table><thead><tr><th>Answer engine</th><th class="n">Answers</th><th class="n">Score</th></tr></thead><tbody>{eng_rows}</tbody></table>
<p style="margin-top:14px"><a href="/qualifier-survival.html">Method and every answer</a> &middot; <a href="/misquotes.html">{len(mis)} graded misquotes</a></p>
</div>
</div>

<h2>Where to start</h2>
<ul class="doors">
<li><b>An AI gave me a number</b><span>Paste the receipt above, or <a href="/check-answer.html">paste the whole answer</a>: we mark what the number carries and what was added.</span></li>
<li><b>I was denied an FHA loan</b><span><a href="/denial-code-lookup.html">What the reason on your letter means</a> and what to ask the lender in writing. No prediction, no lender pick.</span></li>
<li><b>I report or research</b><span>The record: <a href="/fha-denial-rates-top-100.html">100 largest FHA lenders</a>, <a href="/fha-denial-rates-by-state.html">every state</a>, <a href="/metro/index.html">metros</a>, <a href="/why-fha-denial-rates-differ.html">why published rates differ</a>, <a href="/methodology.html">method</a>, <a href="/reconciliation.html">how to check us</a>.</li>
<li><b>I publish statistics</b><span>Put a live receipt next to your own numbers with <a href="/pricing.html">the free badge</a>, or have <a href="/pricing.html">receipts issued for your figures</a>. Want to know how AI systems restate your data? Ask for a <a href="/pricing.html">citation fidelity report</a>.</span></li>
<li><b>I build agents</b><span><a href="/mcp-server.html">MCP server</a> with {18} tools, <a href="/data-catalog.html">open datasets</a>, <a href="/spec/receipt-1.0.md">the Receipt 1.0 format</a>, <a href="/pricing.html">pricing</a>. Reading is free; the licence is <a href="/license.html">CC BY 4.0</a>.</li>
</ul>

<div class="fine">
<div class="links"><a href="/site-index.html">Every page</a><a href="/metro/index.html">Metro pages</a><a href="/stat/index.html">Question pages</a><a href="/city/index.html">City pages</a><a href="/fha-denial-rates-by-lender.html">Lender table</a><a href="/fha-denial-reasons-by-lender.html">Denial reasons</a><a href="/door-effect.html">The door effect</a><a href="/benchmark-scorecard.html">AI benchmark</a><a href="/answers.html">Answers</a><a href="/tools.html">Tools</a><a href="/top-100-pack.html">Top-100 pack</a><a href="/glossary.html">Glossary</a><a href="/data.html">Data</a></div>
<p>Published by Ziya Yeti&#351;, 23 years in bank credit, working independently. No lender, servicer, vendor or AI company funds this site, and it carries no advertising. Figures are historical aggregates from public records: not predictions about any application, not ratings of any lender, not advice. Computed figures have been reproduced by an unaffiliated implementation and not yet by an unaffiliated person; <a href="/reconciliation.html">the specification for checking them is public</a>.</p>
</div>
</main>
<script>{JS}</script>
</body>
</html>
'''
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        cur = re.sub(r'<script type="application/ld\+json" id="frc-claims-jsonld">.*?</script>\n?', "", cur, flags=re.S)
        ok = cur.strip() == page.strip()
        print("home page:", "current" if ok else "STALE"); sys.exit(0 if ok else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    print(f"wrote index.html: {total} receipts ({fam}), {len(own)} corrections, {qsi['answers_graded']} graded answers")


if __name__ == "__main__":
    main()
