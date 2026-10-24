#!/usr/bin/env python3
"""Every page gets a way home. Found 2026-10-24: 265 pages (227 indexable) had no link to the home page at all.
Adds one small <nav> right after <body> on any page that carries no link to "/" - idempotent (marker data-frc-nav)."""
import glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAV = ('<nav data-frc-nav="1" aria-label="Site" style="font-family:system-ui,sans-serif;font-size:12.5px;padding:8px 16px;background:#0b0d12;border-bottom:1px solid rgba(255,255,255,.08);display:flex;gap:14px;flex-wrap:wrap;align-items:center">'
       '<a href="/" style="color:#C8A84B;font-weight:700;text-decoration:none">FinanceRateCalc</a>'
       '<a href="/fha-denial-rates-top-100.html" style="color:rgba(255,255,255,.7);text-decoration:none">Lenders</a>'
       '<a href="/fha-denial-rates-by-state.html" style="color:rgba(255,255,255,.7);text-decoration:none">States</a>'
       '<a href="/metro-gaps.html" style="color:rgba(255,255,255,.7);text-decoration:none">Metros</a>'
       '<a href="/check-answer.html" style="color:rgba(255,255,255,.7);text-decoration:none">Check an answer</a>'
       '<a href="/corrections.html" style="color:rgba(255,255,255,.7);text-decoration:none">Corrections</a>'
       '<a href="/about.html" style="color:rgba(255,255,255,.7);text-decoration:none">About</a></nav>\n')
HOME = re.compile(r'href="(/|/index\.html|index\.html|https://financeratecalc\.com/?)"')
n = 0
for f in glob.glob(os.path.join(ROOT, "*.html")) + glob.glob(os.path.join(ROOT, "*", "*.html")):
    rel = os.path.relpath(f, ROOT)
    if rel.startswith(("eval/", "fixtures/", "examples/", "rl-env/", "readers/")) or rel == "404.html":
        continue
    s = open(f, encoding="utf-8", errors="ignore").read()
    if "data-frc-nav" in s or HOME.search(s) or 'content="0;url=' in s[:600]:
        continue
    m = re.search(r"<body[^>]*>", s)
    if not m:
        continue
    s = s[:m.end()] + "\n" + NAV + s[m.end():]
    open(f, "w", encoding="utf-8").write(s); n += 1
print("nav added to", n, "pages")
