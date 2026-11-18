#!/usr/bin/env python3
"""Vintages from the Internet Archive: every archived edition of an official monthly report, read with the same reader
that restates new editions, and compared month by month.

Each edition of HUD's FHA Loan Performance Trends report prints a table of the latest thirteen months. A month is
therefore printed in up to thirteen editions. Reading every archived edition gives, for each month and each figure,
the value as first printed and as printed in every later edition: a real-time (vintage) data set, and a count of how
often, how far and in which direction the publisher changed a figure it had already printed.

    python3 scripts/archive_backfill.py hud-lpt            # list, download, read, compare; writes data/vintage/ and eval/vintage/
    python3 scripts/archive_backfill.py hud-lpt --list     # availability only: what the Archive holds, nothing downloaded

Nothing here is estimated. An edition that cannot be read with confidence (a row whose parts do not sum to the printed
serious delinquency rate, a missing year, a duplicate month) is recorded as unread with the reason, not repaired.
"""
import collections, datetime as dt, hashlib, json, os, re, sys, tempfile, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import official_restate as R  # noqa: E402

UA = "Mozilla/5.0 (compatible; FinanceRateCalc vintage-backfill/1.0; +https://financeratecalc.com)"
QUERIES = {   # CDX prefix queries; file names and folders changed over the years, so several are tried and merged
    "hud-lpt": ["hud.gov/sites/default/files/Housing/documents/FHALPT", "hud.gov/sites/dfiles/Housing/documents/FHALPT", "hud.gov/sites/documents/FHALPT",
                "portal.hud.gov/hudportal/documents/huddoc?id=FHALPT", "hud.gov/sites/default/files/Housing/documents/FHA_LPT", "hud.gov/sites/dfiles/Housing/documents/FHA_LPT"],
    "hud-fhaprod": ["hud.gov/sites/default/files/Housing/documents/FHAProd", "hud.gov/sites/dfiles/Housing/documents/FHAProd", "hud.gov/sites/documents/FHAProd",
                    "portal.hud.gov/hudportal/documents/huddoc?id=FHAProd"],
    "ginnie-iss": ["ginniemae.gov/s3/sites/default/files/", "ginniemae.gov/data_and_reports/reporting/ReportingDocuments/"],
}
KEEP = {"hud-lpt": r"fhalpt|fha_lpt", "hud-fhaprod": r"fhaprod", "ginnie-iss": r"_iss\.pdf|issuance.*summary"}


def get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180) as r:
                return r.read()
        except Exception as e:   # the Archive throttles; wait and try again
            last = e; time.sleep(6 * (i + 1))
    raise last


def captures(source):
    """{original url: [(timestamp, digest)]} for captures answered 200, one per distinct content digest."""
    out = collections.defaultdict(dict)
    notes = []
    for q in QUERIES[source]:
        u = "http://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode({"url": q, "matchType": "prefix", "output": "json", "filter": "statuscode:200",
                                                                             "fl": "original,timestamp,digest,mimetype,length", "limit": "20000"})
        try:
            rows = json.loads(get(u) or b"[]")
        except Exception as e:
            notes.append(f"{q}: query failed ({type(e).__name__} {str(e)[:60]})"); continue
        n = 0
        for row in rows[1:]:
            orig, ts, dig, mime = row[0], row[1], row[2], row[3]
            if not re.search(KEEP[source], orig, re.I) or "pdf" not in (mime + orig).lower():
                continue
            key = re.sub(r"^https?://(www\.)?", "", orig).split("#")[0]
            out[key].setdefault(dig, (ts, orig)); n += 1
        notes.append(f"{q}: {len(rows) - 1 if rows else 0} captures, {n} kept")
        time.sleep(2)
    return {k: sorted(v.values()) for k, v in out.items()}, notes


def read_lpt(pdf):
    """({month: [7 printed cells]}, None) or (None, reason)."""
    try:
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in R.text_of(pdf).splitlines()]
        rows = R.lpt_rows(lines)
    except SystemExit as e:
        return None, str(e)[:200]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:160]}"
    if len(rows) < 6:
        return None, f"only {len(rows)} month rows recognised (the table layout of this edition differs)"
    out = {}
    for k, r in rows.items():
        c = [R.num(x) for x in r["cells"]]
        if len(c) != 7 or abs(c[3] + c[4] + c[5] - c[6]) > 0.021:
            return None, f"row {k}: 90-day + foreclosure + bankruptcy does not give the printed serious delinquency rate ({r['line'][:80]})"
        out[k] = c
    return out, None


