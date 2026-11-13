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
    "ginnie-iss": {
        "kind": "month_table",
        "title": "Ginnie Mae Monthly Issuance Report (Issuance Summary)",
        "publisher": "Government National Mortgage Association (Ginnie Mae), U.S. Department of Housing and Urban Development",
        # the publisher moved these files in 2026; the first two locations are where the 2026 editions were found, the last is the old one
        "url_patterns": ["https://www.ginniemae.gov/s3/sites/default/files/{PUB1}/{Mon}{YY}_ISS.pdf",   # e.g. 2026-10/Sep26_ISS.pdf: filed under the month of publication
                         "https://www.ginniemae.gov/s3/sites/default/files/{PUB2}/{Mon}{YY}_ISS.pdf",
                         "https://www.ginniemae.gov/s3/sites/default/files/{PUB0}/{Mon}{YY}_ISS.pdf",
                         "https://www.ginniemae.gov/s3/sites/default/files/assets/redirects/{Mon}{YY}_ISS.pdf",
                         "https://www.ginniemae.gov/s3/sites/default/files/assets/pdfs/{Mon}{YY}_ISS.pdf",
                         "https://www.ginniemae.gov/data_and_reports/reporting/MonthlyIssuanceReports/{Mon}{YY}_ISS.pdf"],
        "exclusions": "Mortgage-backed securities issued under Ginnie Mae I and Ginnie Mae II programs, in USD millions; a securities-issuance figure, not a count of loans",
        "table": "Table 1: Monthly Issuance Summary (In Millions)",
        "ncols": 18,
        # id -> (0-based index among the 18 numbers on a month's row, column as described, description)
        "cells": {
            "total-issuance-musd":     (17, "last numeric column (Total Ginnie Mae I and II)", "Ginnie Mae mortgage-backed securities issued in the month, Ginnie Mae I and II together"),
            "ginnie-ii-issuance-musd": (16, "seventeenth numeric column (Ginnie Mae II total)", "Ginnie Mae II mortgage-backed securities issued in the month"),
            "ginnie-i-issuance-musd":  (8, "ninth numeric column (Ginnie Mae I single-family and multifamily total)", "Ginnie Mae I mortgage-backed securities issued in the month"),
        },
        "not_comparable_with": ["FHA endorsements (HUD's production report counts loans insured; this is the dollar amount of securities issued, and the pools also hold VA, USDA and PIH loans)",
                                "HMDA originations or applications", "any denial figure on this site"],
        "does_not_establish": ["a number of loans, originations or applications (it is a dollar amount of securities issued)", "FHA-only activity (Ginnie Mae pools also hold VA, USDA and PIH loans)",
                               "any denial or approval rate", "any lender-level or issuer-level figure", "that the figure has not been revised in a later edition (check the latest report)"],
        "quoting_rule": "Keep the publisher, the edition, the month and the unit (USD millions of securities issued) with the figure. It is a securities-issuance amount: do not present it as a loan count, an FHA-only figure, an origination total or a denial figure. If revision_status says a later edition revised it, say so.",
    },
    "sba-7a504": {
        "kind": "xlsx_months",
        "title": "SBA 7(a) and 504 Monthly and Yearly Activity Report",
        "publisher": "U.S. Small Business Administration, Office of Capital Access",
        "url": "https://sba-llms-prd-public.sbalenderportal.com/SBA-Monthly-MonthlyYearlyActivity7a504.xlsx",
        "landing": "https://data.sba.gov/dataset/7a-504-activity-reports-current-month",
        "table": "sheet 'Monthly'",
        # id -> (block, 0-based column in the sheet, unit, description); block columns: 7(a) = A-F, 504 = H-L
        "cells": {
            "7a-approved-loans":  ("7(a)", 3, "loans", "7(a) loans approved in the month"),
            "7a-approved-usd":    ("7(a)", 4, "USD", "dollar amount of 7(a) loans approved in the month"),
            "504-approved-loans": ("504", 10, "loans", "504 loans approved in the month"),
            "504-approved-usd":   ("504", 11, "USD", "dollar amount of 504 loans approved in the month"),
        },
        "not_comparable_with": ["loans disbursed or outstanding (an approval is not a disbursement)", "HMDA mortgage applications or originations", "any figure for another SBA program (microloans, disaster loans)"],
        "does_not_establish": ["the number or amount of loans actually disbursed (these are approvals)", "any lender-level figure", "any applicant's chance of approval",
                               "that the figure has not changed since this edition (the publisher overwrites the file each month; check the latest edition and the revision ledger)"],
        "quoting_rule": "Keep the program (7(a) or 504), the approval month, the word 'approved' and the edition's as-of date with the figure. It is an approval count or amount as recorded on that date: do not present it as loans disbursed, as a lender figure, or as anyone's chance of approval. The publisher replaces the file monthly and earlier months can change; if revision_status says a later edition printed a different value, say so.",
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
    if not src.get("landing"):
        return []
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
            url = pat.format(MON=MON[m - 1], Mon=mon, Y=y, YY=str(y)[2:], **{f"PUB{k}": f"{y + (m - 1 + k) // 12}-{(m - 1 + k) % 12 + 1:02d}" for k in (0, 1, 2)})
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
    if pdf.endswith(".txt"):   # a saved text layer (tests)
        return open(pdf, encoding="utf-8").read()
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


MONTH_RE = r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"


def month_rows(lines, ncols):
    """{'YYYY-MM': [numbers as printed]} for every line that is a month, a year and exactly ncols numbers."""
    rows = {}
    for ln in lines:
        m = re.match(r"^" + MONTH_RE + r" (\d{4}) ((?:\$? ?[\d,]+ ?)+)$", ln)
        if not m:
            continue
        cells = re.findall(r"[\d,]+", m.group(3))
        if len(cells) != ncols:
            continue
        key = f"{m.group(2)}-{[x[:3] for x in FULL].index(m.group(1)[:3]) + 1:02d}"
        if key in rows and rows[key]["cells"] != cells:
            sys.exit(f"month {key} printed twice with different numbers; not restating")
        rows[key] = {"cells": cells, "line": ln}
    return rows


def main_month_table(source, src, period, pdf, url):
    """A report whose table has one row per month and restates many prior months (Ginnie Mae: 25). The current month's
    labelled columns become receipts; every prior month on the page is kept as printed and compared with the most recent
    earlier edition on file, so a figure the publisher changed between editions is recorded. Read, not computed; the
    column positions are confirmed by the table's own printed totals (I + II = grand total) or the run stops."""
    y, m = int(period[:4]), int(period[5:7])
    sha = sha256(pdf)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text_of(pdf).splitlines()]
    rows = month_rows(lines, src["ncols"])
    if period not in rows:
        sys.exit(f"no row for {period} with {src['ncols']} numbers in the document (months found: {sorted(rows)[-3:]}); not restating")
    for k, r in rows.items():   # the printed totals must agree with the column positions assumed here
        c = [num(x) for x in r["cells"]]
        if c[8] + c[16] != c[17] or sum(c[9:16]) != c[16]:
            sys.exit(f"row {k}: printed totals do not match the assumed column layout ({r['line']}); not restating")
    month_label = f"{MON[m - 1].title()} {y}"
    figures = {}
    for fid, (col, coldesc, desc) in src["cells"].items():
        cell = rows[period]["cells"][col]
        figures[fid] = {"value": num(cell), "display": cell, "unit": "USD millions", "period_kind": "month", "period": month_label, "table": src["table"],
                        "row_label": coldesc.split("(")[1].rstrip(")") + ", month of " + FULL[m - 1] + " " + str(y), "column": coldesc, "line_as_printed": rows[period]["line"], "description": desc,
                        "revision": "as first printed; no later edition checked yet"}
    history = {k: {fid: num(rows[k]["cells"][col]) for fid, (col, _, _) in src["cells"].items()} for k in sorted(rows)}
    earlier = sorted(f for f in os.listdir(os.path.join(ROOT, "data", "official")) if re.fullmatch(re.escape(source) + r"-\d{4}-\d{2}\.json", f) and f[len(source) + 1:-5] < period) if os.path.isdir(os.path.join(ROOT, "data", "official")) else []
    prev_path = os.path.join(ROOT, "data", "official", earlier[-1]) if earlier else None
    prev = json.load(open(prev_path, encoding="utf-8")) if prev_path else None
    revisions = []
    if prev:
        for k in sorted(set(history) & set(prev.get("months_as_printed", {}))):
            for fid in src["cells"]:
                a, b = prev["months_as_printed"][k][fid], history[k][fid]
                yy, mm = int(k[:4]), int(k[5:7])
                revisions.append({"figure": fid, "month": k, "period": f"{MON[mm - 1].title()} {yy}", "first_printed": a, "printed_in": prev["document"]["edition"],
                                  "restated_in": f"{month_label} report", "restated_value": b, "revised": a != b, "has_receipt": k == prev["period"]})
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {"generated": now, "source_id": source, "period": period,
           "document": {"title": src["title"], "publisher": src["publisher"], "edition": f"{month_label} report", "url": url, "sha256": sha, "pages": None,
                        "exclusions": src["exclusions"], "retrieved_at": now},
           "level": "2 — attested restatement of an official publication; not computed by FinanceRateCalc",
           "not_comparable_with": src["not_comparable_with"], "does_not_establish": src["does_not_establish"], "quoting_rule": src["quoting_rule"],
           "figures": figures, "months_as_printed": history,
           "prior_edition_check": {"edition_compared": prev["document"]["edition"] if prev else None, "revisions": revisions,
                                   "note": "The table restates every month it lists; each is compared with the same month as printed in the most recent earlier edition on file. A difference is a source revision, recorded here and, where the month has a receipt, written into that edition's file as revised_in/revised_to."}}
    os.makedirs(os.path.join(ROOT, "data", "official"), exist_ok=True)
    p = os.path.join(ROOT, "data", "official", f"{source}-{period}.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if prev:
        for rev in revisions:
            if not rev["has_receipt"]:
                continue
            pf = prev["figures"][rev["figure"]]
            pf["revision"] = f"revised in the {month_label} report to {rev['restated_value']}" if rev["revised"] else f"unchanged in the {month_label} report"
            if rev["revised"]:
                pf["revised_in"] = f"{month_label} report"; pf["revised_to"] = rev["restated_value"]
        json.dump(prev, open(prev_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"compared with {prev['document']['edition']}: {len(revisions)} month-figures, {sum(1 for r in revisions if r['revised'])} revised")
    ip = os.path.join(ROOT, "data", "official", "index.json")
    idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else {"purpose": "index of restated official editions; latest per source", "editions": {}, "latest": {}}
    idx["editions"].setdefault(source, [])
    if period not in idx["editions"][source]:
        idx["editions"][source].append(period); idx["editions"][source].sort()
    idx["latest"][source] = idx["editions"][source][-1]; idx["generated"] = now
    json.dump(idx, open(ip, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{source} {period}: {len(figures)} figures restated, {len(history)} months kept as printed (sha256 {sha[:12]}…) -> {os.path.relpath(p, ROOT)}")
    for k, f in figures.items():
        print(f"  {k}: {f['display']} {f['unit']} [{f['period']}]")


# Files a new source is read from before any reader is written: fixed list, never a URL from the command line.
PROBES = {
    "sba-monthly-yearly": "https://sba-llms-prd-public.sbalenderportal.com/SBA-Monthly-MonthlyYearlyActivity7a504.xlsx",
    "sba-activity": "https://sba-llms-prd-public.sbalenderportal.com/SBA-Monthly-ActivityDashboard7a504.xlsx",
}


def probe(key):
    """Download one listed spreadsheet, print its hash, sheet names, sizes and first rows. Writes nothing to the site.
    The workflow posts this log as an issue (the run ends without a data file by design)."""
    import io
    import openpyxl
    data = _get(PROBES[key])
    print(f"PROBE {key}: {PROBES[key]} | {len(data):,} bytes | sha256 {hashlib.sha256(data).hexdigest()}")
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    budget = 9000
    for ws in wb.worksheets:
        head = f"--- sheet '{ws.title}' {ws.max_row} rows x {ws.max_column} cols"
        print(head); budget -= len(head)
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 14 or budget <= 0:
                break
            line = " | ".join("" if c is None else str(c)[:16] for c in row[:12]).rstrip(" |")
            if line:
                print(f"{i + 1}: {line}"); budget -= len(line) + 4
    print("probe complete; nothing written")


def _asof(wb):
    """The edition's own date: the 'as of' statement on the About sheet, as (date or None, sentence as printed)."""
    for ws in wb.worksheets:
        if ws.title.lower() != "about":
            continue
        for row in ws.iter_rows(values_only=True):
            for c in row:
                t = str(c or "")
                m = re.search(r"as of\s+([A-Za-z0-9,/ .-]+)", t)
                if not m:
                    continue
                raw = m.group(1).strip().rstrip(".")
                for rx, f in ((r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda g: (int(g[2]), int(g[0]), int(g[1]))), (r"(\d{4})-(\d{2})-(\d{2})", lambda g: (int(g[0]), int(g[1]), int(g[2]))),
                              (r"([A-Za-z]+)\.? (\d{1,2}),? (\d{4})", lambda g: (int(g[2]), [x[:3] for x in FULL].index(g[0][:3].title()) + 1, int(g[1])))):
                    mm = re.search(rx, raw)
                    if mm:
                        try:
                            return dt.date(*f(mm.groups())), t.strip()
                        except Exception:
                            pass
                return None, t.strip()
    return None, None


def main_xlsx_months(source, src, period, path):
    """A spreadsheet the publisher overwrites every month, with one row per approval month back to 1991 (SBA 7(a)/504).
    The file is hashed and kept (data/official/archive/), the requested month's labelled cells become receipts, every month
    in the sheet is kept as printed and compared with the previous edition on file. Read, not computed: the header labels
    must be where they are expected and the monthly loan counts must add up to the publisher's own Yearly sheet, or the
    run stops. 'latest' = the last month that was complete on the file's as-of date."""
    import io
    import calendar
    import openpyxl
    if path:
        data = open(path, "rb").read(); url = None
    else:
        data = _get(src["url"]); url = src["url"]
    sha = hashlib.sha256(data).hexdigest()
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb["Monthly"]
    rows = list(ws.iter_rows(values_only=True))
    hi = next((i for i, r in enumerate(rows[:12]) if r and str(r[0] or "").strip() == "Fiscal Year"), None)
    if hi is None:
        sys.exit("Monthly sheet: header row 'Fiscal Year' not found; not restating")
    H = [str(c or "").strip() for c in rows[hi]] + [""] * 12
    want = {1: "Approval Month", 2: "Program", 3: "Approved Loans", 4: "Approved Dollars", 8: "Approval Month", 9: "Program", 10: "Approved Loans", 11: "Approved Dollars"}
    bad = {k: (v, H[k]) for k, v in want.items() if H[k] != v}
    if bad:
        sys.exit(f"Monthly sheet: columns are not where expected {bad}; not restating")
    blocks = {"7(a)": (0, 1, 2), "504": (7, 8, 9)}   # block -> (fiscal year col, month col, program col)
    months, fy_loans = {}, {"7(a)": {}, "504": {}}
    for r in rows[hi + 1:]:
        r = list(r) + [None] * 12
        for blk, (cf, cm, cp) in blocks.items():
            if r[cm] is None or str(r[cp] or "").strip() != blk:
                continue
            key = str(r[cm]).strip()
            if not re.fullmatch(r"\d{6}", key):
                continue
            k = key[:4] + "-" + key[4:]
            for fid, (b, col, unit, _) in src["cells"].items():
                if b != blk:
                    continue
                v = r[col]
                if v is None:
                    sys.exit(f"Monthly sheet: empty cell for {fid} in {k}; not restating")
                months.setdefault(k, {})[fid] = int(v) if unit == "loans" else round(float(v), 2)
            fy_loans[blk][int(r[cf])] = fy_loans[blk].get(int(r[cf]), 0) + int(r[3 if blk == "7(a)" else 10])
    asof, asof_text = _asof(wb)
    allm = sorted(k for k, v in months.items() if len(v) == len(src["cells"]))
    if not allm:
        sys.exit("Monthly sheet: no month with all four figures; not restating")
    complete = [k for k in allm if asof and dt.date(int(k[:4]), int(k[5:7]), calendar.monthrange(int(k[:4]), int(k[5:7]))[1]) <= asof] if asof else allm[:-1]
    if period == "latest":
        period = complete[-1]
    if period not in complete:
        sys.exit(f"{period} is not a complete month in this file (as-of statement: {asof_text!r}; last complete month: {complete[-1]}); not restating")
    # the publisher's own Yearly sheet must agree with the monthly rows for every fiscal year that is fully in the past
    yr = list(wb["Yearly"].iter_rows(values_only=True))
    yhi = next((i for i, r in enumerate(yr[:12]) if r and str(r[0] or "").strip() == "Fiscal Year"), None)
    checked = 0
    if yhi is not None:
        last_fy = int(complete[-1][:4]) + (1 if int(complete[-1][5:7]) >= 10 else 0)
        for r in yr[yhi + 1:]:
            r = list(r) + [None] * 10
            for blk, cf, cl in (("7(a)", 0, 2), ("504", 6, 8)):
                if r[cf] is None or not str(r[cf]).strip().isdigit() or int(r[cf]) >= last_fy:
                    continue
                if fy_loans[blk].get(int(r[cf])) != int(r[cl]):
                    sys.exit(f"Yearly sheet says {int(r[cl])} {blk} loans for FY{int(r[cf])}; the monthly rows add to {fy_loans[blk].get(int(r[cf]))}; column layout not confirmed, not restating")
                checked += 1
    if checked < 10:
        sys.exit(f"only {checked} fiscal-year totals could be checked against the Yearly sheet; not restating")
    y, m = int(period[:4]), int(period[5:7])
    month_label = f"{MON[m - 1].title()} {y}"
    edition = f"edition as of {asof.isoformat()}" if asof else f"edition retrieved {dt.date.today().isoformat()}"
    figures = {}
    for fid, (blk, col, unit, desc) in src["cells"].items():
        v = months[period][fid]
        figures[fid] = {"value": v, "display": f"{v:,}" if unit == "loans" else f"{v:,.0f}", "unit": unit, "period_kind": "month", "period": month_label, "table": src["table"],
                        "row_label": f"{blk}, approval month {period.replace('-', '')}, {'Approved Loans' if unit == 'loans' else 'Approved Dollars'}", "column": "ABCDEFGHIJKL"[col],
                        "line_as_printed": f"{blk} | {period.replace('-', '')} | {v}", "description": desc, "revision": "as first printed; no later edition checked yet"}
    earlier = sorted(f for f in os.listdir(os.path.join(ROOT, "data", "official")) if re.fullmatch(re.escape(source) + r"-\d{4}-\d{2}\.json", f) and f[len(source) + 1:-5] < period) if os.path.isdir(os.path.join(ROOT, "data", "official")) else []
    prev_path = os.path.join(ROOT, "data", "official", earlier[-1]) if earlier else None
    prev = json.load(open(prev_path, encoding="utf-8")) if prev_path else None
    revisions = []
    if prev:
        if prev["document"]["sha256"] == sha:
            sys.exit(f"the file is byte-identical to the edition already restated ({prev['document']['edition']}); nothing new")
        for k in sorted(set(months) & set(prev.get("months_as_printed", {}))):
            for fid in src["cells"]:
                a0, b0 = prev["months_as_printed"][k].get(fid), months[k].get(fid)
                if a0 is None or b0 is None:
                    continue
                yy, mm_ = int(k[:4]), int(k[5:7])
                revisions.append({"figure": fid, "month": k, "period": f"{MON[mm_ - 1].title()} {yy}", "first_printed": a0, "printed_in": prev["document"]["edition"], "restated_in": edition,
                                  "restated_value": b0, "revised": abs(float(a0) - float(b0)) > 0.005, "has_receipt": k == prev["period"]})
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    od = os.path.join(ROOT, "data", "official"); os.makedirs(os.path.join(od, "archive"), exist_ok=True)
    arch = f"archive/{source}-{(asof.isoformat() if asof else dt.date.today().isoformat())}-{sha[:8]}.xlsx"
    open(os.path.join(od, arch), "wb").write(data)
    out = {"generated": now, "source_id": source, "period": period,
           "document": {"title": src["title"], "publisher": src["publisher"], "edition": edition, "url": url, "landing": src["landing"], "sha256": sha, "pages": None,
                        "exclusions": "Loan approvals as recorded on the edition's as-of date; the publisher replaces this file every month and earlier months can change",
                        "as_of_statement": asof_text, "archived_copy": "data/official/" + arch, "retrieved_at": now},
           "level": "2 — attested restatement of an official publication; not computed by FinanceRateCalc",
           "not_comparable_with": src["not_comparable_with"], "does_not_establish": src["does_not_establish"], "quoting_rule": src["quoting_rule"],
           "figures": figures, "months_as_printed": {k: months[k] for k in allm}, "fiscal_year_totals_checked_against_yearly_sheet": checked,
           "prior_edition_check": {"edition_compared": prev["document"]["edition"] if prev else None, "revisions": [r for r in revisions if r["revised"] or r["has_receipt"]],
                                   "compared": len(revisions), "changed": sum(1 for r in revisions if r["revised"]),
                                   "note": "Every month in the sheet is compared with the same month in the previous edition on file. Only changed figures and the receipted month are listed; 'compared' and 'changed' count all of them. The publisher overwrites the file, so the previous edition survives only as the archived copy named in that edition's record."}}
    json.dump(out, open(os.path.join(od, f"{source}-{period}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if prev:
        for rev in revisions:
            if not rev["has_receipt"]:
                continue
            pf = prev["figures"][rev["figure"]]
            pf["revision"] = f"printed as {rev['restated_value']} in the {edition}" if rev["revised"] else f"unchanged in the {edition}"
            if rev["revised"]:
                pf["revised_in"] = edition; pf["revised_to"] = rev["restated_value"]
        json.dump(prev, open(prev_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"compared with {prev['document']['edition']}: {len(revisions)} month-figures, {sum(1 for r in revisions if r['revised'])} changed")
    ip = os.path.join(od, "index.json")
    idx = json.load(open(ip, encoding="utf-8")) if os.path.exists(ip) else {"purpose": "index of restated official editions; latest per source", "editions": {}, "latest": {}}
    idx["editions"].setdefault(source, [])
    if period not in idx["editions"][source]:
        idx["editions"][source].append(period); idx["editions"][source].sort()
    idx["latest"][source] = idx["editions"][source][-1]; idx["generated"] = now
    json.dump(idx, open(ip, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open("/tmp/official_period", "w").write(period)
    print(f"{source} {period}: {len(figures)} figures restated, {len(allm)} months kept as printed, {checked} fiscal-year totals confirmed against the Yearly sheet, {edition} (sha256 {sha[:12]}…)")
    for k, f in figures.items():
        print(f"  {k}: {f['display']} {f['unit']} [{f['period']}]")


def main():
    source, period = sys.argv[1], sys.argv[2]
    if source in SOURCES and SOURCES[source].get("kind") == "xlsx_months":
        a_ = sys.argv[3:]
        return main_xlsx_months(source, SOURCES[source], period, a_[a_.index("--pdf") + 1] if "--pdf" in a_ else None)
    if source == "probe":
        if period not in PROBES:
            sys.exit(f"unknown probe '{period}'; known: {', '.join(PROBES)}")
        probe(period); return
    src = SOURCES[source]
    y, m = int(period[:4]), int(period[5:7])
    a = sys.argv[3:]
    pdf = a[a.index("--pdf") + 1] if "--pdf" in a else None
    url = None
    if not pdf:
        os.makedirs(os.path.join(ROOT, "data", "official", "cache"), exist_ok=True)
        pdf = os.path.join(ROOT, "data", "official", "cache", f"{source}-{period}.pdf")
        url = fetch(src, y, m, pdf)
    if src.get("kind") == "month_table":
        return main_month_table(source, src, period, pdf, url)
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
