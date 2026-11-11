#!/usr/bin/env python3
"""Level-2 receipts: attested restatement of an official publication's figures.

    python3 scripts/official_restate.py hud-fhaprod 2026-08 [--pdf /path/to/file.pdf]

Nothing is computed here. An official document (today: HUD's monthly "FHA Single Family Production Report") is
downloaded, hashed, its text layer read, and a fixed set of labelled cells is copied out exactly as printed, each with
its table, row and column label, the document's own exclusions (HECM), its period and its publication month. The
output, data/official/<source>-<period>.json, is the only thing the claim builders read; a cell that cannot be located
unambiguously is not written, and the run fails loudly.

What a Level-2 receipt means: "this figure, with this definition and period, appears in this document with this
SHA-256". It does not mean FinanceRateCalc computed or endorses the figure; it means an AI system restating it can be
checked against the source without us. The use contract says what the figure is not (an HMDA origination, an application
count, a denial figure).
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SOURCES = {
    "hud-fhaprod": {
        "title": "Federal Housing Administration Single Family Production Report",
        "publisher": "U.S. Department of Housing and Urban Development, Office of Housing, Office of Risk Management, Reporting and Analysis Division",
        "landing": "https://www.hud.gov/hud-partners/fha-production-report",   # lists the current edition and the archive
        "url_patterns": ["https://www.hud.gov/sites/default/files/Housing/documents/FHAProd_{MON}{Y}.pdf",
                         "https://www.hud.gov/sites/default/files/Housing/documents/FHAProd_{Mon}{Y}.pdf",
                         "https://www.hud.gov/sites/default/files/Housing/documents/FHAProd-{Mon}{Y}.pdf",
                         "https://www.hud.gov/sites/dfiles/Housing/documents/FHAProd-{Mon}{Y}.pdf",
                         "https://www.hud.gov/sites/dfiles/Housing/documents/FHAProd_{MON}{Y}.pdf"],
        "exclusions": "Does not include Home Equity Conversion Mortgages (HECM) (table note)",
        # id -> (table, row label regex, column index among the numbers on that row, unit, kind, description)
        "cells": {
            "endorsements-count":        ("Table 1", r"^Endorsements\s+([\d,()]+)\s+([\d,()]+)", 0, "loans", "month", "FHA single-family loans endorsed for insurance in the month"),
            "endorsements-balance-musd": ("Table 1", r"^Endorsements\s+([\d,()]+)\s+([\d,()]+)", 1, "USD millions", "month", "unpaid principal balance of loans endorsed in the month"),
            "insurance-in-force-end":    ("Table 1", r"^Insurance in Force \(Ending\)\S*\s+([\d,()]+)\s+([\d,()]+)", 0, "loans", "month-end", "single-family loans in force at month end"),
            "total-endorsement-count":   ("Table 4", r"^Total Endorsement Count\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", 0, "loans", "month", "FHA single-family endorsements in the month, as totalled in Table 4 (this row also restates the prior month, so revisions of the headline count are tracked here)"),
            "endorsements-fytd":         ("Table 4", r"^Total Endorsement Count\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", 2, "loans", "fiscal-year-to-date", "FHA single-family endorsements, fiscal year to date"),
            "purchase-share-pct":        ("Table 4", r"^Purchase \(%\)\s+([\d.]+)\s+([\d.]+)", 0, "percent of endorsements", "month", "share of the month's endorsements that were purchase loans"),
            "refinance-share-pct":       ("Table 4", r"^Refinance \(%\)\s+([\d.]+)\s+([\d.]+)", 0, "percent of endorsements", "month", "share of the month's endorsements that were refinances"),
            "purchase-count":            ("Table 4", r"^Purchase Loan Count\s+([\d,]+)\s+([\d,]+)", 0, "loans", "month", "purchase loans endorsed in the month"),
            "refinance-count":           ("Table 4", r"^Refinance Loan Count\s+([\d,]+)\s+([\d,]+)", 0, "loans", "month", "refinance loans endorsed in the month"),
            "first-time-homebuyer-pct":  ("Table 4", r"^First-Time Homebuyer \(%\)\s+([\d.]+)\s+([\d.]+)", 0, "percent of purchase endorsements", "month", "share of the month's purchase endorsements to first-time homebuyers"),
            "fha-streamline-pct":        ("Table 4", r"^FHA Streamline \(%\)\s+([\d.]+)\s+([\d.]+)", 0, "percent of refinance endorsements", "month", "share of the month's refinance endorsements that were FHA Streamline refinances"),
        },
    },
}
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MON_FULL = ["Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec"]
FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FinanceRateCalc official-restate/1.0; +https://financeratecalc.com)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def discover(src, y, m):
    """Read the publisher's index page and return PDF links whose name carries the month and year, most specific first."""
    try:
        html_ = _get(src["landing"]).decode("utf-8", "ignore")
    except Exception as e:
        print("landing page not readable:", str(e)[:80]); return []
    links = re.findall(r'href="([^"]*FHAProd[^"]*\.pdf)"', html_, re.I)
    toks = {MON[m - 1].lower(), MON_FULL[m - 1].lower(), FULL[m - 1].lower()}
    out = []
    for h in links:
        name = h.rsplit("/", 1)[-1].lower()
        if str(y) in name and any(t in name for t in toks):
            out.append(h if h.startswith("http") else "https://www.hud.gov" + h)
    return list(dict.fromkeys(out))


