#!/usr/bin/env python3
"""Denominator reasoning tasks: procedurally generated, so there is nothing to memorise.

    python3 scripts/build_denominator_tasks.py [--n 240] [--seed 2026] [--out DIR] [--check] [--selftest]

The edition-aware set asks what a document says. These tasks ask whether a system understands what a rate IS. Each task
gives the five outcome counts of a block of mortgage applications (originated, approved-not-accepted, denied, withdrawn,
closed-incomplete) and asks one of four things:

    compute   the denial rate under a denominator stated in words (one of the three in common use)
    novel     the rate under a denominator defined on the spot (any subset of the five outcomes that contains 'denied')
    convert   given the rate on one denominator and some of the counts, the rate on another
    infer     given the counts and a quoted rate, WHICH denominator produced it (the inverse problem; the generator
              guarantees exactly one subset fits within 0.05 points)

Counts are drawn around the real cells of data/purpose/*.json (shape and scale of the 2025 file) and then perturbed with
the seed, so every instance is new while the proportions stay realistic. A different seed gives a different set of the
same difficulty: the public split uses seed 2026; a held-out split is made by passing a seed that is not published.

Scoring is arithmetic: score(answer_text, task). No model."""
import glob
import itertools
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = ["originated", "approved_not_accepted", "denied", "withdrawn", "closed_incomplete"]
WORD = {"originated": "originated", "approved_not_accepted": "approved but not accepted", "denied": "denied", "withdrawn": "withdrawn", "closed_incomplete": "closed for incompleteness"}
STD = {"decisioned": ("originated", "approved_not_accepted", "denied"), "acted_on": tuple(A), "denied_plus_originated": ("originated", "denied")}
STD_WORDS = {"decisioned": "applications that reached a credit decision (originated, approved but not accepted, or denied)",
             "acted_on": "all applications acted on (every outcome listed)", "denied_plus_originated": "only applications that were either originated or denied"}
SUBSETS = [s for r in range(2, 6) for s in itertools.combinations(A, r) if "denied" in s]


def rate(c, subset):
    return 100.0 * c["denied"] / sum(c[k] for k in subset)


def seeds():
    cells = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "purpose", "*-2025.json"))):
        d = json.load(open(f, encoding="utf-8"))
        cells += [{k: c[k] for k in A} for key, c in sorted(d["cells"].items()) if c["acted_on"] >= 5000]
    return cells or [{"originated": 600000, "approved_not_accepted": 20000, "denied": 100000, "withdrawn": 150000, "closed_incomplete": 60000}]


def draw(rng, base):
    scale = rng.choice([0.002, 0.01, 0.05, 0.3, 1.0])
    return {k: max(7, int(base[k] * scale * rng.uniform(0.55, 1.6))) for k in A}


def unique_subset(c, target):
    return [s for s in SUBSETS if abs(rate(c, s) - target) <= 0.05]


def listing(c):
    return "; ".join(f"{WORD[k]}: {c[k]:,}" for k in A)


def make(n, seed):
    rng = random.Random(seed); base = seeds(); out = []; kinds = ["compute", "novel", "convert", "infer"]
    while len(out) < n:
        kind = kinds[len(out) % 4]; c = draw(rng, rng.choice(base)); tid = f"dr-{seed}-{len(out):04d}"
        if kind == "compute":
            b = rng.choice(list(STD)); v = rate(c, STD[b])
            out.append({"id": tid, "kind": kind, "counts": c, "question": f"A block of mortgage applications ended as follows. {listing(c)}. What is the denial rate if the denominator is {STD_WORDS[b]}? Answer in percent to one decimal.",
                        "answer_value": round(v, 2), "answer_text": f"{v:.1f}%", "denominator": list(STD[b])})
        elif kind == "novel":
            s = rng.choice([x for x in SUBSETS if x not in STD.values()]); v = rate(c, s)
            out.append({"id": tid, "kind": kind, "counts": c, "question": f"A block of mortgage applications ended as follows. {listing(c)}. Define the denominator as the applications that were {', '.join(WORD[k] for k in s[:-1])} or {WORD[s[-1]]}. What share of that denominator was denied? Answer in percent to one decimal.",
                        "answer_value": round(v, 2), "answer_text": f"{v:.1f}%", "denominator": list(s)})
        elif kind == "convert":
            given = rate(c, STD["decisioned"]); v = rate(c, STD["acted_on"]); dec = sum(c[k] for k in STD["decisioned"])
            out.append({"id": tid, "kind": kind, "counts": c, "question": f"Of {dec:,} mortgage applications that reached a credit decision, {given:.2f}% were denied. A further {c['withdrawn']:,} applications were withdrawn and {c['closed_incomplete']:,} were closed for incompleteness. What share of all applications acted on was denied? Answer in percent to one decimal.",
                        "answer_value": round(v, 2), "answer_text": f"{v:.1f}%", "denominator": list(STD["acted_on"])})
        else:
            s = rng.choice(SUBSETS); v = round(rate(c, s), 1)
            if len(unique_subset(c, v)) != 1:
                continue
            out.append({"id": tid, "kind": kind, "counts": c, "question": f"A block of mortgage applications ended as follows. {listing(c)}. A report says the denial rate was {v:.1f}%. Which outcomes must be in the report's denominator for that figure to be right? List them.",
                        "answer_value": v, "answer_text": ", ".join(WORD[k] for k in s), "denominator": list(s)})
    return out


