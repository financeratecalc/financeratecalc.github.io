#!/usr/bin/env python3
"""Build correction-latency.html from eval/correction-latency.json. Rerun after every new observation."""
import html, json, os, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
c = json.load(open(os.path.join(ROOT, "eval", "correction-latency.json"), encoding="utf-8"))
E = html.escape
def status(o):
    st = o.get("status") or ""
    codes = o.get("codes") or []
    note = (o.get("note") or "").lower()
    if st in ("not_reached", "stale_publisher_copy") or "STALE" in " ".join(codes) or "TEMPORAL_DRIFT" in codes or "served the old value" in note:
        return "old"
    if "corrected value" in note or "described the correction" in note:
        return "new"
    return "mixed"
rows = []
n_obs = n_old = n_pub = 0
for x in c["corrections"]:
    obs = x.get("observations", [])
    trs = []
    for o in obs:
        n_obs += 1
        s = status(o)
        n_old += s == "old"
        pub = "publisher" in (o.get("note") or "").lower() or o.get("status") == "stale_publisher_copy" or "our own stale" in (o.get("note") or "").lower() or "stat page itself" in (x.get("corrected_on") or "")
        n_pub += bool(pub and s == "old")
        label = {"old": "served the old version", "new": "served the corrected version", "mixed": "mixed / see note"}[s]
        if o.get("adjudication_2026_10_14"):
            label = "void (our grading error)"
        trs.append(f"<tr><td data-l='Observed'>{E(str(o.get('observed','')))[:16]}</td><td data-l='System'>{E(o.get('system',''))}</td><td data-l='Condition'>{E(o.get('condition',''))}</td><td data-l='Result' class='{s}'>{E(label)}</td><td data-l='Note' class='note'>{E(o.get('adjudication_2026_10_14') or o.get('note',''))}</td></tr>")
    rows.append(f"""<section><h2>{E(x['figure'])}</h2>
<p class="meta">Corrected on <b>{E(x['corrected_on'])}</b> · old: {E(x['old'])} · new: {E(x['new'])} · <a href="{E(x.get('log','/corrections.html'))}">log entry</a></p>
<table><thead><tr><th>Observed</th><th>System</th><th>Condition</th><th>Result</th><th>Note</th></tr></thead><tbody>{''.join(trs)}</tbody></table></section>""")
today = datetime.date.today().isoformat()
page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Correction Latency: How Long AI Answers Keep a Corrected Figure | FinanceRateCalc</title>
<meta name="description" content="When a publisher corrects a figure, how long do AI answer engines keep serving the old one? Dated observations of ChatGPT, Perplexity, Claude, Gemini, Copilot, DeepSeek and Meta AI against this publisher's own corrections log, with the finding that most of the delay sat on the publisher's side.">
<link rel="canonical" href="https://financeratecalc.com/correction-latency.html">
<link rel="alternate" type="application/json" href="https://financeratecalc.com/eval/correction-latency.json">
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ND9P4F3PHT"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-ND9P4F3PHT');</script>
<script src="/assets/ai-referral.js?v=3" defer></script>
<script type="application/ld+json">{json.dumps({"@context":"https://schema.org","@type":"Dataset","name":"Correction latency of AI answer engines","description":c["purpose"],"url":"https://financeratecalc.com/correction-latency.html","dateModified":today,"license":"https://creativecommons.org/licenses/by/4.0/","creator":{"@type":"Organization","name":"FinanceRateCalc","url":"https://financeratecalc.com"},"distribution":[{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":"https://financeratecalc.com/eval/correction-latency.json"}],"measurementTechnique":c["method"]})}</script>
<style>
:root{{--bg:#08090c;--fg:#e8e4da;--mut:#a5a094;--line:#23262e;--gold:#C8A84B;--old:#e8845a;--new:#5fb4a2}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:0;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:28px 16px 60px}} h1{{font-family:Georgia,serif;font-size:28px;line-height:1.2;margin:6px 0 12px}}
h2{{font-family:Georgia,serif;font-size:19px;margin:30px 0 6px}} a{{color:var(--gold)}} .kicker{{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--gold)}}
.lead{{font-size:16px;color:#d6d2c6}} .meta{{font-size:13px;color:var(--mut)}} .box{{border:1px solid var(--gold);border-radius:10px;padding:14px 16px;margin:18px 0;background:#0d0f14}}
table{{width:100%;border-collapse:collapse;font-size:13px;display:block;overflow-x:auto}} th,td{{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}}
th{{color:var(--mut);font-weight:600}} td.old{{color:var(--old);font-weight:600;white-space:nowrap}} td.new{{color:var(--new);font-weight:600;white-space:nowrap}} td.mixed{{white-space:nowrap}}
code{{font-size:12.5px;background:#14161c;padding:1px 5px;border-radius:4px}} @media (max-width:640px){{table,thead,tbody,tr,td{{display:block;width:auto}} thead{{display:none}} tr{{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:10px 0}} td{{border:0;padding:2px 0}} td:before{{content:attr(data-l) ": ";color:var(--mut);font-weight:600}} td.note:before{{content:""}} td.note{{margin-top:4px;color:#cbc7bb}}}}
pre{{white-space:pre-wrap;background:#14161c;padding:12px;border-radius:8px;font-size:13px}}
</style></head><body><div class="wrap">
<div class="kicker">FinanceRateCalc · measurement · updated {today}</div>
<h1>When a publisher corrects a figure, how long do AI answers keep the old one?</h1>
<p class="lead">This page tracks one publisher's corrections, dated in a public log, against what AI answer engines say afterwards. Every row is a single dated probe of a single system. Nothing is averaged across systems.</p>
<div class="box"><b>What the record shows so far ({n_obs} observations, 3 corrections).</b> In {n_old} observations the system served the old version. In {n_pub} of those, the old version demonstrably came from <i>our</i> pages, not from the model: a page we had not yet regenerated, a sitemap that still told crawlers the corrections log had not changed since July, or an atom on our own log that contradicted another. For the other {n_old - n_pub} we cannot tell whether the delay was the model, its search index or a page of ours. A correction is not finished when the log entry is written; it is finished when every copy the engines read says the same thing. Two of the corrections below are our own errors, logged with the same severity.</div>
{''.join(rows)}
<h2>Run the probe yourself</h2>
<p>Ask any AI assistant, in a fresh session with no follow-up:</p>
<pre>Has FinanceRateCalc ever corrected or retracted any of its published findings? Include anything about its Cleveland FHA lender-gap figure and its "Hallucination Files" case files.</pre>
<p>The current answer, with dates: the 26 July 2026 universe correction (national rate 21.7% → 22.1%; Cleveland gap 73.8 → 73.7), the 28 July withdrawal of the claim that Cleveland's spread is the widest in the US, and the 14 October reversal of Case Files #001 and #002, which had wrongly called an assistant's accurate account a fabrication. Source of record: <a href="/corrections.html">corrections log</a> · <a href="/corrections.json">corrections.json</a>.</p>
<h2>Method</h2>
<p class="meta">{E(c['method'])} Conditions differ (clean consumer sessions, batched sessions, API with web search) and are labelled per row. Data: <a href="/eval/correction-latency.json">eval/correction-latency.json</a> (CC BY 4.0).</p>
</div></body></html>
"""
open(os.path.join(ROOT, "correction-latency.html"), "w", encoding="utf-8").write(page)
print("observations", n_obs, "old", n_old, "publisher-side", n_pub)
