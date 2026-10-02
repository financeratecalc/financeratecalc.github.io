#!/usr/bin/env python3
"""Record the publisher's live tool outputs into a replay cache for offline rollouts.

Why: the live MCP server is free and rate-limited; a trainer running thousands of
rollouts should not depend on it. The cache holds the outputs of every call the
twelve-question battery needs, plus the tool list, keyed by (tool, canonical args).
`servers/tool.py` serves a hit from the cache and only goes to the network on a miss
(or never, with FRC_OFFLINE=1).

Run from a machine that can reach the worker (GitHub Actions does):
    python -m frc_citation.record_tool_cache [out.json]
"""
from __future__ import annotations
import datetime as dt
import json
import sys
from pathlib import Path

from .servers.tool import _jsonrpc, cache_key

OUT = Path(__file__).resolve().parent / "fixtures" / "tool-cache.json"

# Every call the battery can need. Lenders and states are the ones named in the
# answer key plus the ranked table's extremes; args mirror the server's schemas.
CALLS: list[tuple[str, dict]] = [
    ("get_national_fha_stats", {}),
    ("list_lenders", {}),
    ("list_cohorts", {}),
    ("get_door_effect_summary", {}),
    ("get_denial_reason_shares", {}),
    ("get_small_loan_penalty", {}),
    ("get_small_loan_penalty", {"state": "all"}),
    ("get_metro_lender_gap", {"metro": "Cleveland"}),
    ("get_metro_lender_gap", {"metro": "Cleveland, OH"}),
    ("get_conditional_door_map", {}),
    ("check_claim_contract", {"claim_id": "national-fha-denial-rate-2025"}),
]
for lender in ["AmeriSave", "CrossCountry", "Rocket", "United Wholesale", "Freedom Mortgage",
               "Pennymac", "loanDepot", "Mutual of Omaha", "NewRez", "Fairway", "Guild",
               "Movement", "CMG", "Nationstar", "Bank of America", "Wells Fargo", "JPMorgan Chase",
               "Citizens", "Truist", "U.S. Bank", "Navy Federal", "Flagstar", "PNC"]:
    CALLS.append(("get_lender_denial_stats", {"lender": lender}))
for st in ["ID", "NH", "CA", "TX", "FL", "NY", "OH", "WV", "MS", "AL", "LA", "AR", "OK", "KS",
           "IA", "NE", "ND", "SD", "MT", "WY", "VT", "ME", "AK", "HI", "DC", "PR"]:
    CALLS.append(("get_state_denial_stats", {"state": st}))
for metro in ["Cleveland", "Detroit", "Chicago", "Houston", "Phoenix", "Atlanta", "Dallas",
              "Los Angeles", "New York", "Miami", "Memphis", "Birmingham", "St. Louis"]:
    CALLS.append(("get_metro_lender_gap", {"metro": metro}))


def main(out: Path = OUT) -> None:
    rec: dict = {
        "recorded": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "server": "https://frc-mcp.ziyetis.workers.dev",
        "note": "Replay cache of the publisher's live tool outputs. Receipts inside carry the issue "
                "channel 'm' and the month of recording; the offline verifier accepts them. "
                "Re-record after any correction (scripts/build_receipts_snapshot.py changes).",
        "tools_list": None,
        "calls": {},
        "errors": {},
    }
    rec["tools_list"] = _jsonrpc("tools/list").get("result", {})
    rec["worker_version"] = (rec["tools_list"].get("_meta") or {}).get("version")
    for tool, args in CALLS:
        k = cache_key(tool, args)
        try:
            res = _jsonrpc("tools/call", {"name": tool, "arguments": args})
            rec["calls"][k] = res.get("result", res)
        except Exception as e:  # recorded, not fatal: a miss falls through to the network at rollout time
            rec["errors"][k] = str(e)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"recorded {len(rec['calls'])} calls, {len(rec['errors'])} errors -> {out}")
    if rec["errors"]:
        for k, v in rec["errors"].items():
            print("  error", k, v[:120])


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
