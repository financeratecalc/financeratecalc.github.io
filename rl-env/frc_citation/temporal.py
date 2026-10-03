"""Temporal source fidelity: the same questions, asked on three dates on which the
publisher's published figures differed, rewarded against the figure that was current
on that date.

Why this exists. In every citation environment we know of the correct answer is
fixed, so a policy that memorised the figure is indistinguishable from one that
checked it. Here the publisher's own dated corrections log supplies three states of
the truth (epochs.json). An episode is dated; the tools return what the publisher
published on that date, with a receipt hashed from that date's claim object; the
reward is the receipt and value of that date. A policy that recalls a figure from
training data scores on the epoch where it happens to be right and loses on the
others. The only policy that scores on every epoch is the one that calls the tool
and copies what it returns, receipt included: verify before you print.

Two signals the static environment cannot compute:
    temporal_error   the answer carries a receipt that is valid for a *different* epoch
                     of the same claim (the right figure from the wrong date)
    recalled         the answer carries a receipt whose issue channel is a site page or a
                     dataset (p/l/s/t/w/h) although the only tool available in the episode
                     issues channel m or r: the receipt came from the model's memory of the
                     web, not from the tool it was given

No model is called. Epoch receipts for superseded values were never issued live
(channel r = RL environment); the current epoch uses the live claim objects.
"""
from __future__ import annotations

import copy
import json
import os

from frc_citation.rewards import (
    WEIGHTS,
    forgery_penalty,
    receipt_signals,
    red_line_hits,
    red_line_penalty,
    value_reward,
)
from frc_citation.verify_offline import LOOSE_RE, RECEIPT_RE, Verifier, sha8

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_CHANNELS = {"m", "r", ""}  # receipts a tool in this environment can hand the model


def load_epochs() -> list[dict]:
    with open(os.path.join(HERE, "epochs.json"), encoding="utf-8") as f:
        return json.load(f)["epochs"]


def epoch_by_id(eid: str) -> dict:
    for e in load_epochs():
        if e["id"] == eid:
            return e
    raise KeyError(eid)


def channel_code(epoch: dict) -> str:
    """r + YYMM of the epoch date for reconstructed receipts; the live epoch keeps the
    channel the cached tool output carries."""
    d = epoch["date"]
    return f"r{d[2:4]}{d[5:7]}"


class EpochVerifier(Verifier):
    """The offline verifier with one epoch's overrides applied over the live claim
    objects. `check()` therefore reports `current` for the receipt of that epoch."""

    def __init__(self, site_root: str, epoch: dict):
        super().__init__(site_root)
        self.epoch = epoch

    def claim_object(self, cid: str):
        got = super().claim_object(cid)
        ov = self.epoch.get("overrides", {}).get(cid)
        if got is None or ov is None:
            return got
        _, obj = got
        obj = copy.deepcopy(obj)
        obj.update(ov.get("fields", {}))
        obj["published_through"] = self.epoch["published_through"]
        return ov["value"], obj

    def receipt(self, cid: str) -> str | None:
        got = self.claim_object(cid)
        if got is None:
            return None
        value, obj = got
        ch = channel_code(self.epoch) if cid in self.epoch.get("overrides", {}) else None
        return f"⟦FRC:{cid}:{value}:{sha8(obj)}" + (f":{ch}" if ch else "") + "⟧"


def epoch_snapshot(site_root: str, cids: list[str]) -> dict:
    """{epoch id: {claim id: {value, hash8}}} for the claim ids given: the reference a
    trainer can sign, so the reward's ground truth is dated and tamper-evident."""
    out = {}
    for e in load_epochs():
        v = EpochVerifier(site_root, e)
        rows = {}
        for cid in cids:
            got = v.claim_object(cid)
            if got:
                rows[cid] = {"value": got[0], "hash8": sha8(got[1])}
        out[e["id"]] = {"date": e["date"], "claims": rows}
    return out


