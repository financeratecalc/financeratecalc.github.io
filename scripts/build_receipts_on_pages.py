#!/usr/bin/env python3
"""Put claim receipts on the site's figure-bearing pages.

A receipt  ⟦FRC:<id>:<value>:<hash8>⟧  is computed exactly as the worker's /verify does
(rl-env/frc_citation/verify_offline.py). Each page gets:
  - a visible receipt line next to its headline figure, linking to /verify.html
  - the same receipt as a PropertyValue in its Dataset JSON-LD `identifier`
Idempotent: receipt lines live between <!--RECEIPT:id--> ... <!--/RECEIPT--> markers and
are replaced on every run. A page whose headline value does not equal the data value is
skipped and reported; that mismatch is a publisher error, not something to paper over.

Pages: how-often-are-fha-loans-denied.html (national), fha-denial-rates-top-100.html
(AmeriSave + Flat Branch), 100 lender pages, 50+ state pages, the small-loan stat page
(Idaho), fha-denial-rates-by-metro.html (Cleveland).
"""
import glob, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import Verifier, sha8  # noqa: E402

V = Verifier(ROOT)
STYLE = "font-family:'DM Mono',monospace;font-size:11.5px;color:rgba(200,168,75,.85);display:inline-block;margin:6px 0 2px"


def receipt(cid):
    cur, obj = V.claim_object(cid)
    return cur, f"⟦FRC:{cid}:{cur}:{sha8(obj)}⟧"


def line(cid, r, note="claim receipt"):
    q = urllib.parse.quote(r)
    return (f"<!--RECEIPT:{cid}--><span class=\"frc-receipt\" data-receipt=\"{r}\" style=\"{STYLE}\">{r} "
            f"<a href=\"/verify.html?r={q}\" style=\"color:inherit\">verify</a> &middot; <span style=\"color:rgba(255,255,255,.4)\">{note}: "
            f"the hash changes if this figure is ever corrected</span></span><!--/RECEIPT-->")


def strip_old(html, cid):
    return re.sub(rf"<!--RECEIPT:{re.escape(cid)}-->.*?<!--/RECEIPT-->", "", html, flags=re.S)


def add_jsonld_identifier(html, r):
    """Append a PropertyValue receipt to every Dataset JSON-LD identifier on the page."""
    def fix(m):
        try:
            d = json.loads(m.group(1))
        except Exception:
            return m.group(0)
        if d.get("@type") != "Dataset":
            return m.group(0)
        pv = {"@type": "PropertyValue", "propertyID": "FRC claim receipt", "value": r,
              "url": "https://frc-mcp.ziyetis.workers.dev/verify?r=" + urllib.parse.quote(r)}
        ident = d.get("identifier")
        if ident is None:
            ident = []
        elif not isinstance(ident, list):
            ident = [ident]
        ident = [x for x in ident if not (isinstance(x, dict) and x.get("propertyID") == "FRC claim receipt" and x.get("value", "").split(":")[1:2] == r.split(":")[1:2])]
        ident.append(pv)
        d["identifier"] = ident
        return '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False) + "</script>"
    return re.sub(r'<script type="application/ld\+json">(\{.*?\})</script>', fix, html, flags=re.S)


def patch(path, cid, anchor_re, expect_value_in_anchor=True, note="claim receipt"):
    html = open(path, encoding="utf-8").read()
    try:
        cur, r = receipt(cid)
    except Exception as e:
        return ("no-claim", f"{cid}: {e}")
    html = strip_old(html, cid)
    m = re.search(anchor_re, html, flags=re.S)
    if not m:
        return ("no-anchor", cid)
    if expect_value_in_anchor and cur.rstrip("%x") not in m.group(0):
        return ("value-mismatch", f"{cid}: page anchor lacks {cur}")
    html = html[:m.end()] + line(cid, r, note) + html[m.end():]
    html = add_jsonld_identifier(html, r)
    open(path, "w", encoding="utf-8").write(html)
    return ("ok", cid)


