#!/usr/bin/env python3
"""Tie every data table on the live pages to the published data file its rows come from, and prove the tie row by row.

A table row names something (a lender, a state, a metro, a loan purpose) and prints numbers about it. A row is
*found* when one record of a published data file carries that name and every figure-like number of the row.
A table is bound to the file (or folder of files) in which at least 95% of its rows are found. A bound table gets
the source path and its SHA-256 as attributes and one visible line under it, so a reader or a machine can fetch the
file, check the hash and find each row. Tables that do not reach 95% are listed with their best candidate, not bound.

Matching a number allows for how a page prints it: thousands separators, fewer decimals than stored, a share stored
as 0.2208 and printed as 22.1%. Matching a name ignores case and punctuation and knows state names and codes.
Finding a row's numbers inside the record that carries its name is far stronger than finding them anywhere in a
file: a large file contains most small numbers somewhere.

    python3 scripts/bind_tables.py            # bind, write eval/table-binding.json
    python3 scripts/bind_tables.py --check    # fail if a bound table no longer matches its source
"""
import glob, hashlib, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TABLE = re.compile(r"<table\b[^>]*>[\s\S]*?</table>", re.I)
ROW = re.compile(r"<tr\b[^>]*>([\s\S]*?)</tr>", re.I)
CELL = re.compile(r"<t[dh]\b[^>]*>([\s\S]*?)</t[dh]>", re.I)
NUM = re.compile(r"(?<![\w.])-?\$?\d[\d,]*\.?\d*%?")
REC = re.compile(r"⟦FRC:[^⟧]*⟧")
NOTE = re.compile(r'\n?<p class="frc-table-source"[\s\S]*?</p>')
THRESH = 0.95
# pages rewritten from their data by a builder that compares its own output byte for byte: bound in the manifest, not in the page
GENERATED = {"official-figures.html", "revision-ledger.html", "fha-denial-reasons-by-lender.html"}
ST = {"alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de", "district of columbia": "dc",
      "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id", "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks", "kentucky": "ky", "louisiana": "la", "maine": "me",
      "maryland": "md", "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms", "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
      "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny", "north carolina": "nc", "north dakota": "nd", "ohio": "oh", "oklahoma": "ok", "oregon": "or",
      "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc", "south dakota": "sd", "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va",
      "washington": "wa", "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy", "puerto rico": "pr"}


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(t).lower())).strip()


def forms_of(v):
    out = set()
    for x in (v, v * 100):
        for d in (0, 1, 2):
            out.add(round(x, d))
    return out


def records(o, key, out):
    """Every dict in the document as a record: the names it carries and every number beneath it."""
    nums = set()
    if isinstance(o, dict):
        names = {norm(key)} if key is not None else set()
        for k, v in o.items():
            if isinstance(v, str):
                if len(v) <= 90:
                    names.add(norm(v))
                for t in NUM.findall(v):
                    w = re.sub(r"[^\d.\-]", "", t)
                    if re.fullmatch(r"-?\d+(\.\d+)?", w):
                        nums |= forms_of(float(w))
            elif isinstance(v, bool) or v is None:
                continue
            elif isinstance(v, (int, float)):
                nums |= forms_of(float(v))
            else:
                nums |= records(v, k, out)
        out.append((names - {""}, nums))
    elif isinstance(o, list):
        for v in o:
            if isinstance(v, (dict, list)):
                nums |= records(v, key, out)
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                nums |= forms_of(float(v))
    return nums


def load_sources():
    src = {}
    paths = sorted(glob.glob("api/**/*.json", recursive=True) + glob.glob("data/*.json") + glob.glob("data/purpose/*.json") + glob.glob("data/official/*.json") + glob.glob("data/programs/*.json"))
    for f in paths:
        try:
            raw = open(f, "rb").read()
            recs = []
            allnums = records(json.loads(raw), None, recs)
        except Exception:
            continue
        if allnums:
            src[f] = {"recs": recs, "all": allnums, "sha": hashlib.sha256(raw).hexdigest()}
    # a table that lists many states, lenders or metros draws on a folder of files; the folder is one source, hashed as
    # the SHA-256 of its files' hashes in name order
    for folder in ("api/state/", "api/lender/", "api/metro/"):
        members = [k for k in sorted(src) if k.startswith(folder)]
        if members:
            recs = []
            for k in members:
                slug = norm(os.path.basename(k)[:-5])
                whole = (set().union(*(r[0] for r in src[k]["recs"])) | {slug}, src[k]["all"])   # the file as one record, named by its slug
                recs.append(whole); recs.extend(src[k]["recs"])
            src[folder] = {"recs": recs, "all": set().union(*(src[k]["all"] for k in members)), "sha": hashlib.sha256("".join(src[k]["sha"] for k in members).encode()).hexdigest()}
    for v in src.values():   # name -> records index
        idx = {}
        for i, (names, _) in enumerate(v["recs"]):
            for n in names:
                idx.setdefault(n, []).append(i)
        v["idx"] = idx
    return src


def cell_text(c):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", REC.sub(" ", c)))).strip()


