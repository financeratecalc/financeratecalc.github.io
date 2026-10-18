"""Run: python3 rulecheck/tests/test_rulecheck.py — standard library only."""
import datetime, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); RC = os.path.join(HERE, "..", "rulecheck.py")
CASES = [  # (file content, today, expected class for the value, value)
  ("const CONFORMING_LIMIT = 806500;  // conforming loan limit", "2026-10-18", "presented_as_current", "806500"),
  ("The 2025 conforming loan limit was $806,500.", "2026-10-18", "dated_correct", "806,500"),
  ("FHA floor: $498,257 (2025)", "2026-10-18", "presented_as_current", "498,257"),
  ("The FHA loan limit is $726,200 in most counties.", "2026-10-18", "role_misuse", "726,200"),
  ("Loans at or below $726,200 pay 0.55% annual MIP.", "2026-10-18", None, "726,200"),
  ("2026 conforming loan limit: $832,750", "2026-10-18", "expiring", "832,750"),
  ("Current conforming loan limit: $832,750", "2027-01-02", "presented_as_current", "832,750"),
  ("The 2026 conforming loan limit was $832,750.", "2027-01-02", "dated_correct", "832,750"),
  ("Was $806,500 in 2025, now $832,750 (conforming loan limit).", "2026-10-18", "changelog", "806,500"),
  ("VA funding fee: 2.3% for first use", "2026-10-18", "presented_as_current", "2.3%"),
]
fails = 0
for i, (text, today, want, val) in enumerate(CASES):
    d = tempfile.mkdtemp(); open(os.path.join(d, "f.md"), "w").write(text + "\n")
    out = os.path.join(d, "o.json")
    subprocess.run([sys.executable, RC, "--path", d, "--today", today, "--fail-on", "never", "--json", out, "--warn-days", "120"], capture_output=True)
    got = [f["class"] for f in json.load(open(out))["findings"] if val.replace(",", "").replace("%", "") in f["value"].replace(",", "").replace("%", "").replace("$", "")]
    ok = (want is None and not any(g in ("presented_as_current", "role_misuse") for g in got)) or (want in got)
    fails += not ok
    print("PASS" if ok else "FAIL", i, want, got, "|", text)
print(len(CASES) - fails, "/", len(CASES)); sys.exit(1 if fails else 0)
