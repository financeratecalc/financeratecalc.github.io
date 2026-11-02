#!/usr/bin/env python3
"""qualifier-survival.html from eval/qsi/qsi.json. Generated; `--check` exits 1 if the committed page differs."""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "qualifier-survival.html")
d = json.load(open(os.path.join(ROOT, "eval", "qsi", "qsi.json"), encoding="utf-8"))
Q = ["value", "period", "population", "program", "universe", "no_drift", "attribution"]
QL = {"value": "current value", "period": "period (2025)", "population": "denominator named", "program": "program (FHA)", "universe": "universe (HECM out / top-100 scope)", "no_drift": "no causal, second-person, advice or legal drift", "attribution": "source named"}


def short(e):
    e = e.lower()
    for k, v in (("perplexity", "Perplexity"), ("chatgpt", "ChatGPT"), ("openai", "ChatGPT"), ("deepseek", "DeepSeek"), ("gemini", "Gemini"), ("unknown", "Engine 4 (unconfirmed)")):
        if k in e:
            return v
    return e[:24]


rows = "".join(
    f'<tr><td>{r["date"]}</td><td>{html.escape(short(r["engine"]))}</td><td class=n><b>{r["qsi"]:.2f}</b></td>'
    + "".join(f'<td class="{"ok" if r["survived"][q] else "no"}">{"✓" if r["survived"][q] else "✗"}</td>' for q in Q)
    + f'<td class="small">{html.escape(", ".join(r["superseded_values_quoted"]) or "")}{(" · " if r["superseded_values_quoted"] and r["drift_phrases"] else "")}{html.escape("; ".join(r["drift_phrases"]))}</td>'
    + f'<td class="small"><a href="/{r["log"]}">text</a></td></tr>'
    for r in sorted(d["rows"], key=lambda r: (r["date"], r["engine"])))
surv = "".join(f'<tr><td>{QL[q]}</td><td class=n>{d["qualifier_survival_rates"].get(q, 0) * 100:.0f}%</td></tr>' for q in Q)
eng = "".join(f'<tr><td>{html.escape(short(e))}</td><td class=n>{v["answers"]}</td><td class=n><b>{v["qsi"]:.2f}</b></td></tr>' for e, v in sorted(d["by_engine"].items(), key=lambda x: -x[1]["qsi"]))

