#!/usr/bin/env python3
"""Phrasings the record cannot support, on our own pages. The claim contracts forbid turning an aggregate into a
statement about one application (association -> cause, observation -> prediction). This is the site-side twin of
the gate's sentence checks, kept deliberately short to avoid false alarms. Exit 1 on any hit.

    python3 scripts/check_page_phrasing.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERNS = [
    # one application tried at two lenders: HMDA has no such thing (found on 49 pages, 2026-10-31, via an Exa snippet)
    re.compile(r"\bthe same (FHA )?(application|applicant|borrower|file|buyer) (faces|would face|has|gets|sees)\b", re.I),
    re.compile(r"\byour (odds|chance|chances|probability) of (being )?(denied|denial|approval|approved) (is|are|will be)\b", re.I),
    re.compile(r"\b(will|would) (be )?(deny|denied|approve|approved) you\b", re.I),
]
SKIP = re.compile(r"^(eval|rulecheck|rl-env|scripts|fixtures|examples|readers|case-files|node_modules|packages)/")
# corrections.html quotes our own errors verbatim; that is its job (same exclusion as rulecheck)
SKIP_FILES = {"corrections.html"}


def main():
    hits = []
    for path in sorted(glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(path, ROOT)
        if SKIP.match(rel) or rel in SKIP_FILES:
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        for rx in PATTERNS:
            for m in rx.finditer(text):
                if "rulecheck:ignore" in text[max(0, m.start() - 200):m.start()]:
                    continue
                hits.append(f"{rel}: …{text[max(0, m.start() - 60):m.end() + 60].replace(chr(10), ' ')}…")
    for h in hits:
        print(h)
    print(f"phrasing hits: {len(hits)}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