def score(answer_text, task):
    t = answer_text.lower()
    if task["kind"] == "infer":
        said = {k for k in A if WORD[k] in t or k.replace("_", " ") in t}
        if "approved" in t and "not accepted" in t:
            said.add("approved_not_accepted")
        if re.search(r"incomplete", t):
            said.add("closed_incomplete")
        return 1.0 if said == set(task["denominator"]) else 0.0
    nums = [float(x) for x in re.findall(r"(?<![\d,.])\d{1,2}(?:\.\d+)?(?=\s?%)", t)] or [float(x) for x in re.findall(r"(?<![\d,.])\d{1,2}\.\d+", t)]
    return 1.0 if any(abs(x - task["answer_value"]) <= 0.06 for x in nums) else 0.0


README = """---
license: cc-by-4.0
task_categories:
- question-answering
language:
- en
tags:
- evaluation
- reasoning
- procedural
- statistics
- finance
pretty_name: Denominator Reasoning (procedurally generated)
size_categories:
- n<1K
---

# Denominator Reasoning: does a system understand what a rate is?

{n} tasks, generated by a public script from a seed. Each gives the five outcome counts of a block of mortgage applications and asks for a denial rate under a stated denominator ({k[compute]} tasks), under a denominator defined on the spot ({k[novel]}), converted from one denominator to another ({k[convert]}), or the inverse: which denominator produced a quoted rate ({k[infer]}; exactly one subset of outcomes fits).

**Nothing to memorise.** The counts are drawn around the shape of the real 2025 HMDA cells and perturbed by the seed; another seed gives another set of the same difficulty. This file is the public split (seed {seed}). Scoring is arithmetic, no model: `scripts/build_denominator_tasks.py::score`.

**Why.** The same public file yields "FHA denial rates" from 10.6% to 37.4% depending on loan purpose and denominator, and answer engines quote them interchangeably. Recalling a published number is not the skill; applying a definition to counts is. These tasks isolate that skill from recall.

**Limits.** One narrow skill (ratios over stated subsets), English only, one domain's vocabulary. A perfect score shows the arithmetic and the reading of a definition, not understanding of mortgage lending. The counts are synthetic; no figure here is a statistic about any lender, place or year.

Generator and reference scorer: https://github.com/financeratecalc/financeratecalc.github.io/blob/main/scripts/build_denominator_tasks.py. Real cells: https://financeratecalc.com/denominator-map.html. Licence: CC BY 4.0.
"""


def main():
    a = sys.argv[1:]; opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    n = int(opt("--n", "240")); seed = int(opt("--seed", "2026")); out_dir = opt("--out", os.path.join(ROOT, "data", "hf-mirrors", "denominator-reasoning"))
    tasks = make(n, seed)
    if "--selftest" in a:
        ok = all(score(t["answer_text"], t) == 1.0 for t in tasks)
        wrong = all(score("50.0%", t) == 0.0 for t in tasks if t["kind"] != "infer" and abs(t["answer_value"] - 50) > 0.1)
        inf = [t for t in tasks if t["kind"] == "infer"]; uniq = all(len(unique_subset(t["counts"], t["answer_value"])) == 1 for t in inf)
        partial = all(score("denied", t) == 0.0 for t in inf)
        print(f"selftest: reference answers 1.0: {ok}; wrong number 0.0: {wrong}; inverse tasks have one solution: {uniq}; partial list 0.0: {partial}; same seed reproduces: {make(n, seed) == tasks}")
        sys.exit(0 if ok and wrong and uniq and partial else 1)
    from collections import Counter
    k = Counter(t["kind"] for t in tasks)
    files = {"denominator_reasoning.jsonl": "\n".join(json.dumps(t, ensure_ascii=False) for t in tasks) + "\n", "README.md": README.format(n=len(tasks), k=k, seed=seed)}
    if "--check" in a:
        stale = [f for f, c in files.items() if not os.path.exists(os.path.join(out_dir, f)) or open(os.path.join(out_dir, f), encoding="utf-8").read() != c]
        print("denominator tasks:", "current" if not stale else f"STALE {stale}"); sys.exit(1 if stale else 0)
    os.makedirs(out_dir, exist_ok=True)
    for f, c in files.items():
        open(os.path.join(out_dir, f), "w", encoding="utf-8").write(c)
    print(f"wrote {len(tasks)} tasks (seed {seed}): {dict(k)}")


if __name__ == "__main__":
    main()