MONS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def period_from_name(url):
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[ _-]?((?:19|20)\d{2})", urllib.parse.unquote(url).rsplit("/", 1)[-1].replace("id=", " ").lower())
    return f"{m.group(2)}-{MONS.index(m.group(1)) + 1:02d}" if m else None


def read_fhaprod(pdf):
    """({figure: (this month, prior month as restated)}, None) or (None, reason). Table 4 prints the month and the month before it."""
    try:
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in R.text_of(pdf).splitlines()]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:160]}"
    out = {}
    for fid, (table, rx, col, unit, kind, desc) in R.SOURCES["hud-fhaprod"]["cells"].items():
        if table != "Table 4" or kind != "month" or col != 0:
            continue
        hits = {m.group(0): m for ln in lines for m in [re.match(rx, ln)] if m}
        if len(hits) != 1:
            continue
        m = next(iter(hits.values()))
        if m.lastindex and m.lastindex >= 2:
            out[fid] = (R.num(m.group(1)), R.num(m.group(2)))
    if "purchase-count" not in out or "refinance-count" not in out:
        return None, "purchase and refinance loan-count rows not found once each (the layout of this edition differs)"
    for j in (0, 1):   # the printed purchase share must follow from the two counts, or the columns are not what is assumed
        pc, rc = out["purchase-count"][j], out["refinance-count"][j]
        if "purchase-share-pct" in out and pc + rc and abs(100 * pc / (pc + rc) - out["purchase-share-pct"][j]) > 0.06:
            return None, f"column {j + 1}: the printed purchase share does not follow from the two counts ({pc}, {rc}, {out['purchase-share-pct'][j]})"
    return out, None


