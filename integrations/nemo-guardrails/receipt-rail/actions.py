"""Receipt rail for NVIDIA NeMo Guardrails: an output rail that checks the receipts in a bot message before it is shown.

A receipt looks like ⟦FRC:<claim-id>:<value>:<hash8>⟧ and travels next to a number taken from a public record. This
action asks the publisher's verify endpoint about every receipt in the message. No model is called. The message is
blocked when a receipt is

    stale                        the publisher corrected the figure after the receipt was issued
    hash-current-value-mismatch  the number next to the receipt was altered
    unrecognized                 the publisher never issued it
    revised by its source        an official report printed a different value in a later edition and the message does
                                 not say so

With FRC_RAIL_REQUIRE_RECEIPT=1 a message that states an FHA or VA denial rate with no receipt at all is blocked too.

Put this file next to config.yml. Endpoint: FRC_VERIFY_URL (default: the public, keyless endpoint)."""
import asyncio
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Callable, Optional

try:  # nemoguardrails >= 0.2x
    from nemoguardrails.actions import action
except Exception:  # lets the checks below be imported and tested without the library
    def action(**_kw):
        return lambda f: f
try:
    from nemoguardrails.actions.rail_outcome import RailOutcome
except Exception:
    class RailOutcome:  # same two constructors and the attribute the Colang flow reads
        def __init__(self, is_blocked, reason=None):
            self.is_blocked = is_blocked; self.reason = reason

        @classmethod
        def allow(cls):
            return cls(False)

        @classmethod
        def block(cls, reason=None):
            return cls(True, reason)

VERIFY = os.environ.get("FRC_VERIFY_URL", "https://frc-mcp.ziyetis.workers.dev/verify")
RECEIPT = re.compile(r"⟦FRC:[^⟧\s]+(?::[^⟧\s]+)*⟧")
RATE_CLAIM = re.compile(r"\b(FHA|VA)\b[^.]{0,80}\b(den(?:ial|ied))\b[^.]{0,80}\d+(?:\.\d+)?\s?%|\d+(?:\.\d+)?\s?%[^.]{0,80}\b(FHA|VA)\b[^.]{0,80}\bden(?:ial|ied)\b", re.I)


def _fetch(receipt: str) -> dict:
    req = urllib.request.Request(VERIFY + "?r=" + urllib.parse.quote(receipt, safe=""), headers={"Accept": "application/json", "User-Agent": "frc-receipt-rail/1.0 (nemo-guardrails)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def _mentions(text: str, value) -> bool:
    try:
        v = float(str(value).replace(",", ""))
    except ValueError:
        return str(value) in text
    return any(abs(float(n.replace(",", "")) - v) < 0.0051 for n in re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", text))


def check_text(text: str, fetch: Callable[[str], dict] = _fetch, require_receipt: bool = False) -> dict:
    """Pure check, no library needed: {"blocked": bool, "reason": str|None, "checked": [...]}"""
    receipts = list(dict.fromkeys(RECEIPT.findall(text or "")))
    checked, problems = [], []
    for r in receipts:
        try:
            v = fetch(r)
        except Exception as e:  # an unreachable verifier is reported, never silently passed
            problems.append(f"{r}: could not be verified ({str(e)[:60]})"); continue
        status = v.get("status")
        checked.append({"receipt": r, "status": status, "current_value": v.get("current_value")})
        if status == "stale":
            problems.append(f"{r}: the publisher corrected this figure; current value {v.get('current_value')}")
        elif status == "hash-current-value-mismatch":
            problems.append(f"{r}: the number next to this receipt was altered; the publisher's value is {v.get('current_value')}")
        elif status != "current":
            problems.append(f"{r}: not a receipt this publisher issued")
        else:
            rev = v.get("publisher_revision")
            if rev and rev.get("revised_to") is not None and not _mentions(text, rev["revised_to"]):
                problems.append(f"{r}: the source printed {rev['revised_to']} for this period in the {rev.get('revised_in')}; state both values and editions")
    if require_receipt and not receipts and RATE_CLAIM.search(text or ""):
        problems.append("an FHA or VA denial rate is stated without a receipt; quote the figure from the source tool with its receipt")
    return {"blocked": bool(problems), "reason": "; ".join(problems) or None, "checked": checked}


@action(name="frc_check_receipts", is_system_action=True)
async def frc_check_receipts(context: Optional[dict] = None):
    text = (context or {}).get("bot_message") or ""
    res = await asyncio.to_thread(check_text, text, _fetch, os.environ.get("FRC_RAIL_REQUIRE_RECEIPT") == "1")
    return RailOutcome.block(reason=res["reason"]) if res["blocked"] else RailOutcome.allow()
