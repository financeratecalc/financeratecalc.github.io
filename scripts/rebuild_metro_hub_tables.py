#!/usr/bin/env python3
"""Rebuild the figure-bearing parts of fha-denial-rates-by-metro.html from _data/metro_fha_2025.json.

Why this exists: the hub page was built on 2026-07-22, four days before the HECM correction
(2026-07-26). The correction updated the data file and the intro sentence, but the extremes
lists and the 60-row table kept pre-correction figures until the evidence-footnote audit of
2026-10-14 found them. This script makes the data file the only source for those sections, so
the page cannot drift from it again. Idempotent; run after any metro data rebuild.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "fha-denial-rates-by-metro.html")
D = json.load(open(os.path.join(ROOT, "_data", "metro_fha_2025.json"), encoding="utf-8"))
ROWS = D["rows"]
SLUGS = {}
for f in os.listdir(os.path.join(ROOT, "api", "metro")):
    m = json.load(open(os.path.join(ROOT, "api", "metro", f), encoding="utf-8"))
    SLUGS[m["metro"]] = m["slug"]


def pct(x):
    return f"{x:.1f}%"


def li(r, txt):
    return f"<li><b>{r['name']}</b> &mdash; {txt}</li>"


def main():
    s = open(PAGE, encoding="utf-8").read()
    n = len(ROWS)
    big = [r for r in ROWS if r["apps"] >= 1000]
    hard = sorted(big, key=lambda r: -r["denials"] / r["apps"])[:5]
    soft = sorted(big, key=lambda r: r["denials"] / r["apps"])[:5]
    pen = sorted([r for r in ROWS if r.get("penalty")], key=lambda r: -r["penalty"])[:5]
    lists = (
        '<p><b style="color:#e8845a;">Hardest five:</b></p><ul>' + "".join(li(r, f"{pct(r['denial_rate_pct'])} ({r['apps']:,} apps)") for r in hard) + "</ul>\n"
        '<p><b style="color:#22c55e;">Softest five:</b></p><ul>' + "".join(li(r, f"{pct(r['denial_rate_pct'])} ({r['apps']:,} apps)") for r in soft) + "</ul>\n"
        '<p><b style="color:#e8845a;">Biggest small-loan penalties:</b></p><ul>' + "".join(
            li(r, f"{r['penalty']:.2f}&times; (small {pct(r['small_denial_pct'])} vs large {pct(r['big_denial_pct'])})") for r in pen) + "</ul>\n"
    )
    s, k = re.subn(r'<p><b style="color:#e8845a;">Hardest five:</b></p><ul>.*?</ul>\n<p><b style="color:#22c55e;">Softest five:</b></p><ul>.*?</ul>\n<p><b style="color:#e8845a;">Biggest small-loan penalties:</b></p><ul>.*?</ul>\n',
                   lambda _: lists, s, flags=re.S)
    assert k == 1, "extremes block not found"

    top = sorted(ROWS, key=lambda r: -r["apps"])[:60]
    trs = []
    for r in top:
        slug = SLUGS.get(r["name"])
        name = (f"<a href='/metro/{slug}.html' style='color:inherit;text-decoration:none;border-bottom:1px dotted rgba(200,168,75,.4);'>{r['name']}</a>"
                if slug and os.path.exists(os.path.join(ROOT, "metro", slug + ".html")) else r["name"])
        small = pct(r["small_denial_pct"]) if r.get("small_denial_pct") is not None else "&mdash;"
        p = f"{r['penalty']:.2f}&times;" if r.get("penalty") else "&mdash;"
        hot = ' style="color:#e8845a;font-weight:700;"' if r.get("penalty") and r["penalty"] >= 2.5 else ""
        trs.append(f"<tr><td>{name}</td><td class='mono'>{r['apps']:,}</td><td class='mono'>{pct(r['denial_rate_pct'])}</td><td class='mono'{hot}>{small}</td><td class='mono'{hot}>{p}</td></tr>")
    head = "<tr><th>Metro / division</th><th>Decisioned apps</th><th>Denial rate</th><th>Small-loan denial</th><th>Small-loan penalty</th></tr>\n"
    s, k = re.subn(r"(<h2>The 60 largest FHA metros</h2>\s*<table>\s*)" + re.escape(head) + r"(?:<tr[^>]*>.*?</tr>\s*)+", lambda m: m.group(1) + head + "\n".join(trs) + "\n", s, flags=re.S)
    assert k == 1, "table not found"

    ep = next(r for r in ROWS if r["name"] == "El Paso, TX")
    s, k = re.subn(r"was denied (<b[^>]*>)?[0-9.]+&times;(</b>)? as often as a large one \([0-9.]+% vs [0-9.]+%\)",
                   lambda m: f"was denied {m.group(1) or ''}{ep['penalty']:.2f}&times;{m.group(2) or ''} as often as a large one ({pct(ep['small_denial_pct'])} vs {pct(ep['big_denial_pct'])})", s)
    assert k == 1, "El Paso sentence not found"
    s = re.sub(r"Among the \d+ metros with at least 1,000", f"Among the {len(big)} metros with at least 1,000", s)
    open(PAGE, "w", encoding="utf-8").write(s)
    print(f"{n} metros, {len(big)} with 1,000+; hardest {hard[0]['name']} {hard[0]['denial_rate_pct']}; softest {soft[0]['name']} {soft[0]['denial_rate_pct']}; table 60 rows")


if __name__ == "__main__":
    main()