def run_fhaprod(caps, summary):
    editions, unread, tmp = {}, [], tempfile.mkdtemp()
    for u in sorted(caps):
        want = period_from_name(u)
        if want and want in editions:
            continue   # the same edition filed under another folder
        for ts, orig in caps[u][:2]:
            try:
                data = get(f"http://web.archive.org/web/{ts}id_/{orig}")
            except Exception as e:
                unread.append({"url": orig, "capture": ts, "reason": f"download failed: {type(e).__name__}"}); continue
            if data[:4] != b"%PDF":
                unread.append({"url": orig, "capture": ts, "reason": "not a PDF"}); continue
            p = os.path.join(tmp, "e.pdf"); open(p, "wb").write(data)
            vals, why = read_fhaprod(p)
            if vals is None:
                unread.append({"url": orig, "capture": ts, "reason": why}); continue
            if not want:
                unread.append({"url": orig, "capture": ts, "reason": "the file name carries no month and year"}); continue
            editions.setdefault(want, {"period": want, "url": orig, "capture": ts, "archive_url": f"https://web.archive.org/web/{ts}/{orig}", "sha256": hashlib.sha256(data).hexdigest(),
                                       "this_month": {k: v[0] for k, v in vals.items()}, "prior_month_as_restated": {k: v[1] for k, v in vals.items()}})
            time.sleep(1.5); break
    order = sorted(editions)
    os.makedirs(os.path.join(ROOT, "data", "vintage"), exist_ok=True)
    json.dump({"what": "Every edition of HUD's FHA Single Family Production Report that the Internet Archive holds and that could be read: Table 4, the month and the prior month as restated. Read, not computed.",
               "source": "hud-fhaprod", "editions": [editions[p] for p in order]}, open(os.path.join(ROOT, "data", "vintage", "hud-fhaprod-editions.json"), "w", encoding="utf-8"), indent=1)
    nxt = lambda p: f"{int(p[:4]) + (p[5:] == '12')}-{(int(p[5:]) % 12) + 1:02d}"
    changes, stats = [], {}
    for p in order:
        q = nxt(p)
        if q not in editions:
            continue
        for fid, a in editions[p]["this_month"].items():
            if fid not in editions[q]["prior_month_as_restated"]:
                continue
            b = editions[q]["prior_month_as_restated"][fid]
            s = stats.setdefault(fid, {"comparisons": 0, "changed": 0, "up": 0, "down": 0, "sum_change": 0.0, "sum_abs_change": 0.0, "largest": None})
            s["comparisons"] += 1
            if a != b:
                s["changed"] += 1; s["up" if b > a else "down"] += 1; s["sum_change"] += b - a; s["sum_abs_change"] += abs(b - a)
                c = {"figure": fid, "month": p, "first_printed": a, "in_edition": p, "restated_as": b, "in_edition_after": q, "difference": round(b - a, 4),
                     "relative_pct": round(100 * (b - a) / a, 4) if a else None}
                changes.append(c)
                if s["largest"] is None or abs(c["difference"]) > abs(s["largest"]["difference"]):
                    s["largest"] = c
    for s in stats.values():
        s["share_changed_pct"] = round(100 * s["changed"] / s["comparisons"], 1) if s["comparisons"] else None
        s["mean_change_when_changed"] = round(s["sum_change"] / s["changed"], 4) if s["changed"] else None
        s["sum_change"] = round(s["sum_change"], 4); s["sum_abs_change"] = round(s["sum_abs_change"], 4)
    summary.update({"editions_read": len(order), "first_edition": order[0] if order else None, "last_edition": order[-1] if order else None,
                    "consecutive_pairs": sum(1 for p in order if nxt(p) in editions), "unread": unread, "by_figure": stats,
                    "reading": "comparisons = a month's figure in its own edition against the same month as restated in the next month's edition (Table 4 prints both). Only consecutive editions are compared."})
    json.dump(summary, open(os.path.join(ROOT, "eval", "vintage", "hud-fhaprod-summary.json"), "w", encoding="utf-8"), indent=1)
    json.dump({"what": "Every figure the next edition restated with a different value.", "changes": changes}, open(os.path.join(ROOT, "eval", "vintage", "hud-fhaprod-revisions.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("unread", "queries")}, indent=1)[:7000])
    print("unread:", len(unread), collections.Counter(re.sub(r"\(.*", "", x["reason"])[:70] for x in unread).most_common(6))


def main():
    source = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "hud-lpt"
    list_only = "--list" in sys.argv
    caps, notes = captures(source)
    urls = sorted(caps)
    multi = {u: len(c) for u, c in caps.items() if len(c) > 1}
    stamps = sorted(ts for c in caps.values() for ts, _ in c)
    summary = {"source": source, "run": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "queries": notes, "distinct_files": len(urls),
               "captures_with_distinct_content": sum(len(c) for c in caps.values()), "files_whose_content_changed_under_the_same_name": len(multi),
               "earliest_capture": stamps[0][:8] if stamps else None, "latest_capture": stamps[-1][:8] if stamps else None}
    os.makedirs(os.path.join(ROOT, "eval", "vintage"), exist_ok=True)
    # other names the same report may have been filed under (listed only, so a gap in the editions can be explained)
    if source == "hud-lpt":
        try:
            u = "http://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode({"url": "hud.gov/sites/dfiles/Housing/documents/", "matchType": "prefix", "output": "json", "collapse": "urlkey",
                                                                                 "filter": ["statuscode:200", "urlkey:.*(lpt|loanperf|loan_perf|performance).*"], "fl": "original,timestamp", "limit": "3000"}, doseq=True)
            rows = json.loads(get(u) or b"[]")[1:]
            summary["other_candidate_names"] = sorted({r[0].rsplit("/", 1)[-1] for r in rows if not re.search(r"fhalpt", r[0], re.I)})[:200]
        except Exception as e:
            summary["other_candidate_names"] = f"query failed: {type(e).__name__}"
    if source == "hud-fhaprod" and not list_only and urls:
        return run_fhaprod(caps, summary)
    if list_only or source != "hud-lpt" or not urls:
        summary["files"] = [{"url": u, "captures": [ts for ts, _ in caps[u]]} for u in urls][:600]
        summary["note"] = "Availability only." if list_only or not urls else "Reading is implemented for hud-lpt; this run lists what the Archive holds for the other reports."
        json.dump(summary, open(os.path.join(ROOT, "eval", "vintage", f"{source}-availability.json"), "w", encoding="utf-8"), indent=1)
        print(json.dumps({k: v for k, v in summary.items() if k != "files"}, indent=1)); return

    cells = R.SOURCES["hud-lpt"]["cells"]
    editions, unread = {}, []   # period -> edition record (first capture wins; later distinct contents kept as 'reissues')
    tmp = tempfile.mkdtemp()
    for u in urls:
        if period_from_name(u) in editions and len(caps[u]) == 1:
            continue   # the same edition filed under another folder
        for j, (ts, orig) in enumerate(caps[u]):
            try:
                data = get(f"http://web.archive.org/web/{ts}id_/{orig}")
            except Exception as e:
                unread.append({"url": orig, "capture": ts, "reason": f"download failed: {type(e).__name__}"}); continue
            if data[:4] != b"%PDF":
                unread.append({"url": orig, "capture": ts, "reason": "not a PDF"}); continue
            p = os.path.join(tmp, "e.pdf"); open(p, "wb").write(data)
            rows, why = read_lpt(p)
            if rows is None:
                unread.append({"url": orig, "capture": ts, "reason": why}); continue
            period = max(rows)
            rec = {"period": period, "url": orig, "capture": ts, "archive_url": f"https://web.archive.org/web/{ts}/{orig}", "sha256": hashlib.sha256(data).hexdigest(),
                   "months": {k: {fid: rows[k][spec[0]] for fid, spec in cells.items()} for k in sorted(rows)}}
            if period not in editions:
                editions[period] = rec
            elif editions[period]["sha256"] != rec["sha256"]:
                editions[period].setdefault("reissues", []).append({k: rec[k] for k in ("url", "capture", "archive_url", "sha256", "months")})
            time.sleep(1.5)
    os.makedirs(os.path.join(ROOT, "data", "vintage"), exist_ok=True)
    order = sorted(editions)
    json.dump({"what": "Every edition of HUD's FHA Single Family Loan Performance Trends report that the Internet Archive holds and that could be read with the row check passing; "
                       "the non-seasonally-adjusted month table as printed in each. Read, not computed.",
               "source": source, "editions": [editions[p] for p in order]}, open(os.path.join(ROOT, "data", "vintage", "hud-lpt-editions.json"), "w", encoding="utf-8"), indent=1)

    # the triangle: for each month and figure, the value in each edition that prints it, in edition order
    tri = collections.defaultdict(list)
    for p in order:
        for m, vals in editions[p]["months"].items():
            for fid, v in vals.items():
                tri[(m, fid)].append((p, v))
    changes, stats = [], {fid: {"months_seen_in_two_or_more_editions": 0, "comparisons": 0, "changed": 0, "up": 0, "down": 0, "first_print_seen": 0,
                                "first_to_last_changed": 0, "first_to_last_up": 0, "first_to_last_down": 0, "sum_first_to_last": 0.0, "largest": None} for fid in cells}
    for (m, fid), seq in sorted(tri.items()):
        s = stats[fid]
        if len(seq) < 2:
            continue
        s["months_seen_in_two_or_more_editions"] += 1
        for (pa, a), (pb, b) in zip(seq, seq[1:]):
            s["comparisons"] += 1
            if a != b:
                s["changed"] += 1; s["up" if b > a else "down"] += 1
                changes.append({"figure": fid, "month": m, "printed": a, "in_edition": pa, "then": b, "in_next_edition_read": pb, "difference": round(b - a, 4)})
                if s["largest"] is None or abs(b - a) > abs(s["largest"]["difference"]):
                    s["largest"] = changes[-1]
        if seq[0][0] == m:   # the month's own edition was read, so the first print is known
            s["first_print_seen"] += 1
            d = seq[-1][1] - seq[0][1]
            if d:
                s["first_to_last_changed"] += 1; s["first_to_last_up" if d > 0 else "first_to_last_down"] += 1; s["sum_first_to_last"] += d
    for s in stats.values():
        s["mean_first_to_last_revision"] = round(s["sum_first_to_last"] / s["first_print_seen"], 5) if s["first_print_seen"] else None
        s["sum_first_to_last"] = round(s["sum_first_to_last"], 4)
    summary.update({"editions_read": len(order), "first_edition": order[0] if order else None, "last_edition": order[-1] if order else None,
                    "editions_missing_between": [f"{y}-{mo:02d}" for y in range(int(order[0][:4]), int(order[-1][:4]) + 1) for mo in range(1, 13)
                                                 if order and order[0] <= f"{y}-{mo:02d}" <= order[-1] and f"{y}-{mo:02d}" not in editions],
                    "editions_reissued_under_the_same_name": sorted(p for p in order if editions[p].get("reissues")),
                    "unread": unread, "by_figure": stats,
                    "reading": "comparisons = a month's value in one edition against the same month in the next edition read (consecutive editions when none is missing). "
                               "first_to_last = the value in the month's own edition against its value in the last edition that prints it. A gap in the editions read makes a change "
                               "datable only to the interval between the two editions compared."})
    json.dump(summary, open(os.path.join(ROOT, "eval", "vintage", "hud-lpt-summary.json"), "w", encoding="utf-8"), indent=1)
    json.dump({"what": "Every change found between two editions of the report for the same month and figure.", "changes": changes},
              open(os.path.join(ROOT, "eval", "vintage", "hud-lpt-revisions.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("unread", "queries")}, indent=1)[:6000])
    print("unread:", len(unread), collections.Counter(re.sub(r"\(.*", "", x["reason"])[:60] for x in unread).most_common(6))


if __name__ == "__main__":
    main()