def main():
    out = {"ok": [], "value-mismatch": [], "no-anchor": [], "no-claim": []}
    def rec(res):
        out[res[0]].append(res[1])

    # national answer page
    rec(patch(os.path.join(ROOT, "how-often-are-fha-loans-denied.html"), "national-fha-denial-rate-2025",
              r'<div class="answer">In 2025, 22\.1% of decisioned FHA applications were denied[^<]*'))
    # top-100: the range sentence, two receipts
    p = os.path.join(ROOT, "fha-denial-rates-top-100.html")
    anchor = r'\(Amerisave Mortgage Company\)</b> &mdash; roughly a <b class="mono">44&times;</b> spread on the same federal program\.'
    rec(patch(p, "lender-flat-branch-mortgage-2025", anchor, False, "Flat Branch receipt"))
    rec(patch(p, "lender-amerisave-mortgage-2025", anchor, False, "AmeriSave receipt"))
    # lender pages
    for f in sorted(glob.glob(os.path.join(ROOT, "*-fha-denial-rate.html"))):
        slug = os.path.basename(f)[:-len("-fha-denial-rate.html")]
        if not os.path.exists(os.path.join(ROOT, "api", "lender", slug + ".json")):
            rec(("no-claim", slug)); continue
        rec(patch(f, f"lender-{slug}-2025", r"<p style=\"font-size:15px;color:#fff;font-weight:700;margin-bottom:8px;\">[^<]*FHA denial rate in 2025 was [0-9.]+%\.</p>"))
    # older-template lender pages whose file slug differs from the data slug
    ALIAS = {'rocket':'rocket-mortgage','pennymac':'pennymac-loan-services','freedom':'freedom-mortgage','guild':'guild-mortgage',
             'wells-fargo':'wells-fargo-bank','us-bank-n-a':'us-bank','crosscountry':'crosscountry-mortgage','loandepot':'loandepotcom',
             'planet-home':'planet-home-lending','mr-cooper':'nationstar-mortgage','uwm':'united-wholesale-mortgage','loan-store':'the-loan-store',
             'loanunited-com':'loanunitedcom','m-t-bank':'mandt-bank','v-i-p-mortgage':'vip-mortgage','velocio-mortgage-l-l-c':'velocio-mortgage',
             'village-capital-investment':'village-capital-and-investment'}
    for s_, a_ in ALIAS.items():
        f = os.path.join(ROOT, f"{s_}-fha-denial-rate.html")
        if os.path.exists(f):
            rec(patch(f, f"lender-{a_}-2025", r"denied <span class=\"mono\">[0-9.]+%</span> of its [\d,]+ decisioned FHA applications in 2025</b>|[A-Za-z&.,' ]+ denied [0-9.]+% of its FHA applications in 2025"))
    # state pages
    names = {}
    for f in glob.glob(os.path.join(ROOT, "api", "state", "*.json")):
        st = os.path.basename(f)[:-5]
        names[st] = json.load(open(f)).get("state_name") or None
    for f in sorted(glob.glob(os.path.join(ROOT, "fha-denial-rates-*.html"))):
        base = os.path.basename(f)[len("fha-denial-rates-"):-5]
        if base.startswith("by-") or base in ("top-100",):
            continue
        st = STATE_SLUGS.get(base)
        if not st or not os.path.exists(os.path.join(ROOT, "api", "state", st + ".json")):
            continue
        html = open(f, encoding="utf-8").read()
        cur, r = receipt(f"state-{st}-2025")
        if cur not in html:
            rec(("value-mismatch", f"state-{st}: page lacks {cur}")); continue
        rec(patch(f, f"state-{st}-2025", r"<h1>FHA denial rates in [^<]*<em>[^<]*</em>[^<]*</h1>", False, f"statewide rate {cur}, claim receipt"))
    # small-loan stat page (Idaho)
    rec(patch(os.path.join(ROOT, "stat", "is-the-smallloan-penalty-worse-in-expensive-states.html"), "small-loan-penalty-id-2025",
              r'<div class="big">4\.45x</div>'))
    # metro page: Cleveland
    rec(patch(os.path.join(ROOT, "fha-denial-rates-by-metro.html"), "metro-gap-cleveland-oh-2025",
              r'<div class="big-box"><b style="color:#C8A84B;">The spread lives inside your city:</b>[^<]*(?:<[^>]+>[^<]*)*?</div>', False, "Cleveland gap receipt"))
    print(json.dumps({k: (len(v) if k == "ok" else v) for k, v in out.items()}, indent=1))
    return out


STATE_SLUGS = {s.lower().replace(" ", "-"): c for s, c in {
    "Alabama": "al", "Alaska": "ak", "Arizona": "az", "Arkansas": "ar", "California": "ca", "Colorado": "co", "Connecticut": "ct",
    "Delaware": "de", "District of Columbia": "dc", "Florida": "fl", "Georgia": "ga", "Hawaii": "hi", "Idaho": "id", "Illinois": "il",
    "Indiana": "in", "Iowa": "ia", "Kansas": "ks", "Kentucky": "ky", "Louisiana": "la", "Maine": "me", "Maryland": "md",
    "Massachusetts": "ma", "Michigan": "mi", "Minnesota": "mn", "Mississippi": "ms", "Missouri": "mo", "Montana": "mt",
    "Nebraska": "ne", "Nevada": "nv", "New Hampshire": "nh", "New Jersey": "nj", "New Mexico": "nm", "New York": "ny",
    "North Carolina": "nc", "North Dakota": "nd", "Ohio": "oh", "Oklahoma": "ok", "Oregon": "or", "Pennsylvania": "pa",
    "Puerto Rico": "pr", "Rhode Island": "ri", "South Carolina": "sc", "South Dakota": "sd", "Tennessee": "tn", "Texas": "tx",
    "Utah": "ut", "Vermont": "vt", "Virginia": "va", "Washington": "wa", "West Virginia": "wv", "Wisconsin": "wi", "Wyoming": "wy"}.items()}

if __name__ == "__main__":
    main()
