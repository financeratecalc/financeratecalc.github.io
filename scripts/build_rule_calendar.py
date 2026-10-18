#!/usr/bin/env python3
"""Rule expiry calendar: rules/rule-calendar.ics + rules/rule-calendar.json + rule-calendar.html.
Every date on which a US mortgage rule constant stops being valid, or on which its replacement is
expected, from the dated rule files. Subscribable (.ics), machine-readable (JSON), readable (HTML)."""
import datetime, glob, hashlib, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://financeratecalc.com"
today = datetime.date.today()
rules = {}
for f in sorted(glob.glob(os.path.join(ROOT, "rules", "*.json"))):
    if f.endswith("index.json"): continue
    r = json.load(open(f, encoding="utf-8")); rules[r["rule_id"]] = (r, os.path.basename(f))

def ev(date, title, rule_id, kind, detail, certainty):
    r, fn = rules[rule_id]
    return {"date": date, "title": title, "kind": kind, "certainty": certainty, "rule": rule_id, "rule_url": f"{SITE}/rules/{fn}",
            "detail": detail, "source": r.get("issuer_of_rule"), "verify": f"{SITE}/verify.html", "receipt_gate": "check_claim_contract (MCP) with passport_id " + rule_id}

E = []
# expiries from the rule files
for rid, (r, fn) in rules.items():
    if r.get("effective_to"):
        E.append(ev(r["effective_to"], f"Last valid day: {r['title']}", rid, "expiry",
                    f"Values in this table stop being valid after this date. Code and content that still carry them on the next day are stale. Rule Watch warns 75 days before.", "fixed by the rule"))
    else:
        E.append(ev(None, f"No scheduled end: {r['title']}", rid, "open-ended",
                    "In force since " + r["effective_from"] + " with no end date; changes only when the issuer publishes a new letter or the statute changes.", "open"))
# expected announcements (pattern of recent years; dated as expected, not promised)
E.append(ev("2026-11-24", "Expected: FHFA announces 2027 conforming loan limits", "frc:rule:fhfa-conforming-loan-limits-2026", "announcement",
            "FHFA announced the 2026 values on 2025-11-25 and the 2025 values on 2024-11-26; the last Tuesday of November is the pattern, not a commitment. When the release appears, the 2027 rule file is drafted the same day and published after a human check.", "expected (pattern of recent years)"))
E.append(ev("2026-12-10", "Expected: HUD Mortgagee Letter with 2027 FHA forward loan limits", "frc:rule:fha-forward-loan-limits-2026", "announcement",
            "HUD published ML 2025-23 (the 2026 limits) on 2025-12-11, about two weeks after FHFA. Expected, not promised.", "expected (pattern of recent years)"))
E.append(ev("2026-12-15", "Expected: CFPB publishes 2027 HOEPA and QM thresholds", "frc:rule:cfpb-hoepa-qm-thresholds-2026", "announcement",
            "The 2026 thresholds were published 2025-12-15 (90 FR). Expected, not promised.", "expected (pattern of recent years)"))
E.append(ev("2027-01-01", "2027 values take effect: FHA limits, conforming limits, HOEPA/QM thresholds", "frc:rule:fhfa-conforming-loan-limits-2026", "effective",
            "Every 2026 limit becomes a historical value. Anything that says 'the 2027 limit is $832,750' is wrong from this day. The public re-scan of stale constants runs on 2027-01-02 and is published as eval/stale-constants-scan-2027-01-02.json.", "fixed by the rule"))
E.append(ev("2027-01-02", "Pre-registered re-scan: how much public code still carries 2026 limits", "frc:rule:fhfa-conforming-loan-limits-2026", "measurement",
            "Pre-registered 2026-10-18. The same stale-constant scan that found 29 repositories with 2025 values in October 2026 runs on this date against the 2026 values, and its result is published unedited. Prediction: at least 20 public repositories will carry a 2026 limit as current on 2027-01-02.", "pre-registered"))
E = sorted(E, key=lambda e: (e["date"] or "9999", e["title"]))
pred = "Prediction (2026-10-18): on 2027-01-02 at least 20 public GitHub repositories will present a 2026 conforming or FHA limit as the current value."
out = {"generated": today.isoformat(), "purpose": "Every date on which a US mortgage rule constant stops being valid or its replacement is expected, from FinanceRateCalc's dated rule files. Subscribe: rule-calendar.ics. Not legal advice; expected dates are patterns of recent years, not commitments.",
       "preregistered_prediction": {"text": pred, "sha256": hashlib.sha256(pred.encode()).hexdigest(), "graded_on": "2027-01-02", "method": "scripts/stale_constant_scan.mjs with the 2026 values as the stale set"},
       "events": E, "license": "CC BY 4.0"}
json.dump(out, open(os.path.join(ROOT, "rules", "rule-calendar.json"), "w"), indent=1, ensure_ascii=False)

