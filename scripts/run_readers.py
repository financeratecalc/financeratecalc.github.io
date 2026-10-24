#!/usr/bin/env python3
"""Print the prompt for a reading: one reader file + one page, in the fixed report format.
Usage: python3 scripts/run_readers.py --page index.html --readers 01,08,11
The prompts are handed to fresh agents that have not seen the project; results go to eval/readers/.
"""
import argparse, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser(); ap.add_argument("--page", required=True); ap.add_argument("--readers", default="all"); a = ap.parse_args()
files = sorted(glob.glob(os.path.join(ROOT, "readers", "[0-9][0-9]-*.md")))
if a.readers != "all":
    want = set(a.readers.split(",")); files = [f for f in files if os.path.basename(f)[:2] in want]
tmpl = open(os.path.join(ROOT, "readers", "_template.md")).read()
for f in files:
    print("=" * 80); print(f"READER {os.path.basename(f)} on {a.page}"); print("=" * 80)
    print(f"You are role-playing a specific first-time reader and must stay in that role. You have NO prior knowledge of this website or its author.\n\n{open(f).read()}\nThe site's static HTML is checked out at {ROOT}. Start at {a.page}; read visible text as a browser would show it (ignore scripts); follow the links this person would actually click; roughly 6-12 pages, proportionate to fifteen minutes.\n\nReport format:\n{tmpl}")