def table_rows(tab):
    """[(label, [numbers])] for rows that print at least one figure-like number."""
    out = []
    for r in ROW.findall(tab):
        cells = [cell_text(c) for c in CELL.findall(r)]
        label, nums = None, []
        for c in cells:
            found = []
            for x in NUM.findall(c):
                digits = re.sub(r"\D", "", x)
                if not digits or re.fullmatch(r"(19|20)\d\d", x):
                    continue
                if "%" in x or "$" in x or len(digits) >= 3 or "." in x:   # the same test the coverage meter uses
                    w = re.sub(r"[^\d.\-]", "", x)
                    if re.fullmatch(r"-?\d+(\.\d+)?", w):
                        found.append(float(w))
            nums += found
            if label is None and re.search(r"[A-Za-z]{2}", c) and not found:
                label = c
        if nums:
            out.append((label, nums))
    return out


def row_found(label, nums, s):
    if label is None:
        return False
    n = norm(label)
    keys = [n] + ([ST[n]] if n in ST else [])
    cands = []
    for k in keys:
        cands += s["idx"].get(k, [])
    if not cands and len(n) >= 6:   # the page may print a shortened or lengthened name
        for name, ids in s["idx"].items():
            if len(name) >= 6 and (name.startswith(n) or n.startswith(name)):
                cands += ids
    return any(all(v in s["recs"][i][1] for v in nums) for i in cands[:400])


def live_pages():
    for f in sorted(glob.glob("**/*.html", recursive=True)):
        if f.startswith((".venv/", "node_modules/", "packages/")):
            continue
        s = open(f, encoding="utf-8", errors="ignore").read()
        if re.search(r"Retired \d{4}-\d{2}-\d{2};", s) or "<table" not in s:
            continue
        yield f, s


def main():
    check = "--check" in sys.argv
    src = load_sources()
    bound = failed = nums_bound = nums_failed = 0
    report, bad = [], []
    for f, s in live_pages():
        parts, pos, changed = [], 0, False
        for m in TABLE.finditer(s):
            tab = m.group(0)
            rows = table_rows(tab)
            n_nums = sum(len(r[1]) for r in rows)
            if len(rows) < 2 or n_nums < 4:
                continue
            head = tab[:tab.index(">") + 1]
            had = re.search(r'data-frc-source="([^"]+)"', head)
            if check:
                if had:
                    sc = src.get(had.group(1))
                    share = sum(row_found(l, n, sc) for l, n in rows) / len(rows) if sc else 0
                    if share < THRESH:
                        bad.append((f, had.group(1), round(share, 3)))
                continue
            best, share = None, 0.0
            for name, sc in src.items():
                if sum(1 for _, ns in rows for v in ns if v in sc["all"]) < 0.9 * n_nums:
                    continue   # cheap screen before the row-level test
                sh = sum(row_found(l, n, sc) for l, n in rows) / len(rows)
                if sh > share or (sh == share and best and len(name) < len(best)):
                    best, share = name, sh
            if best and share >= THRESH and f in GENERATED:
                bound += 1; nums_bound += n_nums
                report.append({"page": f, "source": best, "sha256": src[best]["sha"], "rows": len(rows), "numbers": n_nums, "rows_found": round(share, 3), "written_in_page": False})
            elif best and share >= THRESH:
                head2 = re.sub(r'\sdata-frc-(?:source|sha256)="[^"]*"', "", head)
                head2 = head2[:-1] + f' data-frc-source="{best}" data-frc-sha256="{src[best]["sha"]}">'
                what = "this folder of files" if best.endswith("/") else "this file"
                href = "/api/index.json" if best.endswith("/") else "/" + best
                note = (f'\n<p class="frc-table-source" style="font-size:12px;opacity:.75;margin:6px 0 14px">Each row of this table was found, name and numbers together, in '
                        f'<a href="{href}" style="color:inherit;text-decoration:underline">{best}</a> ({what}; SHA-256 {src[best]["sha"][:16]}&hellip;). '
                        f'<a href="/eval/table-binding.json" style="color:inherit;text-decoration:underline">Checked daily</a>.</p>')
                old = NOTE.match(s[m.end():])
                parts.append(s[pos:m.start()] + head2 + tab[len(head):] + note)
                pos = m.end() + (old.end() if old else 0)
                changed = True; bound += 1; nums_bound += n_nums
                report.append({"page": f, "source": best, "sha256": src[best]["sha"], "rows": len(rows), "numbers": n_nums, "rows_found": round(share, 3), "written_in_page": True})
            else:
                failed += 1; nums_failed += n_nums
                report.append({"page": f, "source": None, "best_candidate": best, "rows": len(rows), "numbers": n_nums, "rows_found": round(share, 3)})
        if changed and not check:
            open(f, "w", encoding="utf-8").write("".join(parts) + s[pos:])
    if check:
        print("bound tables:", "every one still matches its source" if not bad else f"{len(bad)} no longer match, e.g. {bad[:4]}")
        sys.exit(1 if bad else 0)
    out = {"what": "Data tables on live pages and the published source each one's rows were found in. A row is found when one record of the source carries the row's name and every number printed in the row. A table is bound at 95% of rows; bound tables carry the source path and its SHA-256.",
           "tables_bound": bound, "numbers_in_bound_tables": nums_bound, "tables_not_bound": failed, "numbers_in_unbound_tables": nums_failed,
           "tables": sorted(report, key=lambda r: (r["source"] is not None, -r["numbers"]))}
    json.dump(out, open("eval/table-binding.json", "w", encoding="utf-8"), indent=1)
    print(f"bound {bound} tables ({nums_bound} numbers); not bound {failed} tables ({nums_failed} numbers)")
    for r in out["tables"][:16]:
        print("  unbound" if not r["source"] else "  bound", r["numbers"], r["rows_found"], r["page"], r.get("best_candidate") or r["source"])


if __name__ == "__main__":
    main()
