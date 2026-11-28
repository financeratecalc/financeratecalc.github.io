#!/usr/bin/env python3
"""A limited watch: do errors already recorded in the corrections log reappear on the published site?

    python3 scripts/watch_recorded_errors.py            # scan, write transparency/recorded-errors-watch.json and watch.html
    python3 scripts/watch_recorded_errors.py --check    # scan and print; write nothing (exit 0 either way)

What it is: five families of wording that this site has already found and removed, each tied to the corrections-log
entry that recorded it, searched for in every published file of the kinds listed in SCAN. What it is not: an audit of the
site. It does not check that a figure is right, compare with outside sources, or look for errors nobody has recorded.

It only reports. It never changes a page. Each finding keeps the address, the matching text, the corrections-log entry
and the time it was first seen; a finding that disappears is kept with the time it was last seen.

Files that record an error in order to correct it (the corrections log and its feed) and pages that are retirement
notices quoting what they retired are not scanned, and are listed as such in the output.
"""
import datetime as dt
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com"
OUT_JSON = os.path.join(ROOT, "transparency", "recorded-errors-watch.json")
OUT_HTML = os.path.join(ROOT, "watch.html")

FAMILIES = [
    {"id": "personal-prediction", "name": "Wording that predicts one application or picks a lender for a reader",
     "entries": ["2026-11-27-fits-your-file", "2026-10-31-phrasing", "2026-11-27-stories-and-prediction-pages"],
     "patterns": [r"\bfits your file\b", r"\byour odds\b", r"\bwill deny you\b", r"\byou will be approved\b",
                  r"\bestimate your odds\b", r"\bwhich lender (?:type )?fits you\b", r"\bsee if you qualify\b",
                  r"\bthe same (?:FHA )?application faces\b", r"\bapproval odds\b", r"\bPre-Flight Check\b",
                  r"\b(?:files|profiles) like yours\b", r"\bbest lender match\b", r"\byour (?:two|second) doors?\b"]},
    {"id": "sales", "name": "Affiliate, commission and lead-generation wording",
     "entries": ["2026-11-16-partner-links"],
     "patterns": [r"\bmay earn a commission\b", r"\bcommission may be earned\b",
                  r'rel="[^"]*\bsponsored\b', r"(?<!no )(?<!not )\baffiliate links? (?:help|support|on this page)\b"]},
    {"id": "retired-products", "name": "Products withdrawn in September 2026",
     "entries": ["2026-10-20-fresh-eyes"],
     "patterns": [r"\bTalk to Zai\b", r"\bAsk Zai\b", r"\bZai Pro\b", r"\bPro \$49/mo\b", r"\bVerdict Case File\b",
                  r'href="/frc-banker-ai\.html"']},
    {"id": "old-figures", "name": "Figures and rules already corrected",
     "entries": ["2026-11-15-credit-score-minimums", "2026-11-27-fits-your-file"],
     "patterns": [r"\b320 (?:metros|metro areas|metropolitan areas|MSAs)\b", r"\bminimum 620 for FHA\b",
                  r"\b620 (?:minimum )?for FHA\b", r"\bFHA (?:requires|minimum(?: credit score)?(?: is| of)?) 620\b"]},
    {"id": "invented-cases", "name": "Stories or cases presented as real without a source",
     "entries": ["2026-11-15-invented-case-studies", "2026-11-27-stories-and-prediction-pages"],
     "patterns": [r"\bReal Case Study\b", r"\bReal Approval Story\b", r"\bReal Mortgage (?:Story|Redemption)\b",
                  r"\bapproved (?:elsewhere )?in four days\b", r"\bSubmitted to FRC Rejection Database\b"]},
]
SCAN = {".html": "HTML pages (including JSON-LD inside them)", ".txt": "text files for machines (llms.txt and others)",
        ".md": "Markdown pages", ".json": "machine-readable files (API, claims, data)"}
SKIP_DIRS = {".git", "node_modules", "scripts", ".github", "eval", "evals", "readers", "experiments", "fixtures",
             "rl-env", "frc_denial_ai_fidelity.egg-info", "_data", "packages", "worker", "tools", "samples"}
