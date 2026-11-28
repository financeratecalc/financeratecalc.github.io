#!/usr/bin/env python3
"""Calendar watchdog. For every expected announcement in rules/rule-calendar.json whose date is more than GRACE days
past, the next year's rule file must exist, or rules/awaiting.json must record a check, made in the last 7 days, that
the issuer has not published yet. Otherwise this fails.

Added 2026-11-28: FHFA announced the 2027 conforming limits on 2026-11-24, the calendar had the date, and the rule
file was published only on 2026-11-28, because nothing checked the date when it passed.

    python3 scripts/check_rule_calendar_due.py
"""
import datetime, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRACE, ACK_DAYS = 2, 7
today = datetime.date.today()
cal = json.load(open(os.path.join(ROOT, "rules", "rule-calendar.json"), encoding="utf-8"))
ap = os.path.join(ROOT, "rules", "awaiting.json")
acks = json.load(open(ap, encoding="utf-8")).get("checks", []) if os.path.exists(ap) else []
bad, ok = [], []
for e in cal["events"]:
    if e.get("kind") != "announcement" or not e.get("date"):
        continue
    due = datetime.date.fromisoformat(e["date"]) + datetime.timedelta(days=GRACE)
    m = re.match(r"frc:rule:(.+)-(\d{4})$", e["rule"])
    if not m:
        continue
    successor = f"{m.group(1)}-{int(m.group(2)) + 1}"
    if today < due:
        ok.append(f"not due: {successor} (expected {e['date']})"); continue
    if os.path.exists(os.path.join(ROOT, "rules", successor + ".json")):
        ok.append(f"published: {successor}"); continue
    recent = [a for a in acks if a.get("successor") == successor and (today - datetime.date.fromisoformat(a["checked"])).days <= ACK_DAYS]
    if recent:
        ok.append(f"awaiting issuer: {successor} (checked {recent[-1]['checked']}: {recent[-1]['finding']})"); continue
    bad.append(f"{successor}: expected {e['date']}, no rule file and no check in the last {ACK_DAYS} days. "
               f"Either the issuer has published (write rules/{successor}.json) or record in rules/awaiting.json that it has not.")
for x in ok:
    print("ok  ", x)
for x in bad:
    print("DUE ", x)
sys.exit(1 if bad else 0)
