#!/usr/bin/env python3
"""The 2027 Limit Race: which AI answer engine learns the new US loan limits first?

Ground truth changes on a known schedule (FHFA announces the 2027 conforming limits in late
November; they take effect 1 January). Every day this asks each reachable engine the same three
questions, one fresh call each, and grades the answers deterministically against the dated rule
files: no model grades a model. Before the announcement, the only correct answer is "not yet
announced" (or the 2026 value labelled as 2026); a 2027 figure given before FHFA publishes one is
a fabrication. After the announcement, the correct answer is the value in the 2027 rule file,
which is published with a receipt and its hash in the transparency log, so anyone can check that
the ground truth existed before an engine first served it.

Daily output: eval/race-2027/<date>.json. Leaderboard: race-2027.html (hours from the rule file's
publication to each engine's first correct answer). Cost: three short calls per engine per day.
"""
import datetime, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark_api_run import SYSTEMS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONS = [
    {"id": "conf2027", "q": "What is the 2027 conforming loan limit for a one-unit home in most of the US?", "rule": "fhfa-conforming-loan-limits-2027", "cell": "baseline", "value_2026": 832750, "key_2026": "2026 conforming baseline"},
    {"id": "fha2027", "q": "What is the 2027 FHA loan limit floor for a one-unit home in low-cost counties?", "rule": "fha-forward-loan-limits-2027", "cell": "floor", "value_2026": 541287, "key_2026": "2026 FHA floor"},
    {"id": "ceil2027", "q": "What is the 2027 FHA loan limit ceiling for a one-unit home in high-cost counties?", "rule": "fha-forward-loan-limits-2027", "cell": "ceiling", "value_2026": 1249125, "key_2026": "2026 FHA ceiling"},
]


def truth_for(q):
    """The 2027 rule file, if published, with the cell's value; else None (not yet announced)."""
    p = os.path.join(ROOT, "rules", q["rule"] + ".json")
    if not os.path.exists(p):
        return None
    r = json.load(open(p, encoding="utf-8"))
    for c in r.get("cells", []):
        area = (c.get("area") or "").lower()
        if q["cell"] == "baseline" and "baseline" in area and c.get("units", 1) == 1:
            return {"value": c["limit_usd"], "published": r.get("frc_published") or r.get("effective_from"), "rule_url": "https://financeratecalc.com/rules/" + q["rule"] + ".json"}
        if q["cell"] == "floor" and c.get("units", 1) == 1 and "floor_usd" in c:
            return {"value": c["floor_usd"], "published": r.get("frc_published") or r.get("effective_from"), "rule_url": "https://financeratecalc.com/rules/" + q["rule"] + ".json"}
        if q["cell"] == "ceiling" and c.get("units", 1) == 1 and "ceiling_usd" in c:
            return {"value": c["ceiling_usd"], "published": r.get("frc_published") or r.get("effective_from"), "rule_url": "https://financeratecalc.com/rules/" + q["rule"] + ".json"}
    return None


def dollars(text):
    return [int(x.replace(",", "")) for x in re.findall(r"\$\s?(\d{3}(?:,\d{3})+|\d{6,7})", text)]


def grade(text, q, truth):
    """Deterministic. Returns (grade, why). Grades: correct | not_yet_correct | stale_2026 | premature_number | wrong_number | no_number."""
    t = text.lower()
    nums = dollars(text)
    says_not_announced = bool(re.search(r"(not (yet )?(been )?(announced|published|released|set|available)|has not|hasn't|no official|not yet known|expected to be announced|will be announced|to be announced|unavailable)", t))
    if truth is None:
        if says_not_announced and q["value_2026"] in nums and re.search(r"\b2026\b", t):
            return ("not_yet_correct", "says the 2027 value is not announced and gives the 2026 value labelled 2026")
        if says_not_announced and not [n for n in nums if n != q["value_2026"]]:
            return ("not_yet_correct", "says the 2027 value is not announced")
        if q["value_2026"] in nums and re.search(r"\b2027\b[^.]{0,80}\$?\s?" + f"{q['value_2026']:,}", text):
            return ("stale_2026", "presents the 2026 value as the 2027 limit")
        if nums and any(n != q["value_2026"] for n in nums):
            return ("premature_number", "gives a 2027 figure before FHFA/HUD published one: " + ", ".join(f"${n:,}" for n in nums if n != q["value_2026"]))
        if q["value_2026"] in nums:
            return ("stale_2026", "gives the 2026 value without saying 2027 is unannounced")
        return ("no_number", "no figure and no statement that it is unannounced")
    v = truth["value"]
    if v in nums:
        return ("correct", f"gives ${v:,}")
    if q["value_2026"] in nums:
        return ("stale_2026", f"still gives the 2026 value ${q['value_2026']:,}; the 2027 value ${v:,} was published " + str(truth["published"]))
    if nums:
        return ("wrong_number", "gives " + ", ".join(f"${n:,}" for n in nums) + f"; correct ${v:,}")
    if says_not_announced:
        return ("stale_2026", f"says not announced; the 2027 value ${v:,} was published " + str(truth["published"]))
    return ("no_number", "no figure")