SKIP_DIRS_WHY = "source code, test fixtures, and recorded answers of AI systems kept as evidence (eval/, readers/): they quote errors on purpose"
RECORDS = {"corrections.html", "corrections.json", "watch.html", "transparency/recorded-errors-watch.json"}
# Files that name a recorded error in order to record it, with the reason. Matches in them are listed as excepted, not open.
EXCEPT = {"terms.html": "the terms list retired products by name, as a record",
          "refund.html": "the refund policy names retired products so their buyers can claim",
          "affiliate-disclosure.html": "the disclosure page records the links that were removed",
          "pricing.html": "the pricing page names retired products in its record of what was withdrawn",
          "license.html": "a dated publication record keeps the count it had on its date (see the corrections log)"}
# A match preceded by a negation in the same sentence, or set in quotation marks, is a statement about the wording, not the wording.
NEG = re.compile(r"\b(?:not|no|nobody|never|cannot|can't|isn't|doesn't|does not|nor|neither|without)\b[^.!?]{0,70}$", re.I)
QUOTE_OPEN = "\u201c\"\u2018'&ldquo;&quot;"
RETIRED = re.compile(r"<title>[^<]*(?:Retired|page retired)[^<]*</title>|<!-- rulecheck:ignore", re.I)


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def scan():
    rx = [(f, re.compile(p, re.I)) for f in FAMILIES for p in f["patterns"]]
    counts, hits, skipped_records, skipped_retired = {k: 0 for k in SCAN}, [], [], 0
    for d, dirs, files in os.walk(ROOT):
        rel_d = os.path.relpath(d, ROOT)
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".") or x == ".well-known"]
        for fn in files:
            ext = os.path.splitext(fn)[1]
            if ext not in SCAN:
                continue
            rel = os.path.normpath(os.path.join(rel_d, fn)).replace(os.sep, "/")
            if rel in RECORDS:
                skipped_records.append(rel); continue
            try:
                text = open(os.path.join(d, fn), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if ext == ".html" and RETIRED.search(text):
                skipped_retired += 1; continue
            counts[ext] += 1
            for fam, r in rx:
                for m in r.finditer(text):
                    a, b = max(0, m.start() - 90), min(len(text), m.end() + 90)
                    ctx = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text[a:b]))).strip()
                    before = html.unescape(re.sub(r"<[^>]+>", " ", text[max(0, m.start() - 160):m.start()]))
                    after = html.unescape(text[m.end():m.end() + 8])
                    h = {"family": fam["id"], "url": f"{BASE}/{rel}", "match": m.group(0), "pattern": r.pattern, "context": ctx[:220]}
                    if rel in EXCEPT:
                        h["excepted"] = EXCEPT[rel]
                    elif before.rstrip()[-1:] in "\u201c\u2018" and after[:1] in "\u201d\u2019":   # typographic quotes only: a quotation in prose, not a string in code
                        h["excepted"] = "quoted: the page writes about the wording"
                    elif NEG.search(before.split("\n")[-1] if "\n" in before else before):
                        h["excepted"] = "negated in the same sentence"
                    hits.append(h)
    return counts, hits, sorted(skipped_records), skipped_retired


def merge(hits, prev, t):
    stamp = t.strftime("%Y-%m-%dT%H:%M:%SZ")
    old = {(h["family"], h["url"], h["match"].lower()): h for h in (prev or {}).get("findings", [])}
    out, seen = [], set()
    exc = [h for h in hits if h.get("excepted")]
    hits = [h for h in hits if not h.get("excepted")]
    merge.excepted = exc
    for h in hits:
        k = (h["family"], h["url"], h["match"].lower())
        if k in seen:
            continue
        seen.add(k)
        o = old.get(k, {})
        out.append({**h, "first_seen": o.get("first_seen", stamp), "last_seen": stamp, "open": True})
    for k, o in old.items():
        if k not in seen:
            out.append({**o, "open": False})
    return out


