#!/usr/bin/env python3
"""Writes integrations/kaggle/denominator_reasoning_task.py: a self-contained Kaggle Benchmarks task.

40 of the 240 denominator-reasoning items (10 per kind, in file order) are embedded with the same scorer the data set
ships, so the task needs no attached data set and nothing but the kaggle-benchmarks SDK. The file is pasted into
kaggle.com/benchmarks/tasks/new by the publisher; this script only keeps it in step with the data.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_denominator_tasks as b  # noqa: E402

rows = [json.loads(line) for line in open(os.path.join(ROOT, "data", "hf-mirrors", "denominator-reasoning", "denominator_reasoning.jsonl"), encoding="utf-8")]
pick = []
for kind in ("compute", "novel", "convert", "infer"):
    pick += [r for r in rows if r["kind"] == kind][:10]
items = [{k: r[k] for k in ("id", "kind", "question", "answer_value", "denominator")} for r in pick]
for r, it in zip(pick, items):  # the embedded scorer must agree with the shipped one on the reference answer
    assert b.score(r["answer_text"] if r["kind"] != "infer" else ", ".join(b.WORD[k] for k in r["denominator"]), r) == 1.0, r["id"]

SRC = '''# %%
# Denominator reasoning: can a model say which applications a rate is counted over?
# 40 items (10 per kind) from https://huggingface.co/datasets/FinanceRateCalc/denominator-reasoning (CC BY 4.0).
# Every item is generated from invented counts, so the answer is arithmetic, not recall. Score = share of items right.
import json
import re

import kaggle_benchmarks as kbench

ITEMS = json.loads(r"""__ITEMS__""")
A = __A__
WORD = __WORD__


def score(answer_text, task):
    t = answer_text.lower()
    if task["kind"] == "infer":
        said = {k for k in A if WORD[k] in t or k.replace("_", " ") in t}
        if "approved" in t and "not accepted" in t:
            said.add("approved_not_accepted")
        if re.search(r"incomplete", t):
            said.add("closed_incomplete")
        return 1.0 if said == set(task["denominator"]) else 0.0
    nums = [float(x) for x in re.findall(r"(?<![\\d,.])\\d{1,2}(?:\\.\\d+)?(?=\\s?%)", t)] or [float(x) for x in re.findall(r"(?<![\\d,.])\\d{1,2}\\.\\d+", t)]
    return 1.0 if any(abs(x - task["answer_value"]) <= 0.06 for x in nums) else 0.0


# %%
@kbench.task(name="frc-denominator-reasoning")
def denominator_reasoning(llm) -> float:
    right = 0.0
    by_kind = {}
    for it in ITEMS:
        with kbench.chats.new(it["id"]):  # each item in its own conversation: no item sees an earlier one
            reply = llm.prompt(it["question"] + "\\n\\nGive only the final answer on the last line.")
        last = [line for line in str(reply).strip().splitlines() if line.strip()][-1:] or [""]
        s = score(last[0], it)
        right += s
        k = by_kind.setdefault(it["kind"], [0, 0])
        k[0] += s
        k[1] += 1
    print({k: f"{int(v[0])}/{v[1]}" for k, v in by_kind.items()})
    return right / len(ITEMS)


denominator_reasoning.run(kbench.llm)
'''
out = SRC.replace("__ITEMS__", json.dumps(items, ensure_ascii=False)).replace("__A__", repr(list(b.A))).replace("__WORD__", repr(dict(b.WORD)))
p = os.path.join(ROOT, "integrations", "kaggle", "denominator_reasoning_task.py")
open(p, "w", encoding="utf-8").write(out)
print("wrote", p, len(out), "bytes,", len(items), "items")