def main():
    today = datetime.date.today()
    start, end = datetime.date(2026, 11, 10), datetime.date(2027, 2, 15)
    if not (start <= today <= end) and "--force" not in sys.argv:
        print("outside the race window", start, end); return
    if os.environ.get("RACE_ENABLED") != "1" and "--force" not in sys.argv:
        print("RACE_ENABLED is not 1; not spending"); return
    out = {"date": today.isoformat(), "systems": {}, "truth": {q["id"]: truth_for(q) for q in QUESTIONS}}
    for name, env, make in SYSTEMS:
        k = os.environ.get(env)
        if not k:
            out["systems"][name] = {"skipped": env + " not set"}; continue
        try:
            model, ask = make(k)
        except Exception as e:
            out["systems"][name] = {"skipped": str(e)[:200]}; continue
        res = {"model": model, "answers": {}}
        for q in QUESTIONS:
            try:
                r = ask(q["q"]); g, why = grade(r.get("text", ""), q, out["truth"][q["id"]])
                res["answers"][q["id"]] = {"grade": g, "why": why, "text": r.get("text", "")[:1500], "citations": (r.get("citations") or [])[:8]}
            except Exception as e:
                res["answers"][q["id"]] = {"grade": "error", "why": str(e)[:300]}
            print(name, q["id"], res["answers"][q["id"]]["grade"], flush=True)
        out["systems"][name] = res
    os.makedirs(os.path.join(ROOT, "eval", "race-2027"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "eval", "race-2027", today.isoformat() + ".json"), "w"), indent=1, ensure_ascii=False)
    build_page()


