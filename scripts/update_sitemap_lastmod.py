#!/usr/bin/env python3
"""Set every sitemap <lastmod> to the date the page's file last changed in git, and drop
duplicate <loc> entries. Crawlers use lastmod to decide what to re-fetch; a corrections log
whose lastmod says July is a log nobody re-reads. Run after any content change."""
import glob, os, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://financeratecalc.com/"
def file_for(loc):
    p = loc[len(BASE):] if loc.startswith(BASE) else None
    if p is None: return None
    if p == "" or p.endswith("/"): p += "index.html"
    f = os.path.join(ROOT, p)
    return f if os.path.exists(f) else None
dates = {}
def last_change(f):
    if f not in dates:
        out = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%cs", "--", os.path.relpath(f, ROOT)], capture_output=True, text=True).stdout.strip()
        dates[f] = out or None
    return dates[f]
changed = 0
for sm in sorted(glob.glob(os.path.join(ROOT, "sitemap*.xml"))):
    s = open(sm, encoding="utf-8").read()
    seen = set()
    def fix(m):
        global changed
        block = m.group(0); loc = re.search(r"<loc>(.*?)</loc>", block).group(1)
        if loc in seen:
            changed += 1; return ""
        seen.add(loc)
        f = file_for(loc); d = last_change(f) if f else None
        if not d or "<lastmod>" not in block: return block
        new = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{d}</lastmod>", block)
        if new != block: changed += 1
        return new
    s2 = re.sub(r"<url>.*?</url>\n?", fix, s, flags=re.S)
    if s2 != s: open(sm, "w", encoding="utf-8").write(s2)
print("entries changed or deduplicated:", changed)