page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Qualifier Survival Index: what survives when an AI restates a statistic | FinanceRateCalc</title>
<meta name="description" content="A hallucination rate asks whether the number is right. The Qualifier Survival Index asks whether the sentence is: of seven things that belong next to a published figure (current value, period, denominator, program, universe, no causal or second-person drift, source), how many survive when an answer engine restates it. Baseline {d['generated'][:10]}: QSI {d['qsi_mean']:.2f} over {d['answers_graded']} answers; every graded answer archived verbatim; grader public.">
<link rel="canonical" href="https://financeratecalc.com/qualifier-survival.html">
<style>body{{background:#08090c;color:#e8e4da;font-family:'DM Sans',system-ui,sans-serif;margin:0;line-height:1.6}}.wrap{{max-width:1000px;margin:0 auto;padding:36px 18px 70px}}h1{{font-family:Georgia,serif;font-size:27px;color:#f5f2ea;line-height:1.25}}h2{{font-family:Georgia,serif;font-size:19px;color:#f5f2ea;margin-top:28px}}.kicker{{font-family:monospace;font-size:11px;letter-spacing:2px;color:#C8A84B;text-transform:uppercase}}a{{color:#C8A84B}}table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}th,td{{padding:6px 8px;border-bottom:1px solid rgba(255,255,255,.08);text-align:left;vertical-align:top}}th{{color:rgba(255,255,255,.6);font-weight:600;font-size:12px}}td.n{{font-family:monospace;text-align:right}}td.ok{{color:#7ed29a;text-align:center}}td.no{{color:#e07a7a;text-align:center}}.big{{font-family:monospace;font-size:40px;color:#f5f2ea;line-height:1}}.card{{border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:16px 18px;margin:14px 0;background:#0b0d12}}.small{{font-size:12.5px;opacity:.75}}code{{font-family:monospace;font-size:12.5px}}</style></head>
<body>
<nav data-frc-nav="1" aria-label="Site" style="font-family:system-ui,sans-serif;font-size:12.5px;padding:8px 16px;background:#0b0d12;border-bottom:1px solid rgba(255,255,255,.08);display:flex;gap:14px;flex-wrap:wrap;align-items:center"><a href="/" style="color:#C8A84B;font-weight:700;text-decoration:none">FinanceRateCalc</a><a href="/benchmark-scorecard.html" style="color:rgba(255,255,255,.7);text-decoration:none">Benchmark</a><a href="/why-fha-denial-rates-differ.html" style="color:rgba(255,255,255,.7);text-decoration:none">Why rates differ</a><a href="/corrections.html" style="color:rgba(255,255,255,.7);text-decoration:none">Corrections</a><a href="/site-index.html" style="color:rgba(255,255,255,.7);text-decoration:none">Index</a></nav>
<div class="wrap">
<div class="kicker">FinanceRateCalc &middot; measurement &middot; first published 2026-11-03 &middot; rebuilt {d['generated'][:10]}</div>
<h1>Qualifier Survival Index: what survives when an AI restates a statistic</h1>
<p><b>Short answer.</b> A hallucination rate asks whether the number is right. This index asks whether the sentence is. When an answer engine quotes a figure from this site, seven things belong next to the number: the current value, the period, the denominator, the program, the universe, the absence of causal or second-person or advice or legal wording, and the source. QSI is the share of those seven that survive. Over {d['answers_graded']} archived answers from {len(d['by_engine'])} engines, the baseline is <b>{d['qsi_mean']:.2f}</b>. Every answer is archived verbatim and the grader is a public script with fixed patterns and no model, so a score can be re-read and disputed.</p>
<div class="card"><div class="small">QSI, baseline</div><div class="big">{d['qsi_mean']:.2f}</div><div class="small">{d['answers_graded']} answers &middot; {len(d['by_engine'])} engines &middot; instrument of 3 questions &middot; 7 qualifiers each</div></div>
<h2>What survives, what dies</h2>
<table><thead><tr><th>Qualifier</th><th>Survival rate</th></tr></thead><tbody>{surv}</tbody></table>
<p>The pattern of the first week is the one the <a href="/benchmark-scorecard.html">fidelity benchmark</a> has shown since July: period, program and denominator survive; the value is where answers fail &mdash; and in every case so far the superseded value came from a document this site had published (a stale hub page, fixed the same evening; a working paper carrying pre-correction ground truths). The engines did not invent numbers; they found old ones.</p>
<h2>By engine</h2>
<table><thead><tr><th>Engine</th><th>Answers</th><th>QSI</th></tr></thead><tbody>{eng}</tbody></table>
<h2>Every graded answer</h2>
<table><thead><tr><th>Date</th><th>Engine</th><th>QSI</th><th>value</th><th>period</th><th>denom.</th><th>FHA</th><th>universe</th><th>no drift</th><th>source</th><th>What failed</th><th>Archive</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Instrument</h2>
<ol>{"".join(f"<li>{html.escape(q)}</li>" for q in d['instrument'])}</ol>
<p class="small">The three questions are asked in English, one per request, with no system prompt and no mention of this site. The first week's answers were obtained by the site owner from his own accounts and pasted; from December the API engines are asked by <code>scripts/qsi_collect.py</code> on the first of each month (Perplexity, OpenAI, Gemini; under one dollar a run), graded by <code>scripts/qualifier_survival.py</code>, and appended here. Engines without an API are added by hand when asked.</p>
<h2>Caveats</h2>
<ul class="small">{"".join(f"<li>{html.escape(c)}</li>" for c in d['caveats'])}</ul>
<p class="small">Data: <a href="/eval/qsi/qsi.json">eval/qsi/qsi.json</a> &middot; answers: <a href="/eval/answer-engine-log/">eval/answer-engine-log/</a> &middot; grader: <a href="https://github.com/financeratecalc/financeratecalc.github.io/blob/main/scripts/qualifier_survival.py">scripts/qualifier_survival.py</a>. Nothing on this page is advice about any loan; the figures the engines restate are historical aggregates from the public CFPB HMDA 2025 record. CC BY 4.0.</p>
</div>
</body></html>
'''
if "--check" in sys.argv:
    cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
    print("qsi page:", "current" if cur == page else "STALE"); sys.exit(0 if cur == page else 1)
open(OUT, "w", encoding="utf-8").write(page)
print("wrote qualifier-survival.html")
