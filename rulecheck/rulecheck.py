#!/usr/bin/env python3
"""FRC Rule Watch — finds US mortgage rule constants in a codebase that are stale, or about to be.

Like Dependabot, but for regulatory numbers: FHA and conforming loan limits, FHA annual MIP, the VA
funding fee. Every constant in constants.json carries the date after which it stops being valid.
A value past that date, used as if it were current, is reported (and fails the check with
--fail-on stale). A current value whose expiry is near is reported as a warning, so the update can
be made before 1 January rather than after.

Deterministic, no model, no network unless --constants is a URL. Standard library only.
Classes (same as the FinanceRateCalc stale-constant scan):
  presented_as_current  the value is used or described as current            -> error
  role_misuse           $726,200 used as a loan limit (it is the MIP threshold) -> error
  expiring              a current value that expires within --warn-days        -> warning
  dated_correct         labelled with its own year: historical, fine           -> notice only with --verbose
  test_or_mock          test / fixture / mock path                             -> notice
  changelog             the replacement value appears beside it                -> ignored
  unresolved            no year, no currency signal                            -> notice
"""
import argparse, datetime, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT_EXT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".java", ".kt", ".swift", ".cs", ".php", ".rs",
            ".json", ".yaml", ".yml", ".toml", ".md", ".mdx", ".html", ".htm", ".txt", ".csv", ".sql", ".vue", ".svelte", ".dart", ".ex", ".exs"}
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".next", ".venv", "venv", "__pycache__", "coverage", ".cache"}
TEST_RX = re.compile(r"(^|/)(test|tests|__tests__|spec|fixtures?|mocks?|bench|benchmarks?|samples?)(/|$)|\.(test|spec)\.", re.I)


def load_constants(src):
    if re.match(r"https?://", src):
        return json.load(urllib.request.urlopen(src, timeout=20))
    return json.load(open(src, encoding="utf-8"))


def needle(c):
    v = c["value"]
    if c["kind"] == "usd":
        s = f"{int(v):,}"
        return re.compile(r"(?<![\d.,])\$?\s?" + s.replace(",", ",?") + r"(?![\d])")
    s = ("%g" % v).replace(".", r"\.")
    return re.compile(r"(?<![\d.])" + s + r"0?\s?%")  # percentages need the % sign to avoid matching any 2.3


def classify(line, ctx, c, path, today):
    low, win = line.lower(), ctx.lower()
    if not any(k in win for k in c["keywords"]):
        return None  # same digits, different subject
    valid_to = datetime.date.fromisoformat(c["valid_to"])
    year = valid_to.year
    years_line = [int(y) for y in re.findall(r"\b(20\d{2})\b", line)]
    years_near = [int(y) for y in re.findall(r"\b(20\d{2})\b", ctx)]
    current_word = re.search(r"\b(current|currently|today|now|this year|latest|as of)\b", win)
    if c.get("current"):
        days = (valid_to - today).days
        if days < 0:
            if year in years_line and not re.search(r"\b(current|currently|today|now|this year)\b", low):
                return ("dated_correct", f"labelled {year} on the same line")
            return ("presented_as_current", f"{c['meaning']} expired on {c['valid_to']}; replace with {c['replaced_by']}")
        return ("expiring", f"{c['meaning']} is valid until {c['valid_to']} ({days} days); then {c['replaced_by']}")
    repl = c.get("replaced_by", "")
    flat = ctx.replace(",", "")
    for rv in c.get("replacement_values", []):
        pat = (r"(?<![\d.])" + str(int(rv)) + r"(?![\d])") if c["kind"] == "usd" else (r"(?<![\d.])" + ("%g" % rv).replace(".", r"\.") + r"0?\s?%")
        if re.search(pat, flat):
            return ("changelog", "the replacement value appears beside it")
    if c.get("role_check"):
        if re.search(r"\b(loan limit|lending limit|max(imum)? loan|borrow up to|conforming limit)\b", win) and not re.search(r"\b(mip|mortgage insurance|premium|threshold)\b", win):
            return ("role_misuse", "$726,200 used as a loan limit; it is the FHA annual-MIP base-loan threshold (and the 2023 conforming baseline)")
        return ("unresolved", "$726,200 present; role not clear from context")
    # a value labelled with its own year on the same line is historical, unless the same line also names a later year
    if year in years_line and not any(y > year for y in years_line if y != year + 0 and y - year > 1):
        return ("dated_correct", f"labelled {year} on the same line")
    # the file itself is dated to the value's own year (e.g. a 2025 blog post): historical
    path_years = [int(y) for y in re.findall(r"(?<!\d)(20\d{2})(?!\d)", path)]
    if path_years and max(path_years) <= year and not any(y > year for y in years_line):
        return ("dated_correct", f"file is dated {max(path_years)}")
    if TEST_RX.search(path):
        return ("test_or_mock", "test, fixture or mock path")
    if any(y > year for y in years_near) or current_word:
        return ("presented_as_current", f"{c['meaning']} (valid to {c['valid_to']}) presented as current; now {repl}")
    if re.search(r"[=:]\s*['\"]?\$?\s*[\d,._]+\s*['\"]?\s*[,;)\]]?\s*(//.*|#.*)?$", line.strip()):
        return ("presented_as_current", f"unlabelled constant in code: {c['meaning']} (valid to {c['valid_to']}); now {repl}")
    # a dateless "label: value" statement of a superseded figure reads as the current value
    if len(line.strip()) <= 160 and any(k in low for k in c["keywords"]) and re.search(r"[:=]\s*\**\s*\$?\s?[\d][\d,.]*\s?%?", line) and not years_near:
        return ("presented_as_current", f"undated statement of {c['meaning']} (valid to {c['valid_to']}); now {repl}")
    return ("unresolved", "no year and no currency signal nearby")


