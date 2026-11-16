#!/usr/bin/env python3
"""Remove every sponsored, partner and affiliate element from the site (run 2026-11-16; kept as the record and as a check).

The site says it carries no ads and no affiliate links. Pages written before that rule still held partner links
(a property-tax appeal service, a funding-offer network, a legal-forms seller, a tax-filing service), the boxes built
around them, "may earn a commission" lines left behind where links had already been removed, and two routing links
("which lenders approve most", "apply to more than one"). This removes them from the root pages.

    python3 scripts/remove_affiliate.py            # rewrite
    python3 scripts/remove_affiliate.py --check    # fail if any of it is back
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
HOSTS = r"dpbolvw\.net|anrdoezrs\.net|jdoqocy\.com|tkqlhce\.com|kqzyfj\.com|ownwell\.com/partner"
ANCHOR = re.compile(r"<a\b[^>]*>.*?</a>", re.S)
LEFT = re.compile(r"earn a commission|Commission may be earned|Affiliate links?\b[^<]{0,40}(?:we may|\.)|#ad\b", re.I)
ROUTE = re.compile(r'\s*<a\b[^>]*href="/(?:fha-lenders-approval-rates|apply-to-multiple-mortgage-lenders)\.html"[^>]*>[^<]*(?:Which lenders approve most|Apply to more than one)[^<]*</a>')
SKIP = {"corrections.html", "affiliate-disclosure.html", "about.html"}
DIV = re.compile(r"<(/?)div\b[^>]*>")


def text(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def div_parent(s, pos):
    depth = 0
    for m in reversed(list(DIV.finditer(s[:pos]))):
        if m.group(1):
            depth += 1
        elif depth:
            depth -= 1
        else:
            d = 1
            for n in DIV.finditer(s[m.end():]):
                d += -1 if n.group(1) else 1
                if d == 0:
                    return m.start(), m.end() + n.end()
            return None
    return None


def is_sponsored(tag):
    head = tag[:tag.index(">") + 1]
    return bool(re.search(HOSTS, head)) or bool(re.search(r'rel="[^"]*sponsored', head) and re.search(r'href="https?://', head))


def strip_page(s):
    n = 0
    while True:   # 1. sponsored anchors, with the box built around them
        m = next((m for m in ANCHOR.finditer(s) if is_sponsored(m.group(0))), None)
        if not m:
            break
        a, b = m.start(), m.end()
        box = None
        sp = div_parent(s, a)
        for _ in range(4):   # widen to the promo box, never to a page section
            if not sp or len(text(s[sp[0]:sp[1]])) > 330:
                break
            box = sp
            sp = div_parent(s, sp[0])
        if box:
            a, b = box
        else:   # markup around it is unbalanced: take the anchor and the sibling lines that sell it
            while True:
                p = re.search(r"<div\b[^>]*>[^<]{0,400}</div>\s*(?:</div>\s*)?$", s[:a])
                if not p or not re.search(r"Ownwell|Property Tax|Sponsored|Overpaying", p.group(0)):
                    break
                a = p.start()
        s = s[:a] + s[b:]
        n += 1
    while True:   # 2. disclosure lines left behind
        m = LEFT.search(s)
        if not m:
            break
        st = max(s.rfind("<p", 0, m.start()), s.rfind("<div", 0, m.start()), s.rfind("<span", 0, m.start()), s.rfind("<small", 0, m.start()))
        tag = re.match(r"<(\w+)", s[st:]).group(1)
        en = s.find(f"</{tag}>", m.end())
        if st < 0 or en < 0 or len(text(s[st:en])) > 260:
            a2 = s.rfind(">", 0, m.start()) + 1
            b2 = s.find("<", m.end())
            s = s[:a2] + s[b2:]
        else:
            s = s[:st] + s[en + len(tag) + 3:]
        n += 1
    s, k = ROUTE.subn("", s)   # 3. routing links
    return s, n + k


def remaining(s):
    out = []
    if any(is_sponsored(m.group(0)) for m in ANCHOR.finditer(s)):
        out.append("sponsored link")
    if LEFT.search(s):
        out.append("commission line")
    if ROUTE.search(s):
        out.append("routing link")
    return out


def main():
    pages = [f for f in sorted(glob.glob("**/*.html", recursive=True)) if f not in SKIP and not f.startswith((".venv/", "node_modules/", "packages/"))]
    if "--check" in sys.argv:
        bad = [(f, r) for f in pages for r in [remaining(open(f, encoding="utf-8", errors="ignore").read())] if r]
        print("affiliate and routing elements:", "none" if not bad else f"{len(bad)} pages, e.g. {bad[:4]}")
        sys.exit(1 if bad else 0)
    changed = removed = 0
    for f in pages:
        s = open(f, encoding="utf-8", errors="ignore").read()
        t, n = strip_page(s)
        if t != s:
            open(f, "w", encoding="utf-8").write(t)
            changed += 1; removed += n
    print("pages changed:", changed, "| elements removed:", removed)


if __name__ == "__main__":
    main()