def page(doc):
    E = html.escape
    open_n = sum(1 for f in doc["findings"] if f["open"])
    open_f = [f for f in doc["findings"] if f["open"]]
    pages = {f["url"] for f in open_f}
    fams = {f["family"] for f in open_f}
    user_pages = {u for u in pages if u.endswith((".html", "/"))}
    head = ("Of the five error families recorded in our corrections log, none was found again in the last check." if open_n == 0
            else f"{open_n} matches of recorded wording, on {len(pages)} files, in {len(fams)} of the five families.")
    fam_rows = "".join(
        f'<tr><td><b>{E(f["name"])}</b><br><span class="s">{" · ".join(E(p) for p in f["patterns"])}</span></td>'
        f'<td>{" ".join(f"<a href=\"/corrections.html#{E(e)}\">{E(e[:10])}</a>" for e in f["entries"])}</td>'
        f'<td class="n">{doc["by_family"][f["id"]]}</td></tr>' for f in FAMILIES)
    finds = [f for f in doc["findings"] if f["open"]] + [f for f in doc["findings"] if not f["open"]]
    find_rows = "".join(
        f'<tr><td>{"open" if f["open"] else "gone"}</td><td><a href="{E(f["url"])}">{E(f["url"].replace(BASE + "/", ""))}</a><br><span class="s">{E(f["context"])}</span></td>'
        f'<td><code>{E(f["match"])}</code></td><td class="s">{E(f["first_seen"])}<br>{E(f["last_seen"])}</td></tr>' for f in finds) \
        or '<tr><td colspan="4">No finding has been recorded since the watch began.</td></tr>'
    scanned = " · ".join(f'{n:,} {E(SCAN[k])}' for k, n in doc["scanned"].items())
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Recorded Errors Watch | FinanceRateCalc</title>
<meta name="description" content="A limited daily check of whether errors already recorded in this site's corrections log have come back. It is not an audit of the site.">
<link rel="canonical" href="{BASE}/watch.html">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,900&family=DM+Sans:wght@400;600&family=DM+Mono&display=swap" rel="stylesheet">
<style>:root{{--bg:#08090c;--panel:#0e1016;--ink:#ece8dc;--soft:#a39f93;--dim:#6f6c63;--rule:rgba(255,255,255,.11);--gold:#c8a84b;--ok:#6fcf97;--void:#e06c6c}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:'DM Sans',system-ui,sans-serif;font-size:16.5px;line-height:1.6}}a{{color:var(--gold)}}
.wrap{{max-width:960px;margin:0 auto;padding:34px 20px 70px}}h1{{font-family:'Fraunces',Georgia,serif;font-size:clamp(28px,4vw,42px);line-height:1.1;margin:0 0 14px;max-width:24ch}}
h2{{font-family:'Fraunces',Georgia,serif;font-size:22px;margin:34px 0 10px}}.k{{color:var(--dim);font-size:14px}}
.box{{border:1px solid var(--rule);border-left:4px solid {"var(--ok)" if open_n == 0 else "var(--void)"};background:var(--panel);padding:16px 20px;margin:18px 0}}
.box p{{margin:4px 0}}.box b{{display:inline-block;min-width:9.5em;color:var(--soft);font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:15px}}td,th{{text-align:left;vertical-align:top;padding:9px 10px 9px 0;border-bottom:1px solid var(--rule)}}th{{color:var(--dim);font-weight:600;font-size:13px}}
.n{{text-align:right;font-variant-numeric:tabular-nums}}.s{{color:var(--dim);font-size:13px;overflow-wrap:anywhere}}code{{font-family:'DM Mono',monospace;font-size:13.5px}}
@media(max-width:640px){{.box b{{display:block}}td,th{{padding-right:6px}}}}</style></head>
<body><div class="wrap">
<p class="k"><a href="/">FinanceRateCalc</a> · recorded errors watch</p>
<h1>{E(head)}</h1>
<div class="box">
<p><b>Last check</b>{E(doc["checked_at"].replace("T", " ").replace("Z", " UTC"))}</p>
<p><b>Scanned</b>{scanned}</p>
<p><b>Checks</b>{len(FAMILIES)} error families, {sum(len(f["patterns"]) for f in FAMILIES)} patterns</p>
<p><b>Found again</b>{open_n} matches on {len(pages)} files: {len(user_pages)} pages for readers, {len(pages) - len(user_pages)} machine-readable or internal files. Many matches are one template repeated across pages.</p>
<p><b>Not covered</b>whether any figure is right; comparison with outside sources; anything about Bitcoin or other parties&rsquo; records; errors nobody has recorded yet</p>
</div>
<p>This watch is limited on purpose. Each family below is wording this site has already found on its own pages, recorded in the <a href="/corrections.html">corrections log</a> and removed. Once a day every published file of the kinds listed is searched for it again. The watch only reports: it does not change any page. A finding stays on this page with the time it was first seen, and when it is fixed it stays as &ldquo;gone&rdquo; with the time it was last seen.</p>
<p class="s">Retirement notices are skipped because they quote what they retired; a notice replaces the whole page, so skipping it cannot hide a product that is still offered on that page.</p>
<p class="s">Not searched: {len(doc["not_scanned"]["records"])} files that record the errors in order to correct them ({E(", ".join(doc["not_scanned"]["records"]))}); {doc["not_scanned"]["retirement_notices"]:,} retirement notices, which quote what they retired; and {E(SKIP_DIRS_WHY)}.</p>
<p class="s">Matches set aside rather than reported: {len(doc["excepted"])} (a negated sentence such as &ldquo;nobody can tell you your odds&rdquo;, a quotation, or a page that records the error by name). Each is listed with its reason in the machine-readable file.</p>
<h2>The five families</h2>
<table><thead><tr><th>Family and the patterns searched</th><th>Recorded in</th><th class="n">Found now</th></tr></thead><tbody>{fam_rows}</tbody></table>
<h2>Findings</h2>
<table><thead><tr><th>State</th><th>Where</th><th>Text</th><th>First / last seen</th></tr></thead><tbody>{find_rows}</tbody></table>
<p class="s" style="margin-top:22px">Machine-readable: <a href="/transparency/recorded-errors-watch.json">transparency/recorded-errors-watch.json</a> · the watch: <a href="https://github.com/financeratecalc/financeratecalc.github.io/blob/main/scripts/watch_recorded_errors.py">scripts/watch_recorded_errors.py</a></p>
</div></body></html>
'''


def main():
    t = now()
    counts, hits, recs, retired = scan()
    prev = json.load(open(OUT_JSON)) if os.path.exists(OUT_JSON) else None
    findings = merge(hits, prev, t)
    doc = {"what": "A limited watch: whether wording already recorded as an error in the corrections log appears again on the published site. Not an audit; it only reports.",
           "checked_at": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "scanned": counts,
           "not_scanned": {"records": recs, "retirement_notices": retired, "directories": sorted(SKIP_DIRS), "why": SKIP_DIRS_WHY},
           "families": FAMILIES, "by_family": {f["id"]: sum(1 for h in findings if h["open"] and h["family"] == f["id"]) for f in FAMILIES},
           "open": sum(1 for h in findings if h["open"]), "findings": findings,
           "excepted": [{k: h[k] for k in ("family", "url", "match", "excepted")} for h in merge.excepted],
           "not_covered": ["whether any figure is right", "comparison with outside sources", "Bitcoin or other parties' records", "errors nobody has recorded yet"]}
    for h in [x for x in findings if x["open"]][:40]:
        print("FOUND", h["family"], h["url"], "|", h["match"], "|", h["context"][:140])
    print(f"recorded-errors watch: {doc['open']} open, scanned {counts}, retirement notices skipped {retired}")
    if "--check" in sys.argv:
        return 0
    json.dump(doc, open(OUT_JSON, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(OUT_JSON, "a").write("\n")
    open(OUT_HTML, "w", encoding="utf-8").write(page(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