def scan(root, constants, today, warn_days, exclude=()):
    import fnmatch
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(dp, f)
            if os.path.splitext(f)[1].lower() not in TEXT_EXT or os.path.getsize(p) > 2_000_000:
                continue
            try:
                lines = open(p, encoding="utf-8", errors="ignore").read().split("\n")
            except OSError:
                continue
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if any(fnmatch.fnmatch(rel, g) for g in exclude) or any("rulecheck:ignore-file" in l for l in lines[:40]):
                continue
            for c in constants:
                rx = needle(c)
                for i, line in enumerate(lines):
                    m = rx.search(line)
                    if not m or "rulecheck:ignore" in line:
                        continue
                    ctx = "\n".join(lines[max(0, i - 2): i + 3])
                    seg = line if len(line) <= 300 else line[max(0, m.start() - 140): m.end() + 140]
                    r = classify(seg, ctx if len(line) <= 300 else seg, c, rel, today)
                    if not r:
                        continue
                    cls, why = r
                    if cls == "expiring" and (datetime.date.fromisoformat(c["valid_to"]) - today).days > warn_days:
                        continue
                    out.append({"file": rel, "line": i + 1, "col": m.start() + 1, "class": cls, "value": m.group(0).strip(),
                                "meaning": c["meaning"], "why": why, "rule": c["rule"], "source": c["source"], "excerpt": seg.strip()[:200]})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--path", default=".")
    ap.add_argument("--constants", default=os.path.join(HERE, "constants.json"))
    ap.add_argument("--fail-on", default="stale", choices=["stale", "expiring", "never"])
    ap.add_argument("--warn-days", type=int, default=75)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD, for testing")
    ap.add_argument("--json", default=None, help="write findings to this file")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--exclude", default="", help="comma-separated glob patterns relative to --path")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    C = load_constants(a.constants)
    found = scan(a.path, C["constants"], today, a.warn_days, [g.strip() for g in a.exclude.split(",") if g.strip()])
    gha = os.environ.get("GITHUB_ACTIONS") == "true"
    sev = {"presented_as_current": "error", "role_misuse": "error", "expiring": "warning", "test_or_mock": "notice", "unresolved": "notice", "dated_correct": "notice"}
    shown = [f for f in found if f["class"] != "changelog" and (a.verbose or f["class"] != "dated_correct")]
    for f in shown:
        msg = f"{f['value']}: {f['why']}. Source: {f['source']} · table: https://financeratecalc.com/rules/index.json"
        if gha:
            print(f"::{sev[f['class']]} file={f['file']},line={f['line']},col={f['col']},title=Rule Watch: {f['class']}::{msg}")
        else:
            print(f"{f['file']}:{f['line']}: [{f['class']}] {msg}")
    counts = {}
    for f in found:
        counts[f["class"]] = counts.get(f["class"], 0) + 1
    stale = counts.get("presented_as_current", 0) + counts.get("role_misuse", 0)
    summary = (f"## FRC Rule Watch\n\nChecked against the dated table of {len(C['constants'])} US mortgage rule constants (as of {today}).\n\n"
               f"| class | count |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in sorted(counts.items())) +
               f"\n**Stale values used as current: {stale}.** Expiring soon: {counts.get('expiring', 0)}.\n\n"
               "Table and sources: https://financeratecalc.com/rules/index.json · corrections: https://financeratecalc.com/corrections.html\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8").write(summary)
    else:
        print("\n" + summary)
    if a.json:
        json.dump({"today": str(today), "counts": counts, "findings": found}, open(a.json, "w"), indent=1)
    if a.fail_on == "stale" and stale:
        sys.exit(1)
    if a.fail_on == "expiring" and (stale or counts.get("expiring")):
        sys.exit(1)


if __name__ == "__main__":
    main()