def build_page():
    days = sorted(glob.glob(os.path.join(ROOT, "eval", "race-2027", "*.json")))
    rows = [json.load(open(d, encoding="utf-8")) for d in days]
    systems = sorted({s for r in rows for s in r["systems"] if "answers" in r["systems"][s]})
    truth_dates = {}
    for r in rows:
        for qid, t in (r.get("truth") or {}).items():
            if t and qid not in truth_dates:
                truth_dates[qid] = (t.get("published"), t.get("value"))
    first_correct = {}
    for r in rows:
        for s, v in r["systems"].items():
            for qid, a in (v.get("answers") or {}).items():
                if a.get("grade") == "correct" and (s, qid) not in first_correct:
                    first_correct[(s, qid)] = r["date"]
    import html as H
    def cell(r, s, qid):
        a = (r["systems"].get(s) or {}).get("answers", {}).get(qid)
        if not a: return "<td>—</td>"
        g = a["grade"]; mark = {"correct": "✓", "not_yet_correct": "✓", "stale_2026": "stale", "premature_number": "invented", "wrong_number": "wrong", "no_number": "none", "error": "err"}.get(g, g)
        return f"<td class='{g}' title='{H.escape(a.get('why',''))}'>{mark}</td>"
    head = "".join(f"<th>{H.escape(s)}</th>" for s in systems)
    body = ""
    for r in rows:
        for q in QUESTIONS:
            body += f"<tr><td>{r['date']}</td><td>{q['id']}</td>" + "".join(cell(r, s, q["id"]) for s in systems) + "</tr>"
    board = ""
    for q in QUESTIONS:
        pub, val = truth_dates.get(q["id"], (None, None))
        line = f"<p><b>{H.escape(q['q'])}</b><br>" + (f"2027 value published {pub}: ${val:,}. " if pub else "2027 value not yet published; the correct answer today is 'not yet announced'. ")
        for s in systems:
            fc = first_correct.get((s, q["id"]))
            if pub and fc:
                lag = (datetime.date.fromisoformat(fc) - datetime.date.fromisoformat(str(pub)[:10])).days
                line += f"{H.escape(s)}: first correct {fc} ({lag} days after publication) · "
            elif pub:
                line += f"{H.escape(s)}: not yet correct · "
        board += line + "</p>"
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>The 2027 Limit Race: Which AI Learns the New Loan Limits First? | FinanceRateCalc</title>
<meta name="description" content="Daily, deterministic test of AI answer engines on the 2027 US conforming and FHA loan limits: before the announcement the right answer is 'not yet announced'; after it, the published value. Graded against dated rule files, no model grades a model. Days from publication to each engine's first correct answer.">
<link rel="canonical" href="https://financeratecalc.com/race-2027.html">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ND9P4F3PHT"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-ND9P4F3PHT');</script><script src="/assets/ai-referral.js?v=3" defer></script>
<style>:root{{--bg:#08090c;--fg:#e8e4da;--mut:#a5a094;--line:#23262e;--gold:#C8A84B}} body{{background:var(--bg);color:var(--fg);font-family:system-ui,sans-serif;margin:0;line-height:1.6}} .wrap{{max-width:900px;margin:0 auto;padding:28px 16px 60px}}
h1{{font-family:Georgia,serif;font-size:28px;line-height:1.2}} a{{color:var(--gold)}} .kicker{{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--gold)}} .box{{border:1px solid var(--gold);border-radius:10px;padding:14px 16px;margin:18px 0;background:#0d0f14}}
table{{border-collapse:collapse;font-size:13px;width:100%;display:block;overflow-x:auto}} th,td{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}} th{{color:var(--mut)}}
td.correct,td.not_yet_correct{{color:#5fb4a2;font-weight:700}} td.stale_2026{{color:#e8845a}} td.premature_number,td.wrong_number{{color:#ff9b9b;font-weight:700}} .meta{{font-size:13px;color:var(--mut)}}</style></head><body><div class="wrap">
<div class="kicker">FinanceRateCalc · live measurement · {len(rows)} daily runs</div>
<h1>The 2027 limit race: which AI learns the new loan limits first?</h1>
<p>On a known date every US loan limit changes. This page asks each reachable AI engine the same three questions every day, one fresh call each, and grades the answer against our <a href="/rules/index.json">dated rule files</a> with fixed rules, no model in the loop. Before FHFA and HUD publish, the only correct answer is "not yet announced"; a 2027 figure given before then is invented. After publication, the correct answer is the published value, whose rule file carries a receipt and a transparency-log entry proving when it existed.</p>
<div class="box">{board or "<p>The race starts in mid-November 2026, when the 2027 announcements are expected (<a href='/rule-calendar.html'>rule calendar</a>).</p>"}</div>
<table><thead><tr><th>Date</th><th>Question</th>{head}</tr></thead><tbody>{body}</tbody></table>
<p class="meta">Engines are provider APIs with their own web search (not the consumer apps); conditions are labelled in each day's file under <a href="https://github.com/financeratecalc/financeratecalc.github.io/tree/main/eval/race-2027">eval/race-2027</a>. Raw answers kept verbatim. Grading rules: <a href="https://github.com/financeratecalc/financeratecalc.github.io/blob/main/scripts/limit_race.py">scripts/limit_race.py</a>. Companion: <a href="/correction-latency.html">correction latency</a> · <a href="/rule-calendar.html">rule calendar</a> · check your own code: <a href="https://github.com/financeratecalc/financeratecalc.github.io/tree/main/rulecheck">Rule Watch</a>. CC BY 4.0.</p>
</div></body></html>"""
    open(os.path.join(ROOT, "race-2027.html"), "w", encoding="utf-8").write(page)


if __name__ == "__main__":
    if "--page-only" in sys.argv:
        build_page()
    else:
        main()
