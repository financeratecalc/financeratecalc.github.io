#!/usr/bin/env python3
"""Bring hand-built lender and state pages back to the data (found 2026-10-01 by the
receipts builder: 14 lender pages and every state page still carried figures from before
the 26 July HECM universe correction).

No generator exists for these pages in the repository, so this script replaces the
specific stale strings (headline rate, decisioned count, rank, approval rate) with the
values in api/lender/*.json and api/state/*.json, verifies the old strings are gone, and
stamps the page. Every replacement is logged to eval/stale-page-fix-2026-10-01.json.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = {"generated": "2026-10-01", "lender_pages": [], "state_pages": [], "unresolved": []}
STAMP = ('<!--STALE-FIX-2026-10-01--><p style="font-size:11.5px;color:rgba(255,255,255,.45);margin:8px 0 0">'
         'Figures on this page were re-read from the data files on 2026-10-01; an earlier version carried values '
         'from before the 26 July 2026 universe correction (reverse mortgages removed). '
         '<a href="/corrections.html" style="color:rgba(200,168,75,.8)">Corrections log</a>.</p>')


def fmt_int(n):
    return f"{n:,}"


def lender_ranks():
    rows = []
    for f in glob.glob(os.path.join(ROOT, "api", "lender", "*.json")):
        d = json.load(open(f))
        if d.get("in_top_100_by_volume"):
            rows.append((d["denial_rate_pct"], d["slug"]))
    rows.sort(key=lambda x: -x[0])
    return {slug: i + 1 for i, (_, slug) in enumerate(rows)}


def fix_lender(path, slug, ranks):
    html = open(path, encoding="utf-8").read()
    d = json.load(open(os.path.join(ROOT, "api", "lender", slug + ".json")))
    new_rate = f"{d['denial_rate_pct']:.1f}%"
    m = re.search(r"FHA denial rate in 2025 was ([0-9.]+)%", html)
    if not m:
        LOG["unresolved"].append({"page": path, "why": "no headline"}); return False
    old_rate = m.group(1) + "%"
    if old_rate == new_rate and "STALE-FIX" in html:
        return False
    changes = []
    if old_rate != new_rate:
        html, n = re.subn(rf"(?<![\d.]){re.escape(old_rate)}(?![\d])", new_rate, html); changes.append(("rate", old_rate, new_rate, n))
        old_appr = f"{100 - float(old_rate[:-1]):.1f}%"; new_appr = f"{d['approval_rate_pct']:.1f}%"
        if old_appr != new_appr:
            html, n = re.subn(rf"(?<![\d.]){re.escape(old_appr)}(?![\d])", new_appr, html); changes.append(("approval", old_appr, new_appr, n))
    mc = re.search(r"of its ([\d,]+) decisioned FHA applications", html)
    new_cnt = fmt_int(d["decisioned_applications"])
    if mc and mc.group(1) != new_cnt:
        html, n = re.subn(rf"(?<![\d,]){re.escape(mc.group(1))}(?![\d,])", new_cnt, html); changes.append(("count", mc.group(1), new_cnt, n))
    mr = re.search(r"rank <b>#(\d+)</b>", html)
    new_rank = ranks.get(slug)
    if mr and new_rank and int(mr.group(1)) != new_rank:
        html, n = re.subn(rf"rank (<b>)?#{mr.group(1)}(</b>)?", lambda x: f"rank {x.group(1) or ''}#{new_rank}{x.group(2) or ''}", html); changes.append(("rank", mr.group(1), str(new_rank), n))
    if changes:
        html = re.sub(r"updated 2026-\d\d-\d\d", "updated 2026-10-01", html, count=1)
        if "STALE-FIX" not in html:
            html = html.replace("<h2>Who pays for this?</h2>", STAMP + "\n<h2>Who pays for this?</h2>", 1)
        open(path, "w", encoding="utf-8").write(html)
        LOG["lender_pages"].append({"page": os.path.basename(path), "changes": changes})
        return True
    return False


def state_ranks():
    rows = []
    for f in glob.glob(os.path.join(ROOT, "api", "state", "*.json")):
        d = json.load(open(f)); rows.append((d["denial_rate_pct"], d["state"]))
    rows.sort(key=lambda x: -x[0])
    return {st: i + 1 for i, (_, st) in enumerate(rows)}, len(rows), min(r for r, _ in rows), max(r for r, _ in rows)


def fix_state(path, st, ranks, total, lo, hi):
    html = open(path, encoding="utf-8").read()
    d = json.load(open(os.path.join(ROOT, "api", "state", st + ".json")))
    m = re.search(r"overall FHA denial rate in 2025 was ([0-9.]+)% across ([\d,]+) decisioned applications, ranking #(\d+) of (\d+) states and territories \(national range: ([0-9.]+)% to ([0-9.]+)%\)", html)
    if not m:
        LOG["unresolved"].append({"page": os.path.basename(path), "why": "no statewide sentence"}); return False
    old_rate, old_cnt, old_rank, old_tot, old_lo, old_hi = m.groups()
    new_rate, new_cnt, new_rank = f"{d['denial_rate_pct']:.1f}", fmt_int(d["decisioned_applications"]), str(ranks[st.upper()])
    new_lo, new_hi = f"{lo:.1f}", f"{hi:.1f}"
    if (old_rate, old_cnt, old_rank, old_lo, old_hi) == (new_rate, new_cnt, new_rank, new_lo, new_hi):
        return False
    changes = []
    old_s = m.group(0)
    new_s = f"overall FHA denial rate in 2025 was {new_rate}% across {new_cnt} decisioned applications, ranking #{new_rank} of {total} states and territories (national range: {new_lo}% to {new_hi}%)"
    html, n = re.subn(re.escape(old_s), new_s, html); changes.append(("statewide sentence", old_s[:60], new_s[:60], n))
    if old_cnt != new_cnt:
        html, n = re.subn(rf"(?<![\d,]){re.escape(old_cnt)}(?![\d,])", new_cnt, html); changes.append(("count elsewhere", old_cnt, new_cnt, n))
    if old_rate != new_rate:
        # statewide rate elsewhere on the page is ambiguous with lender rates; only the sentence is replaced
        changes.append(("rate", old_rate, new_rate, "sentence only"))
    if "STALE-FIX" not in html:
        html = re.sub(r"(</h1>)", r"\1" + STAMP, html, count=1)
    open(path, "w", encoding="utf-8").write(html)
    LOG["state_pages"].append({"page": os.path.basename(path), "changes": changes})
    return True


STATE_SLUGS = {s.lower().replace(" ", "-"): c for s, c in {
    "Alabama": "al", "Alaska": "ak", "Arizona": "az", "Arkansas": "ar", "California": "ca", "Colorado": "co", "Connecticut": "ct",
    "Delaware": "de", "District of Columbia": "dc", "Florida": "fl", "Georgia": "ga", "Hawaii": "hi", "Idaho": "id", "Illinois": "il",
    "Indiana": "in", "Iowa": "ia", "Kansas": "ks", "Kentucky": "ky", "Louisiana": "la", "Maine": "me", "Maryland": "md",
    "Massachusetts": "ma", "Michigan": "mi", "Minnesota": "mn", "Mississippi": "ms", "Missouri": "mo", "Montana": "mt",
    "Nebraska": "ne", "Nevada": "nv", "New Hampshire": "nh", "New Jersey": "nj", "New Mexico": "nm", "New York": "ny",
    "North Carolina": "nc", "North Dakota": "nd", "Ohio": "oh", "Oklahoma": "ok", "Oregon": "or", "Pennsylvania": "pa",
    "Puerto Rico": "pr", "Rhode Island": "ri", "South Carolina": "sc", "South Dakota": "sd", "Tennessee": "tn", "Texas": "tx",
    "Utah": "ut", "Vermont": "vt", "Virginia": "va", "Washington": "wa", "West Virginia": "wv", "Wisconsin": "wi", "Wyoming": "wy"}.items()}


ALIAS = {'rocket':'rocket-mortgage','pennymac':'pennymac-loan-services','freedom':'freedom-mortgage','guild':'guild-mortgage',
         'wells-fargo':'wells-fargo-bank','us-bank-n-a':'us-bank','crosscountry':'crosscountry-mortgage','loandepot':'loandepotcom',
         'planet-home':'planet-home-lending','mr-cooper':'nationstar-mortgage','uwm':'united-wholesale-mortgage','loan-store':'the-loan-store',
         'loanunited-com':'loanunitedcom','m-t-bank':'mandt-bank','v-i-p-mortgage':'vip-mortgage','velocio-mortgage-l-l-c':'velocio-mortgage',
         'village-capital-investment':'village-capital-and-investment'}


def fix_alias_page(path, api_slug, ranks):
    """Older-template pages: og:title carries the stale rate; the injected answer block carries the current one."""
    html = open(path, encoding="utf-8").read()
    d = json.load(open(os.path.join(ROOT, "api", "lender", api_slug + ".json")))
    new_rate = f"{d['denial_rate_pct']:.1f}%"
    m = re.search(r'og:title" content="[^"]*?\(2025\): ([0-9.]+)%', html)
    if not m:
        LOG["unresolved"].append({"page": os.path.basename(path), "why": "no og:title rate"}); return False
    old_rate = m.group(1) + "%"
    changes = []
    if old_rate != new_rate:
        html, n = re.subn(rf"(?<![\d.]){re.escape(old_rate)}(?![\d])", new_rate, html); changes.append(("rate", old_rate, new_rate, n))
    mr = re.search(r"ranked #(\d+) of the 100", html)
    n_total = len(ranks)
    new_rank = (n_total + 1 - ranks[api_slug]) if api_slug in ranks else None  # these pages rank ascending: lowest denial = #1
    if mr and new_rank and int(mr.group(1)) != new_rank:
        html, n = re.subn(rf"#{mr.group(1)} of the 100", f"#{new_rank} of the 100", html); changes.append(("rank", mr.group(1), str(new_rank), n))
    if changes:
        html = re.sub(r"updated 2026-\d\d-\d\d", "updated 2026-10-01", html, count=1)
        if "STALE-FIX" not in html:
            html = html.replace("</h1>", "</h1>" + STAMP, 1)
        open(path, "w", encoding="utf-8").write(html)
        LOG["lender_pages"].append({"page": os.path.basename(path), "changes": changes}); return True
    return False


def main():
    ranks = lender_ranks()
    for s, a in ALIAS.items():
        f = os.path.join(ROOT, f"{s}-fha-denial-rate.html")
        if os.path.exists(f) and os.path.exists(os.path.join(ROOT, "api", "lender", a + ".json")):
            fix_alias_page(f, a, ranks)
    for f in sorted(glob.glob(os.path.join(ROOT, "*-fha-denial-rate.html"))):
        slug = os.path.basename(f)[:-len("-fha-denial-rate.html")]
        if os.path.exists(os.path.join(ROOT, "api", "lender", slug + ".json")):
            fix_lender(f, slug, ranks)
    sr, total, lo, hi = state_ranks()
    for f in sorted(glob.glob(os.path.join(ROOT, "fha-denial-rates-*.html"))):
        base = os.path.basename(f)[len("fha-denial-rates-"):-5]
        st = STATE_SLUGS.get(base)
        if st and os.path.exists(os.path.join(ROOT, "api", "state", st + ".json")):
            fix_state(f, st, sr, total, lo, hi)
    json.dump(LOG, open(os.path.join(ROOT, "eval", "stale-page-fix-2026-10-01.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"lender_pages_fixed": len(LOG["lender_pages"]), "state_pages_fixed": len(LOG["state_pages"]), "unresolved": LOG["unresolved"]}, indent=1))


if __name__ == "__main__":
    main()
