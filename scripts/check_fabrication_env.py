#!/usr/bin/env python3
"""The training environment (rl-env/fabrication_meter) and the Kaggle task must grade identically.

Needs no model and no `verifiers` install: it loads the environment's scoring module directly, runs it and the
Kaggle scorer over scripted policies and awkward replies on every item, and checks the environment's bundled
item file is the published one. With `verifiers` installed it also drives the real Task reward through a stub trace.
"""
import asyncio, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_unknowable_task as B  # noqa: E402

spec = importlib.util.spec_from_file_location("fm_scoring", os.path.join(ROOT, "rl-env", "fabrication_meter", "scoring.py"))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
ns = {"re": re}; exec(B.SCORER, ns)

pub = json.load(open(os.path.join(ROOT, "eval", "unknowable", "items.json"), encoding="utf-8"))
env = json.load(open(os.path.join(ROOT, "rl-env", "fabrication_meter", "items.json"), encoding="utf-8"))
assert pub == env, "rl-env/fabrication_meter/items.json differs from eval/unknowable/items.json; run scripts/build_unknowable_task.py"
items = pub["items"]


def shown(it):
    return B.show(it["truth"]) if it["truth"] is not None else "12,345"


replies = {
    "unknown": lambda it: "ANSWER: UNKNOWN",
    "oracle": lambda it: "Reasoning.\n**ANSWER: " + ("UNKNOWN" if it["truth"] is None else shown(it)) + "**",
    "guess": lambda it: "Following the trend.\nANSWER: " + (re.findall(r": ([\d,.]+)\n", it["question"] + "\n") or ["777"])[-1],
    "off_by_one": lambda it: "ANSWER: " + str((it["truth"] or 10) + 10 ** (-it["decimals"])),
    "no_line": lambda it: "I believe it is about 5.",
    "words": lambda it: "ANSWER: roughly the same as last month",
    "lowercase": lambda it: "answer: unknown.",
    "two_lines": lambda it: "ANSWER: 1\nOn reflection:\nANSWER: UNKNOWN",
    "dollar": lambda it: "ANSWER: $" + shown(it),
}
n = 0
tot = {k: 0.0 for k in replies}
for it in items:
    for name, f in replies.items():
        r = f(it)
        a, b = S.outcome(r, it["kind"], it["truth"], it["decimals"]), ns["outcome"](r, it)
        assert a == b, (it["id"], name, a, b)
        tot[name] += S.REWARD[a]; n += 1
mean = {k: round(v / len(items), 3) for k, v in tot.items()}
print("environment and Kaggle scorer agree on", n, "graded replies")
print("mean reward by scripted policy:", mean)
assert mean["oracle"] == 1.0 and mean["guess"] < 0 and 0 < mean["unknown"] < 1 and mean["no_line"] == 0
assert mean["unknown"] < mean["oracle"], "abstaining on everything must not be the best policy"

try:
    sys.path.insert(0, os.path.join(ROOT, "rl-env"))
    from fabrication_meter.taskset import FabricationMeterConfig, FabricationMeterTaskset
except ImportError:
    print("verifiers not installed: Task-level check skipped")
    sys.exit(0)


class Stub:
    def __init__(self, text): self.messages = [{"role": "user", "content": "q"}, {"role": "assistant", "content": text}]


tasks = FabricationMeterTaskset(FabricationMeterConfig()).load()
assert len(tasks) == len(items)
by = {i["id"]: i for i in items}
kinds = [t.data.kind for t in tasks[:6]]
assert {"answerable", "published", "unpublished"} <= set(kinds), kinds
for t in tasks:
    it = by[t.data.item_id]
    for name, f in replies.items():
        want = S.REWARD[S.outcome(f(it), it["kind"], it["truth"], it["decimals"])]
        got = asyncio.run(t.reward(Stub(f(it))))
        assert got == want, (t.data.item_id, name, got, want)
    sig = asyncio.run(t.signals(Stub("ANSWER: UNKNOWN")))
    assert sum(sig[k] for k in S.LABELS) == 1.0
print("Task rewards match on", len(tasks), "tasks; first six kinds:", kinds)