def fetch(src, y, m, dest):
    tried = []
    for url in discover(src, y, m):
        tried.append(url)
        try:
            data = _get(url)
            if data[:4] == b"%PDF":
                open(dest, "wb").write(data); print("found via index page:", url); return url
        except Exception as e:
            print("fetch failed:", url, str(e)[:80])
    for pat in src["url_patterns"]:
        for mon in dict.fromkeys([MON[m - 1].title(), MON_FULL[m - 1], MON_FULL[m - 1].upper(), FULL[m - 1], FULL[m - 1].upper(), MON[m - 1]]):
            url = pat.format(MON=MON[m - 1], Mon=mon, Y=y)
            if url in tried:
                continue
            tried.append(url)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; FinanceRateCalc official-restate/1.0; +https://financeratecalc.com)"}), timeout=120) as r:
                    data = r.read()
                if data[:4] == b"%PDF":
                    open(dest, "wb").write(data)
                    return url
                print("not a PDF:", url, data[:60])
            except Exception as e:
                print("fetch failed:", url, str(e)[:80])
                # second attempt with curl (some .gov hosts refuse Python's urllib but accept a browser-like client)
                try:
                    subprocess.run(["curl", "-sL", "--max-time", "120", "-A", "Mozilla/5.0 (X11; Linux x86_64) FinanceRateCalc/1.0", "-o", dest, url], check=True)
                    if open(dest, "rb").read(4) == b"%PDF":
                        return url
                    print("curl got non-PDF:", url, open(dest, "rb").read(60))
                except Exception as e2:
                    print("curl failed:", url, str(e2)[:80])
                continue
    sys.exit("no PDF found; tried: " + ", ".join(tried))


def text_of(pdf):
    try:
        return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    except Exception:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(pdf).pages)


def table_lines(lines, table):
    """Candidate line ranges for `table` (e.g. 'Table 4'): from each occurrence of its heading to the next table heading.
    The text layer sometimes breaks words ('Tabl e 4. Si ngle'), so headings are matched with spaces removed.
    Falls back to all lines when no heading is found."""
    n = int(table.split()[-1])
    heads = [(i, int(m.group(1))) for i, ln in enumerate(lines) for m in [re.match(r"^Table(\d+)\.", ln.replace(" ", ""))] if m]
    starts = [i for i, k in heads if k == n]
    if not starts:
        return [lines]
    segs = []
    for a in starts:   # a table of contents lists every heading on consecutive lines; the real table is the occurrence with a body
        later = [i for i, k in heads if i > a and k != n]
        segs.append(lines[a:(later[0] if later else len(lines))])
    return segs


def num(s):
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    v = float(s.strip("()").replace(",", ""))
    v = int(v) if v.is_integer() and "." not in s else v
    return -v if neg else v