def ics_date(d): return d.replace("-", "")
def esc(s): return s.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")
lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FinanceRateCalc//US mortgage rule expiry calendar//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:US mortgage rule expiries (FinanceRateCalc)", "X-WR-CALDESC:When FHA and conforming loan limits\\, MIP and HOEPA/QM thresholds stop being valid\\, and when replacements are expected.", "REFRESH-INTERVAL;VALUE=DURATION:P1W"]
for e in E:
    if not e["date"]: continue
    uid = hashlib.sha1((e["date"] + e["title"]).encode()).hexdigest()[:16] + "@financeratecalc.com"
    lines += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{ics_date(today.isoformat())}T000000Z", f"DTSTART;VALUE=DATE:{ics_date(e['date'])}",
              f"SUMMARY:{esc(e['title'])}", f"DESCRIPTION:{esc(e['detail'] + ' Certainty: ' + e['certainty'] + '. Rule file: ' + e['rule_url'])}", f"URL:{e['rule_url']}", f"CATEGORIES:{e['kind']}"]
    if e["kind"] == "expiry":
        lines += ["BEGIN:VALARM", "TRIGGER:-P75D", "ACTION:DISPLAY", f"DESCRIPTION:{esc('75 days left: ' + e['title'])}", "END:VALARM"]
    lines += ["END:VEVENT"]
lines += ["END:VCALENDAR"]
open(os.path.join(ROOT, "rules", "rule-calendar.ics"), "w", encoding="utf-8", newline="\r\n").write("\r\n".join(lines) + "\r\n")

import html as H
rows = "".join(f"<tr><td data-l='Date'>{E_['date'] or 'open'}</td><td data-l='Event'><b>{H.escape(E_['title'])}</b><br><span class='meta'>{H.escape(E_['detail'])}</span></td><td data-l='Certainty'>{H.escape(E_['certainty'])}</td><td data-l='Rule'><a href='{E_['rule_url']}'>{E_['rule'].split(':')[-1]}</a></td></tr>" for E_ in E)
page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>US Mortgage Rule Expiry Calendar: When Loan Limits, MIP and QM Thresholds Change | FinanceRateCalc</title>
<meta name="description" content="Every date a US mortgage rule constant stops being valid or its replacement is expected: 2026 FHA and conforming loan limits end 31 December 2026; FHFA's 2027 announcement expected late November; HUD and CFPB in December. Subscribable .ics and JSON, with a pre-registered 2 January 2027 re-scan of public code.">
<link rel="canonical" href="{SITE}/rule-calendar.html"><link rel="alternate" type="text/calendar" href="{SITE}/rules/rule-calendar.ics"><link rel="alternate" type="application/json" href="{SITE}/rules/rule-calendar.json">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ND9P4F3PHT"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-ND9P4F3PHT');</script><script src="/assets/ai-referral.js?v=3" defer></script>
<script type="application/ld+json">{json.dumps([{"@context":"https://schema.org","@type":"Event","name":e["title"],"startDate":e["date"],"eventStatus":"https://schema.org/EventScheduled","description":e["detail"],"url":SITE+"/rule-calendar.html","organizer":{"@type":"Organization","name":"FinanceRateCalc"}} for e in E if e["date"]])}</script>
<style>:root{{--bg:#08090c;--fg:#e8e4da;--mut:#a5a094;--line:#23262e;--gold:#C8A84B}} body{{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:28px 16px 60px}} h1{{font-family:Georgia,serif;font-size:28px;line-height:1.2;margin:6px 0 12px}} h2{{font-family:Georgia,serif;font-size:19px;margin:28px 0 6px}} a{{color:var(--gold)}}
.kicker{{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--gold)}} .meta{{font-size:13px;color:var(--mut)}} .box{{border:1px solid var(--gold);border-radius:10px;padding:14px 16px;margin:18px 0;background:#0d0f14}}
table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}} th{{color:var(--mut)}} code{{background:#14161c;padding:1px 5px;border-radius:4px;font-size:12.5px}}
@media (max-width:640px){{table,thead,tbody,tr,td{{display:block;width:auto}} thead{{display:none}} tr{{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:10px 0}} td{{border:0;padding:2px 0}} td:before{{content:attr(data-l) ": ";color:var(--mut);font-weight:600}}}}</style></head><body><div class="wrap">
<div class="kicker">FinanceRateCalc · rule calendar · updated {today}</div>
<h1>When do US mortgage rule numbers stop being true?</h1>
<p>Loan limits, insurance premiums and lending thresholds carry dates. Code and content that hard-code them do not. This calendar lists every date on which a constant in our <a href="/rules/index.json">dated rule tables</a> stops being valid, and when its replacement is expected.</p>
<div class="box"><b>Subscribe:</b> <a href="/rules/rule-calendar.ics">rule-calendar.ics</a> (Google Calendar, Apple Calendar, Outlook: add by URL; each expiry carries a 75-day reminder) · <a href="/rules/rule-calendar.json">JSON</a> · check a codebase automatically: <a href="https://github.com/financeratecalc/financeratecalc.github.io/tree/main/rulecheck">FRC Rule Watch</a> (GitHub Action).</div>
<table><thead><tr><th>Date</th><th>Event</th><th>Certainty</th><th>Rule</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Pre-registered prediction</h2>
<p>{H.escape(pred)} Hash: <code>{out['preregistered_prediction']['sha256'][:16]}…</code>. Graded on 2027-01-02 by the same scan that, on 2026-10-18, found 29 public repositories presenting 2025 limits as current. The result is published unedited whether the prediction holds or not.</p>
<p class="meta">Expected announcement dates are the pattern of recent years, not commitments by any agency. Rule tables are transcribed by FinanceRateCalc from the public sources named in each file; not legal or underwriting advice; corrections at <a href="/corrections.html">corrections.html</a>. CC BY 4.0.</p>
</div></body></html>"""
open(os.path.join(ROOT, "rule-calendar.html"), "w", encoding="utf-8").write(page)
print(len(E), "events")