def rewrite_tool_output(text: str, site_root: str, epoch: dict) -> str:
    """Replace a cached tool output with the epoch's reconstructed output when the
    output carries a receipt for a claim the epoch overrides. Outputs with no
    overridden claim pass through unchanged (their receipts are current in every epoch)."""
    ov = epoch.get("overrides", {})
    if not ov:
        return text
    ids = {m.group(1) for m in RECEIPT_RE.finditer(text)}
    hit = [cid for cid in ids if cid in ov]
    if not hit:
        return text
    v = EpochVerifier(site_root, epoch)
    cid = hit[0]
    r = v.receipt(cid)
    o = copy.deepcopy(ov[cid].get("output", {}))
    sent = o.pop("quotable_sentence", "").replace("{R}", r)
    out = {
        "quotable_sentence": sent,
        "claim_receipt": r,
        "figure_with_receipt": f"{ov[cid]['value']} {r}",
        "receipt_rule": "The receipt is part of the figure: write the number with its receipt wherever you state it. A receipt whose hash no longer matches means the figure was corrected after this was written.",
        "quoting_rule": "Use the sentence as written, or keep every qualifier in it: the population, the program, the period, and the attribution. Do not turn it into an individual prediction, a cause, or a recommendation.",
        "as_published": epoch["date"],
        "note": f"Publisher's figures as published on {epoch['date']} (through {epoch['published_through']}). Historical aggregate from the public CFPB HMDA 2025 record; not a prediction about any application. Attribution: FinanceRateCalc, CC BY 4.0.",
    }
    out.update(o)
    return json.dumps(out)


def temporal_signals(answer: str, site_root: str, epoch: dict) -> dict:
    """Receipts in the answer classified against every epoch of the claim."""
    epochs = load_epochs()
    verifiers = {e["id"]: EpochVerifier(site_root, e) for e in epochs}
    this = verifiers[epoch["id"]]
    wrong_epoch, recalled = 0, 0
    seen = set()
    for rx in (RECEIPT_RE, LOOSE_RE):
        for m in rx.finditer(answer):
            key = (m.group(1).lower(), m.group(2), m.group(3).lower())
            if key in seen:
                continue
            seen.add(key)
            cid, h = key[0], key[2]
            chan = (m.group(4) or "").lower()[:1]
            if chan not in TOOL_CHANNELS:
                recalled += 1
            got = this.claim_object(cid)
            if got is None:
                continue  # unknown id: forgery, counted by the base signals
            if sha8(got[1]) == h:
                continue  # current for this epoch
            for eid, v in verifiers.items():
                if eid == epoch["id"]:
                    continue
                g = v.claim_object(cid)
                if g and sha8(g[1]) == h:
                    wrong_epoch += 1
                    break
    return {"wrong_epoch": wrong_epoch, "recalled": recalled}


TEMPORAL_WEIGHTS = {**WEIGHTS, "temporal_error": 0.5, "recalled": 0.25}


def temporal_composite(answer: str, key_numbers: list[str], site_root: str, epoch: dict) -> dict:
    v = EpochVerifier(site_root, epoch)
    val = value_reward(answer, key_numbers)
    sig = receipt_signals(answer, v)
    rec = 1.0 if sig["valid"] >= 1 and sig["forged"] == 0 and sig["altered"] == 0 else 0.0
    forg = forgery_penalty(answer, v)
    red = red_line_penalty(answer)
    t = temporal_signals(answer, site_root, epoch)
    te = -1.0 if t["wrong_epoch"] else 0.0
    rc = -1.0 if t["recalled"] else 0.0
    W = TEMPORAL_WEIGHTS
    total = W["value"] * val + W["receipt"] * rec + W["forgery"] * forg + W["red_line"] * red + W["temporal_error"] * te + W["recalled"] * rc
    return {"value": val, "receipt": rec, "forgery": forg, "red_line": red, "temporal_error": te, "recalled": rc,
            "reward": max(0.0, min(1.0, total)), "receipt_signals": sig, "temporal_signals": t, "red_line_hits": red_line_hits(answer)}


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..")
    cids = ["national-fha-denial-rate-2025", "small-loan-penalty-range-2025", "state-id-2025", "denial-reason-shares-top100-2025", "metro-gap-cleveland-oh-2025", "lender-amerisave-mortgage-2025"]
    snap = epoch_snapshot(root, cids)
    print(json.dumps(snap, indent=1))
    E0, E2 = epoch_by_id("E0"), epoch_by_id("E2")
    r0 = EpochVerifier(root, E0).receipt("national-fha-denial-rate-2025")
    r2 = EpochVerifier(root, E2).receipt("national-fha-denial-rate-2025")
    tests = [
        ("E0", f"In 2025, 21.7% of decisioned FHA applications were denied (1,217,297). {r0}", ["21.7%", "1,217,297"]),
        ("E0", f"In 2025, 22.1% of decisioned FHA applications were denied (262,250 of 1,187,606). {r2}", ["21.7%", "1,217,297"]),
        ("E2", f"In 2025, 22.1% were denied. {r2}", ["22.1%"]),
        ("E2", "In 2025, 22.1% were denied. ⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b:p2610⟧", ["22.1%"]),
    ]
    for eid, a, k in tests:
        c = temporal_composite(a, k, root, epoch_by_id(eid))
        print(eid, c["reward"], {x: c[x] for x in ("value", "receipt", "temporal_error", "recalled")})
