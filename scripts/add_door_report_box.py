#!/usr/bin/env python3
"""Insert the Door Report box (free cohort table) on state and lender pages, before the
`.legal` footer line. Idempotent: an existing box is replaced. The box text is the same on
every page; the state link carries the page's state, the lender pages link to the report
without a state (the reader picks one)."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_receipts_on_pages import STATE_SLUGS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MARK = "<!-- door-report-box -->"


def box(state=None):
    state = state.upper() if state else None
    href = f"/door-report.html?state={state}" if state else "/door-report.html"
    where = f" in {state}" if state else ""
    return (f'{MARK}<div style="border:1px solid #23262e;border-radius:12px;padding:14px 18px;background:#0d0f14;margin:18px auto;max-width:860px;font-size:14.5px;color:#cbc7bb">'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:10.5px;letter-spacing:2px;color:#C8A84B;text-transform:uppercase;margin-bottom:6px">Door Report &middot; free</div>'
            f'<b style="color:#fff">Lender denial rates for borrowers like you{where}.</b> Pick loan size and purpose and see every lender with at least 100 decisions in that cohort, alphabetically, from the same federal record. '
            f'Historical observation; not a prediction about any application; not a recommendation; not evidence of misconduct. '
            f'<a href="{href}" style="color:#C8A84B">Open the cohort table &rarr;</a></div>{MARK}\n')


def patch(path, state=None):
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    html = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK) + r"\n?", "", html, flags=re.DOTALL)
    m = re.search(r'<div class="legal">', html)
    if not m:
        return False
    html = html[: m.start()] + box(state) + html[m.start():]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return True


def main():
    n = 0
    for fn in os.listdir(ROOT):
        if not fn.endswith(".html"):
            continue
        base = fn[:-5]
        if base.startswith("fha-denial-rates-") and STATE_SLUGS.get(base[len("fha-denial-rates-"):]):
            n += patch(os.path.join(ROOT, fn), STATE_SLUGS[base[len("fha-denial-rates-"):]])
        elif base.endswith("-fha-denial-rate"):
            n += patch(os.path.join(ROOT, fn))
    print("boxes placed:", n)


if __name__ == "__main__":
    main()
