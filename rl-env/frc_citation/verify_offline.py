"""Offline claim-receipt verifier.

Recomputes a FinanceRateCalc claim receipt  ⟦FRC:<id>:<value>:<hash8>⟧  from the
repository's own data files, with no network call, so a reward function can run at
RL scale. Mirrors worker/index.js `/verify` exactly (same claim objects, same
canonical serialisation: keys sorted, no whitespace, SHA-256, first 8 hex chars).

    from verify_offline import Verifier
    v = Verifier(site_root=".")            # repository root
    v.check("⟦FRC:national-fha-denial-rate-2025:22.1%:ebf6b00b⟧")
    -> {"id": ..., "status": "current" | "stale" | "altered" | "unknown-id" | "malformed"}

Statuses: current  = hash matches today's claim object and the quoted value is today's value
          stale    = hash does not match: the figure was corrected after the receipt was issued
          altered  = hash matches but the quoted value is not the current value (the quote was edited)
          unknown-id / malformed = not a receipt this publisher could have issued
"""
from __future__ import annotations
import hashlib, json, os, re

RECEIPT_RE = re.compile(r"⟦FRC:([a-z0-9-]+):([^:⟧]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?⟧", re.I)
CHANNELS = {"m": "MCP tool output", "w": "site page", "p": "answer page", "l": "lender page", "s": "state page", "t": "top-100 table", "h": "Hugging Face dataset", "a": "API JSON", "r": "RL environment"}
LOOSE_RE = re.compile(r"FRC:([a-z0-9-]+):([^:\s⟧]+):([a-f0-9]{8})(?::([a-z][0-9]{4}))?", re.I)


def _js_num(x):
    """Serialise a number the way JSON.stringify does (integers without .0)."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def _filter(x, allowed):
    """JSON.stringify(obj, keysArray) applies the key whitelist at every depth and emits
    keys in the array's (sorted) order; nested keys absent from the top-level list are
    dropped. Reproduced here so nested claim objects hash identically."""
    if isinstance(x, dict):
        return {k: _filter(v, allowed) for k, v in x.items() if k in allowed}
    if isinstance(x, list):
        return [_filter(v, allowed) for v in x]
    return _js_num(x)


def sha8(obj: dict) -> str:
    canon = json.dumps(_filter(obj, set(obj.keys())), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:8]


class Verifier:
    def __init__(self, site_root: str = "."):
        self.root = site_root

    def _json(self, rel: str):
        with open(os.path.join(self.root, rel.lstrip("/")), encoding="utf-8") as f:
            return json.load(f)

    def claim_object(self, cid: str):
        """(current_value_string, claim_object) for a claim id, or None."""
        if cid == "national-fha-denial-rate-2025":
            idx = self._json("/api/index.json")
            return f"{idx['national']['rate_pct']:.1f}%", self._json("/claims/national-fha-denial-rate-2025.json")["claim"]
        if cid.startswith("lender-"):
            L = self._json(f"/api/lender/{cid[7:-5]}.json")
            return f"{float(L['denial_rate_pct']):.1f}%", {"lender": L["lender"], "metric": "fha_denial_rate", "value": L["denial_rate_pct"], "n": L["decisioned_applications"], "period": "2025"}
        if cid.startswith("state-"):
            S = self._json(f"/api/state/{cid[6:-5]}.json")
            return f"{float(S['denial_rate_pct']):.1f}%", {"state": S["state"], "metric": "fha_denial_rate", "value": S["denial_rate_pct"], "n": S["decisioned_applications"], "period": "2025"}
        if cid == "door-effect-38pct-2026":
            d = self._json("/data/door-effect-2025.json")
            return f"{round(d['door_effect_share_of_explained'] * 100)}%", {"metric": "door_effect_share", "value": d["door_effect_share_of_explained"], "n": d["records_used"], "period": "2025"}
        if cid.startswith("metro-gap-"):
            P = self._json(f"/claims/{cid}.json")
            c = P["claim"]; val = c.get("value", c.get("gap_pp"))
            return f"{float(val):.1f}pp", c
        if cid.startswith("small-loan-penalty-") and cid != "small-loan-penalty-range-2025":
            d = self._json("/api/small-loan-penalty.json"); st = cid[19:-5].upper()
            row = next(r for r in d["ranked"] if r["state"] == st)
            return f"{row['penalty_ratio']}x", {"state": st, "metric": "small_loan_penalty_ratio", "value": row["penalty_ratio"], "small": row["small_loan_denial_pct"], "big": row["big_loan_denial_pct"], "period": "2025"}
        if cid == "small-loan-penalty-range-2025":
            d = self._json("/api/small-loan-penalty.json")
            return f"{d['min_penalty']}x-{d['max_penalty']}x", {"metric": "small_loan_penalty_range", "min": d["min_penalty"], "max": d["max_penalty"], "states": d["states"], "period": "2025"}
        if cid == "denial-reason-shares-top100-2025":
            d = self._json("/api/denial-reasons-top100.json"); br = d["by_reason"]
            top = max(br, key=lambda k: br[k]["median_share_pct"]); inc = br["incomplete"]
            return f"{top}-{br[top]['median_share_pct']}%", {"metric": "denial_reason_median_shares", "top_reason": top, "top_median": br[top]["median_share_pct"], "incomplete_median": inc["median_share_pct"], "incomplete_max": inc["max_share_pct"], "n_lenders": d["n_lenders"], "period": "2025"}
        return None

    def check(self, receipt: str) -> dict:
        m = RECEIPT_RE.search(receipt) or LOOSE_RE.search(receipt)
        if not m:
            return {"status": "malformed", "receipt": receipt}
        cid, value, h = m.group(1), m.group(2), m.group(3).lower()
        chan = (m.group(4) or "").lower()
        issued = {"channel": chan[:1], "channel_meaning": CHANNELS.get(chan[:1], "unknown"), "issued_month": f"20{chan[1:3]}-{chan[3:5]}"} if chan else {"channel": "none"}
        try:
            got = self.claim_object(cid)
        except (FileNotFoundError, StopIteration, KeyError):
            got = None
        if got is None:
            return {"id": cid, "status": "unknown-id", "quoted_value": value, "issued": issued}
        current, obj = got
        now = sha8(obj)
        status = "current" if (now == h and current == value) else ("altered" if now == h else "stale")
        return {"id": cid, "status": status, "quoted_value": value, "current_value": current, "hash_now": now, "hash_quoted": h, "issued": issued}

    def find_all(self, text: str) -> list[dict]:
        """Every receipt-shaped string in a text, checked. Loose (bracketless) forms are
        included because models drop the brackets; a bracketless but otherwise valid
        receipt still verifies."""
        seen, out = set(), []
        for rx in (RECEIPT_RE, LOOSE_RE):
            for m in rx.finditer(text):
                key = (m.group(1).lower(), m.group(2), m.group(3).lower(), (m.group(4) or "").lower())
                if key in seen:
                    continue
                seen.add(key); out.append(self.check(m.group(0)))
        return out


if __name__ == "__main__":
    import sys
    v = Verifier(sys.argv[1] if len(sys.argv) > 1 else ".")
    for r in sys.argv[2:]:
        print(json.dumps(v.check(r)))
