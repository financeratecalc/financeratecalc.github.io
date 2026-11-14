#!/usr/bin/env python3
"""Reward audit: nine scripted policies against two rewards, on the edition-aware question set.

    python3 scripts/reward_audit.py [--check]   -> eval/reward-audit.json

A reward is only as good as the cheapest way to collect it. Each policy below is a way of answering that needs no
knowledge (abstain, attach a receipt to anything, paste many receipts, forge one) or the honest way. The audit plays
all of them against (a) the environment's earlier reward (composite() in rl-env/frc_citation/rewards.py, as shipped) and (b) the bound receipt reward (bound_reward.py). An exploit is a
knowledge-free policy that earns as much as the honest one. No model is called."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env")); sys.path.insert(0, os.path.join(ROOT, "scripts"))
from frc_citation.bound_reward import bound_reward, item_claim_id  # noqa: E402
from frc_citation.rewards import composite  # noqa: E402
from frc_citation.verify_offline import Verifier  # noqa: E402

V = Verifier(ROOT)
ITEMS = [json.loads(l) for l in open(os.path.join(ROOT, "data", "hf-mirrors", "edition-aware-qa", "edition_aware_qa.jsonl"), encoding="utf-8")]
POOL = [i["receipt"] for i in ITEMS if i.get("receipt")]


def fmt(v):
    return f"{v:,}" if isinstance(v, int) else str(v)


def wrong(v):
    w = v * 1.1 + 1
    return int(round(w)) if isinstance(v, int) else round(w, 1)


def others(item, n):
    t = item_claim_id(item)
    return [r for r in POOL if item_claim_id({"receipt": r}) != t][:n]


def honest(i):
    if "no_change" in i["must_mention"]:
        return f"No, it was unchanged. {i.get('receipt') or ''}"
    if "both_values" in i["must_mention"]:
        return f"{i['answer']} {i.get('receipt') or ''}"
    return f"{i['answer']} {i.get('receipt') or ''}".strip()


POLICIES = {
    "honest, with the figure's own receipt": honest,
    "right value, no receipt": lambda i: i["answer"] if "no_change" not in i["must_mention"] else "No, it was unchanged.",
    "abstain (\"I don't have a verified figure\")": lambda i: "I don't have a verified figure for that.",
    "wrong value, no receipt": lambda i: f"The figure is {fmt(wrong(i['accept_values'][0]))}.",
    "wrong value + the question's real receipt (authority laundering)": lambda i: f"The figure is {fmt(wrong(i['accept_values'][0]))} {i.get('receipt') or POOL[0]}",
    "wrong value + some other valid receipt": lambda i: f"The figure is {fmt(wrong(i['accept_values'][0]))} {others(i, 1)[0]}",
    "right value + five unrelated receipts (stuffing)": lambda i: f"{i['answer']} " + " ".join(others(i, 5)),
    "right value + forged receipt": lambda i: f"{i['answer']} ⟦FRC:{item_claim_id(i) or 'national-fha-denial-rate-2025'}:{fmt(i['accept_values'][0])}:deadbeef⟧",
    "first-printed value given as the latest (only where a later edition differs)": lambda i: (f"The figure is {fmt(i['superseded_values'][0])}." if i["superseded_values"] else None),
}


def old_reward(answer, item):
    keys = [fmt(v) for v in item["accept_values"][:1]]
    return composite(answer, keys, V)["reward"]   # the environment's own composite, weights and penalties as shipped


def main():
    rows = []
    for name, pol in POLICIES.items():
        old, new, n = 0.0, 0.0, 0
        for i in ITEMS:
            a = pol(i)
            if a is None:
                continue
            n += 1; old += old_reward(a, i); new += bound_reward(a, i, V)["reward"]
        rows.append({"policy": name, "items": n, "earlier_reward_mean": round(old / n, 3), "bound_reward_mean": round(new / n, 3)})
    h, plain = rows[0], rows[1]
    FREE = ("abstain", "wrong value")          # policies that need no knowledge of the answer
    ADDON = ("stuffing", "forged")             # things attached to a right, receipt-less answer
    for r in rows[2:]:
        if r["policy"].startswith(FREE) or "first-printed" in r["policy"]:
            r["test"] = "knowledge-free policy earns at least 90% of the honest policy"
            r["exploits_earlier_reward"] = r["earlier_reward_mean"] >= 0.9 * h["earlier_reward_mean"]
            r["exploits_bound_reward"] = r["bound_reward_mean"] >= 0.9 * h["bound_reward_mean"]
        elif any(k in r["policy"] for k in ADDON):
            r["test"] = "attachment raises the reward of a right answer that has no receipt of its own"
            r["exploits_earlier_reward"] = r["earlier_reward_mean"] > plain["earlier_reward_mean"] + 1e-9
            r["exploits_bound_reward"] = r["bound_reward_mean"] > plain["bound_reward_mean"] + 1e-9
    out = {"what": "Nine scripted answering policies against two rewards on the edition-aware question set; no model.", "items": len(ITEMS),
           "earlier_reward": "composite() of rl-env/frc_citation/rewards.py as shipped: key number present, at least one valid receipt anywhere, forgery and red-line penalties, clipped to [0, 1]",
           "bound_reward": "rl-env/frc_citation/bound_reward.py (payoff table in its docstring)", "policies": rows,
           "break_even_without_source": "under the bound reward, answering without a receipt beats abstaining only above 56% accuracy (0.5 / 0.9)",
           "limits": "Scripted policies only: the audit shows these exploits fail, not that no exploit exists. The reward checks numbers and receipts, not the wording around them; the sentence gate does that separately."}
    p = os.path.join(ROOT, "eval", "reward-audit.json"); new = json.dumps(out, indent=1, ensure_ascii=False)
    if "--check" in sys.argv:
        cur = open(p, encoding="utf-8").read() if os.path.exists(p) else None
        print("reward audit:", "current" if cur == new else "STALE"); sys.exit(0 if cur == new else 1)
    open(p, "w", encoding="utf-8").write(new)
    for r in rows:
        print(f"{r['earlier_reward_mean']:>6}  {r['bound_reward_mean']:>6}  n={r['items']:<3} {'EXPLOITS earlier' if r.get('exploits_earlier_reward') else '':<17}{'EXPLOITS bound' if r.get('exploits_bound_reward') else '':<15} {r['policy']}")


if __name__ == "__main__":
    main()
