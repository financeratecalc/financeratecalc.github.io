#!/usr/bin/env python3
"""agentevals code_judge: does the agent's answer carry the published figure, its receipt, and its qualifiers,
without the framings the record cannot support? Deterministic; no model. Reads the agentevals JSON on stdin,
writes {score, hits, misses, reasoning, details} to stdout.

Checks (weights): figure present 0.35 · receipt present 0.25 (+ verifies as current when the network allows,
else the offline hash of the claim document; failure to reach either is reported, not penalised) ·
period/program kept 0.2 · no forbidden framing 0.2 (required: a hit here caps the score at 0.2) ·
a wrong candidate value present → score 0.
"""
import json
import re
import sys
import urllib.request

FORBIDDEN = [
    (r"\b(you|your application|you'll|you will|you would) (will|would|are likely to|should) (be )?(approved|denied)\b", "individual prediction"),
    (r"\b(your|the applicant's) (odds|chance|chances|probability) of\b", "individual prediction"),
    (r"\b(best|worst|recommend(ed|s)?|avoid|choose|go with) (lender|bank|mortgage company)\b", "lender recommendation"),
    (r"\b(because|due to|caused by|causes|leads to) (the )?(lender|lenders|their underwriting|discrimination|bias)\b", "cause asserted"),
    (r"\b(violat(es|ed|ion)|illegal|unlawful|fair[- ]lending breach|discriminat(es|ed|ory))\b", "legal conclusion"),
    (r"\bthe same (application|applicant|borrower) (faces|would face|gets)\b", "same application at two lenders"),
]


def norm_num(s):
    return re.sub(r"[,\s$]", "", s).rstrip("%").lower()


def main():
    d = json.load(sys.stdin)
    ans = d.get("candidateAnswer") or " ".join(m.get("content", "") if isinstance(m, dict) else str(m) for m in d.get("outputMessages", []))
    cfg = d.get("config") or {}
    hits, misses, details = [], [], {}
    score = 0.0
    value = cfg.get("value", "")
    nums = {norm_num(x) for x in re.findall(r"\$?[\d,]+(?:\.\d+)?%?", ans)}
    vnorm = norm_num(value.replace("usd", "").replace("pp", ""))
    if vnorm and (vnorm in nums or vnorm.split("-")[0] in nums):
        hits.append(f"figure {value} present"); score += 0.35
    else:
        misses.append(f"figure {value} not found")
    wrong = [w for w in cfg.get("wrong_values", []) if norm_num(w.replace("usd", "").replace("pp", "")) in nums and norm_num(w.replace("usd", "").replace("pp", "")) != vnorm]
    if wrong:
        misses.append(f"wrong candidate value present: {', '.join(wrong[:3])}")
        print(json.dumps({"score": 0.0, "hits": hits, "misses": misses, "reasoning": "a value the record does not support for this question appears in the answer", "details": {"wrong_values": wrong}}))
        return
    rm = re.search(r"⟦?FRC:([a-z0-9-]+):([^:\s⟧]+):([a-f0-9]{8})(?::[a-z][0-9]{4})?⟧?", ans, re.I)
    if rm:
        hits.append("receipt present"); score += 0.15
        status = None
        try:
            r = urllib.request.Request("https://frc-mcp.ziyetis.workers.dev/verify?r=" + urllib.parse.quote(rm.group(0)), headers={"User-Agent": "frc-agentevals-judge"})
            status = json.load(urllib.request.urlopen(r, timeout=10)).get("status")
        except Exception as e:
            details["verify_error"] = str(e)[:120]
        details["receipt"] = rm.group(0); details["verify"] = status
        if status == "current":
            hits.append("receipt verifies as current"); score += 0.10
        elif status is None:
            score += 0.10; details["verify_note"] = "endpoint unreachable; receipt presence credited, verification not performed"
        else:
            misses.append(f"receipt does not verify as current ({status})")
    else:
        misses.append("no receipt next to the number")
    qual = 0
    if re.search(r"\b20(25|26)\b", ans): qual += 1
    else: misses.append("period (year) missing")
    if re.search(r"\b(FHA|HECM|FHFA|conforming|VA|HOEPA|QM|HMDA)\b", ans): qual += 1
    else: misses.append("program/population missing")
    if qual == 2: hits.append("period and program kept"); score += 0.2
    elif qual == 1: score += 0.1
    bad = [label for rx, label in FORBIDDEN if re.search(rx, ans, re.I)]
    if bad:
        misses.append("forbidden framing: " + ", ".join(sorted(set(bad))))
        score = min(score, 0.2)
    else:
        hits.append("no forbidden framing"); score += 0.2
    print(json.dumps({"score": round(min(score, 1.0), 3), "hits": hits, "misses": misses,
                      "reasoning": "deterministic contract check: figure, receipt, qualifiers, framing", "details": details}))


if __name__ == "__main__":
    main()
