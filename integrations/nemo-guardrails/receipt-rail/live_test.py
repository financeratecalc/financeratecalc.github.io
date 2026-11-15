"""Live test of the receipt rail inside NeMo Guardrails itself (run in CI; needs `pip install nemoguardrails`).

test_actions.py checks the rail's logic without the library. This file loads config.yml and rails.co with the real
library, with no model configured, and sends two finished bot messages through the output rail only: one carrying a
receipt the publisher issued, one carrying the same receipt with its hash altered. The first must come back unchanged,
the second must be replaced by the refusal. It always exits 0 and writes live-test.json, pass or fail, so the result
(and the error, if the library's interface is not what this file assumes) is on record either way.
"""
import asyncio
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
GOOD = "In 2025, 22.1% of decisioned FHA applications were denied. " + sys.argv[1]
BAD = GOOD[:-2] + ("0" if GOOD[-2] != "0" else "1") + GOOD[-1]
REFUSAL = "I can't state that figure as written"
out = {"library": "nemoguardrails", "version": None, "cases": [], "error": None, "passed": False}


def text_of(res):
    for get in (lambda r: r.response[-1]["content"], lambda r: r.response["content"], lambda r: r.response, lambda r: r["content"], lambda r: r[-1]["content"]):
        try:
            v = get(res)
            if isinstance(v, str):
                return v
        except Exception:
            pass
    return repr(res)[:400]


async def main():
    import nemoguardrails
    from nemoguardrails import LLMRails, RailsConfig
    out["version"] = getattr(nemoguardrails, "__version__", None)
    rails = LLMRails(RailsConfig.from_path(HERE))
    for name, msg, want_block in (("issued receipt", GOOD, False), ("altered receipt", BAD, True)):
        case = {"case": name, "want_blocked": want_block}
        try:
            res = await rails.generate_async(messages=[{"role": "user", "content": "What was the FHA denial rate in 2025?"}, {"role": "assistant", "content": msg}], options={"rails": ["output"]})
            t = text_of(res)
            case.update(output=t[:300], blocked=REFUSAL in t, unchanged=t.strip() == msg.strip())
            case["ok"] = case["blocked"] if want_block else case["unchanged"]
        except Exception:
            case.update(ok=False, error=traceback.format_exc()[-900:])
        out["cases"].append(case)
    out["passed"] = len(out["cases"]) == 2 and all(c.get("ok") for c in out["cases"])


try:
    asyncio.run(main())
except Exception:
    out["error"] = traceback.format_exc()[-1200:]
json.dump(out, open(os.path.join(HERE, "live-test.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
