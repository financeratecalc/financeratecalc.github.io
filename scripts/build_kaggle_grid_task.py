#!/usr/bin/env python3
"""Writes integrations/kaggle/denominator_grid_task.py: the hard version of the denominator task for Kaggle Benchmarks.

The first task (denominator_reasoning_task.py) was solved 40/40 by a small model, so it separates nothing. This one is
the job the site's denominator map does on real reports: a table of applications by loan purpose (3) and outcome (5),
one reported denial rate, and the question "which cell produced it?". 105 candidate cells (7 purpose sets x 15 outcome
sets containing denials); the generator keeps an item only when exactly one cell reproduces the figure and every other
cell is at least 0.15 points away. A quarter of the items carry a figure that no cell reproduces (the right answer is
NONE), which is what happened with two widely quoted real figures. Counts are invented; truth is by construction.

    python3 scripts/build_kaggle_grid_task.py            # writes the task file
    python3 scripts/build_kaggle_grid_task.py --check    # brute-force solver must score 1.0, a fixed guess must not
"""
import itertools
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PURPOSES = ["purchase", "refinance", "cash-out refinance"]
OUT = ["originated", "approved but not accepted", "denied", "withdrawn", "closed for incompleteness"]
OTHERS = [o for o in OUT if o != "denied"]
P_SETS = [list(c) for n in (1, 2, 3) for c in itertools.combinations(PURPOSES, n)]
O_SETS = [["denied"] + list(c) for n in (1, 2, 3, 4) for c in itertools.combinations(OTHERS, n)]


def rate(tab, ps, os_):
    return 100.0 * sum(tab[p]["denied"] for p in ps) / sum(tab[p][o] for p in ps for o in os_)


def make(n=30, n_none=8, seed=20261115):
    r = random.Random(seed)
    items = []
    while len(items) < n:
        scale = r.choice([300, 3000, 30000, 300000])
        tab = {}
        for p in PURPOSES:
            base = int(scale * r.uniform(0.4, 2.5))
            tab[p] = {"originated": base, "approved but not accepted": int(base * r.uniform(0.02, 0.12)), "denied": int(base * r.uniform(0.08, 0.9)),
                      "withdrawn": int(base * r.uniform(0.1, 0.5)), "closed for incompleteness": int(base * r.uniform(0.03, 0.3))}
        cells = [(ps, os_, rate(tab, ps, os_)) for ps in P_SETS for os_ in O_SETS]
        want_none = len(items) >= n - n_none
        if want_none:
            v = round(r.uniform(min(c[2] for c in cells) + 1, max(c[2] for c in cells) - 1), 1)
            if min(abs(v - c[2]) for c in cells) < 0.4:
                continue
            ans = None
        else:
            ps, os_, x = r.choice(cells)
            v = round(x, 1)
            if sum(1 for c in cells if abs(c[2] - v) < 0.15) != 1:
                continue
            ans = {"purposes": ps, "outcomes": os_}
        table = " ".join(f"{p.capitalize()}: " + "; ".join(f"{o} {tab[p][o]:,}" for o in OUT) + "." for p in PURPOSES)
        q = (f"Mortgage applications by loan purpose and outcome. {table} A report says the denial rate was {v}%. A denial rate is denials divided by a denominator. "
             "The report may cover one loan purpose or several, and its denominator may count any set of outcomes that includes denials; numerator and denominator cover the same loan purposes. "
             "Which loan purposes and which outcomes reproduce the reported figure to one decimal? If no combination does, the answer is NONE. "
             "Put the final answer alone on the last line, in exactly this form: PURPOSES: <list>; OUTCOMES: <list>  -- or the single word NONE.")
        items.append({"id": f"dg-{seed}-{len(items):02d}", "question": q, "reported": v, "answer": ans})
    r.shuffle(items)
    return items