def main():
    source, period = sys.argv[1], sys.argv[2]
    src = SOURCES[source]
    y, m = int(period[:4]), int(period[5:7])
    a = sys.argv[3:]
    pdf = a[a.index("--pdf") + 1] if "--pdf" in a else None
    url = None
    if not pdf:
        os.makedirs(os.path.join(ROOT, "data", "official", "cache"), exist_ok=True)
        pdf = os.path.join(ROOT, "data", "official", "cache", f"{source}-{period}.pdf")
        url = fetch(src, y, m, pdf)
    sha = sha256(pdf)
    text = text_of(pdf)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    month_label = f"{MON[m - 1].title()} {y}"
    fy = y if m < 10 else y + 1   # federal fiscal year starts 1 October
    figures = {}
    prev_period = f"{y if m > 1 else y - 1}-{(m - 1) if m > 1 else 12:02d}"
    prev_path = os.path.join(ROOT, "data", "official", f"{source}-{prev_period}.json")
    prev = json.load(open(prev_path, encoding="utf-8")) if os.path.exists(prev_path) else None
    revisions = []
    for fid, (table, rx, col, unit, kind, desc) in src["cells"].items():
        cands = [[mt for ln in seg for mt in [re.match(rx, ln)] if mt] for seg in table_lines(lines, table)]
        good = [h for h in cands if len(h) == 1]
        if len(good) != 1 and not (len(good) > 1 and len({h[0].group(0) for h in good}) == 1):
            ctx = " | ".join(h.group(0)[:60] for hs in cands for h in hs[:3])
            sys.exit(f"cell {fid}: expected exactly one matching line in exactly one {table} section; sections {len(cands)}, hits per section {[len(h) for h in cands]} ({rx}) :: {ctx}")
        hits = good[0]
        val = num(hits[0].group(col + 1))
        period_label = {"month": month_label, "month-end": f"end of {month_label}", "fiscal-year-to-date": f"FY {fy} to date (1 Oct {fy - 1} – {month_label})"}[kind]
        figures[fid] = {"value": val, "display": hits[0].group(col + 1).strip(), "unit": unit, "period_kind": kind, "period": period_label,
                        "table": table, "row_label": hits[0].group(0).split(hits[0].group(1))[0].strip(), "column": ["first", "second", "third"][col] + " numeric column",
                        "line_as_printed": hits[0].group(0), "description": desc, "revision": "as first printed; no later edition checked yet"}
        # Table 4 prints the prior month beside the current one: the second numeric column restates last month's figure.
        # Compared with last month's own edition, it shows whether HUD revised it - read, not computed.
        if table == "Table 4" and kind == "month" and col == 0 and hits[0].lastindex and hits[0].lastindex >= 2:
            restated = num(hits[0].group(2))
            figures[fid]["prior_month_as_restated_here"] = restated
            if prev and fid in prev["figures"]:
                orig = prev["figures"][fid]["value"]
                rev = {"figure": fid, "period": prev["figures"][fid]["period"], "first_printed": orig, "restated_in": f"{month_label} report", "restated_value": restated,
                       "revised": abs(float(orig) - float(restated)) > 1e-9}
                revisions.append(rev)
    out = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "source_id": source, "period": period,
           "document": {"title": src["title"], "publisher": src["publisher"], "edition": f"{month_label} report", "url": url, "sha256": sha,
                        "pages": None, "exclusions": src["exclusions"], "retrieved_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
           "level": "2 — attested restatement of an official publication; not computed by FinanceRateCalc",
           "not_comparable_with": ["HMDA originations or applications (an endorsement is a loan insured by FHA after closing; counts and timing differ from HMDA action_taken 1)",
                                   "any denial figure on this site"],
           "figures": figures, "prior_edition_check": {"edition_compared": prev["document"]["edition"] if prev else None, "revisions": revisions,
                                                      "note": "Table 4 restates the prior month; a difference from the prior edition's own figure is a source revision, recorded here and, for the affected receipt, written into that edition's file as revised_in/revised_to."}}
    os.makedirs(os.path.join(ROOT, "data", "official"), exist_ok=True)
    p = os.path.join(ROOT, "data", "official", f"{source}-{period}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if prev:
        changed = False
        for rev in revisions:
            pf = prev["figures"][rev["figure"]]
            pf["revision"] = (f"revised in the {month_label} report to {rev['restated_value']}" if rev["revised"] else f"unchanged in the {month_label} report")
            if rev["revised"]:
                pf["revised_in"] = f"{month_label} report"; pf["revised_to"] = rev["restated_value"]
            changed = True
        if changed:
            json.dump(prev, open(prev_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(f"prior edition {prev_period}: {sum(1 for r in revisions if r['revised'])} revised, {sum(1 for r in revisions if not r['revised'])} unchanged -> revision fields written")
    ip = os.path.join(ROOT, "data", "official", "index.json")
    idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else {"purpose": "index of restated official editions; latest per source", "editions": {}, "latest": {}}
    idx["editions"].setdefault(source, [])
    if period not in idx["editions"][source]:
        idx["editions"][source].append(period); idx["editions"][source].sort()
    idx["latest"][source] = idx["editions"][source][-1]
    idx["generated"] = out["generated"]
    json.dump(idx, open(ip, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{source} {period}: {len(figures)} figures restated from {url or pdf} (sha256 {sha[:12]}…) -> {os.path.relpath(p, ROOT)}")
    for k, f in figures.items():
        print(f"  {k}: {f['display']} {f['unit']} [{f['period']}]")


if __name__ == "__main__":
    main()