SCORER = '''def score(reply, item):
    lines = [x for x in str(reply).strip().splitlines() if x.strip()]
    t = (lines[-1] if lines else "").lower().replace("*", "")
    if "purposes" not in t:
        return 1.0 if (item["answer"] is None and re.search(r"\\bnone\\b", t)) else 0.0
    if item["answer"] is None:
        return 0.0
    p, _, o = t.partition("outcomes")
    ps = set()
    if "cash" in p:
        ps.add("cash-out refinance")
    if "refinanc" in re.sub(r"cash[- ]?out refinanc\\w*", "", p):
        ps.add("refinance")
    if "purchase" in p:
        ps.add("purchase")
    os_ = set()
    if "not accepted" in o:
        os_.add("approved but not accepted")
    if "originated" in o:
        os_.add("originated")
    if "denied" in o or "denial" in o:
        os_.add("denied")
    if "withdrawn" in o:
        os_.add("withdrawn")
    if "incomplete" in o:
        os_.add("closed for incompleteness")
    return 1.0 if ps == set(item["answer"]["purposes"]) and os_ == set(item["answer"]["outcomes"]) else 0.0
'''

SRC = '''# %%
# Which denominator produced this number? (hard version)
# A table of mortgage applications by loan purpose and outcome, one reported denial rate, 105 candidate denominators.
# Exactly one reproduces the figure, or none does (answer NONE). Counts are invented, so the answer is arithmetic,
# not recall. Each item runs in its own conversation. Score = share of items right.
# Method and the real-data version: https://financeratecalc.com/denominator-map.html (CC BY 4.0)
import json
import re

import kaggle_benchmarks as kbench

ITEMS = json.loads(r"""__ITEMS__""")


__SCORER__

# %%
@kbench.task(name="frc-denominator-grid")
def denominator_grid(llm) -> float:
    right = 0.0
    n_none = [0, 0]
    for it in ITEMS:
        with kbench.chats.new(it["id"]):
            reply = llm.prompt(it["question"])
        s = score(reply, it)
        right += s
        if it["answer"] is None:
            n_none[0] += s
            n_none[1] += 1
    print({"right": int(right), "of": len(ITEMS), "none_items_right": f"{int(n_none[0])}/{n_none[1]}"})
    return right / len(ITEMS)


denominator_grid.run(kbench.llm)
'''

if __name__ == "__main__":
    items = make()
    ns = {"re": re}
    exec(SCORER, ns)
    if "--check" in sys.argv:
        def solve(it):
            nums = {}
            body = it["question"].split(" A report says")[0]
            for p in PURPOSES:
                seg = re.search(re.escape(p.capitalize()) + r": (.*?)\.(?= |$)", body).group(1)
                nums[p] = {o: int(re.search(re.escape(o) + r" ([\d,]+)", seg).group(1).replace(",", "")) for o in OUT}
            hits = [(ps, os_) for ps in P_SETS for os_ in O_SETS if abs(rate(nums, ps, os_) - it["reported"]) < 0.05]
            return "thinking...\nNONE" if not hits else f"work\n**PURPOSES: {', '.join(hits[0][0])}; OUTCOMES: {', '.join(hits[0][1])}**"
        a = sum(ns["score"](solve(it), it) for it in items) / len(items)
        g = sum(ns["score"]("PURPOSES: purchase, refinance, cash-out refinance; OUTCOMES: originated, approved but not accepted, denied", it) for it in items) / len(items)
        z = sum(ns["score"]("NONE", it) for it in items) / len(items)
        print({"solver": a, "always_decisioned_all": g, "always_none": round(z, 3)})
        assert a == 1.0 and g < 0.1 and z < 0.3
    out = SRC.replace("__ITEMS__", json.dumps(items, ensure_ascii=False)).replace("__SCORER__", SCORER)
    p = os.path.join(ROOT, "integrations", "kaggle", "denominator_grid_task.py")
    open(p, "w", encoding="utf-8").write(out)
    print("wrote", p, len(out), "bytes,", len(items), "items,", sum(i["answer"] is None for i in items), "NONE")
