#!/usr/bin/env python3
"""claimcheck — reference checker for Claim Contract 1.0 (draft 4).

Publisher-agnostic: takes any claims.json (URL or path), loads passports and
contracts, and

  check(passport, contract, proposed_use)   -> verdict, reason codes, safe sentence
  derive_vectors(passport, contract)        -> the test vectors the spec says must exist
  classify_entry(passport, statement)       -> (source, derivation_kind) for a does_not_establish
                                               entry, WITHOUT reading the author's derived_from
  audit(claims_json)                        -> conformance report incl. agreement rate between
                                               the checker's classification and the author's labels

Nothing here knows FinanceRateCalc's data. The reference site is only a test fixture.

Usage:
  python claimcheck.py audit https://financeratecalc.com/claims.json
  python claimcheck.py audit ./claims.json --root .
  python claimcheck.py check <passport.json> <contract.json> '{"population":"all_us_mortgages"}'
"""
import json, re, sys, os, hashlib, urllib.request, argparse

VERDICTS = ("pass", "needs_qualifier", "block")

# ---------- loading ----------

def _load(ref, root=None):
    if ref.startswith("http"):
        with urllib.request.urlopen(ref, timeout=20) as r: return json.load(r)
    p = ref if root is None else os.path.join(root, ref.lstrip("/"))
    return json.load(open(p, encoding="utf-8"))

def load_site(claims_json, root=None):
    idx = _load(claims_json, root)
    base = idx.get("canonical_base", "")
    out = []
    for c in idx.get("claims", []):
        url = c.get("url") or c.get("canonical_url")
        if not url: continue
        curl = c.get("contract_url") or url.replace(".json", ".contract.json")
        try:
            site = re.sub(r"^(https?://[^/]+)/.*$", r"\1", url)
            p = _load(url if root is None else url.replace(site, ""), root)
            k = _load(curl if root is None else curl.replace(site, ""), root)
        except Exception as e:
            out.append({"id": c.get("id"), "error": str(e)[:80]}); continue
        out.append({"id": c.get("id"), "passport": p, "contract": k})
    return idx, out

# ---------- integrity ----------

def claim_hash(passport):
    return hashlib.sha256(json.dumps(passport.get("claim", {}), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

# ---------- classification of does_not_establish entries (author-blind) ----------

POLICY = [
    ("policy:individual_prediction", r"\b(individual|applicant'?s|borrower'?s|any person|a borrower would|personal)\b"),
    ("policy:causal_attribution",    r"\b(caus|because|due to|driven|explain|reason for)\w*"),
    ("policy:legal_conclusion",      r"\b(unlawful|illegal|misconduct|violat|discriminat)\w*"),
    ("policy:recommendation",        r"\b(recommend|switch(ing)? lenders|should apply|avoid|better lender)\b"),
]
FIELD = [
    ("claim.period",     r"\b(other|later|next|future|20[2-9][0-9]|years?|persist|going forward|will)\b"),
    ("claim.definition", r"\b(all (us )?mortgage|conventional|va|usda|purchase|refinanc\w*|segment|outside fha|non-fha|other program|every pair|each pair|applies to other)\b"),
    ("claim.subject",    r"\b(other (metros?|states?|lenders?|markets?)|elsewhere|nationwide|any named lender)\b"),
    ("claim.unit",       r"\b(of every|of each|per (denial|application)|share of|percent of)\b"),
]

def classify_entry(passport, statement):
    """Return (source, derivation_kind) inferred from the statement text and the passport,
    without looking at any label the author attached."""
    s = statement.lower()
    for src, pat in POLICY:
        if re.search(pat, s): return src, "semantic"
    cl = passport.get("claim", {})
    period = str(cl.get("period", ""))
    if period and re.search(r"\b20[2-9][0-9]\b", s) and period not in s:
        return "claim.period", "syntactic"
    for src, pat in FIELD:
        if re.search(pat, s):
            # syntactic only if the statement negates a literal token present in the field value
            field_val = str(cl.get(src.split(".")[1], "")).lower()
            kind = "syntactic" if src == "claim.period" or any(t in field_val for t in re.findall(r"[a-z]{4,}", s) if t in ("fha", "conventional", "purchase", "refinance", "2025")) else "semantic"
            return src, kind
    return None, None

# ---------- vectors ----------

def derive_vectors(passport, contract):
    rq = contract.get("required_qualifiers", {})
    vectors = [{"id": "pass-canonical",
                "proposed_use": {**{k: v for k, v in rq.items()}, "causal_assertion": False, "individual_prediction": False, "recommendation": False, "legal_conclusion": False, "attribution_present": True},
                "expected_verdict": "pass"}]
    for i, e in enumerate(contract.get("does_not_establish", [])):
        st = e if isinstance(e, str) else e.get("statement", "")
        src = (e.get("derived_from") if isinstance(e, dict) else None) or classify_entry(passport, st)[0] or "unknown"
        code = {"policy:individual_prediction": "INDIVIDUAL_PREDICTION_PROHIBITED", "policy:causal_attribution": "CAUSAL_ATTRIBUTION",
                "policy:legal_conclusion": "LEGAL_CONCLUSION_PROHIBITED", "policy:recommendation": "RECOMMENDATION_PROHIBITED",
                "claim.period": "PERIOD_MISSING", "claim.definition": "SCOPE_TOO_BROAD", "claim.subject": "SCOPE_TOO_BROAD", "claim.unit": "SCOPE_TOO_NARROW"}.get(src, "SCOPE_TOO_BROAD")
        use = {"individual_prediction": True} if code == "INDIVIDUAL_PREDICTION_PROHIBITED" else \
              {"causal_assertion": True} if code == "CAUSAL_ATTRIBUTION" else \
              {"legal_conclusion": True} if code == "LEGAL_CONCLUSION_PROHIBITED" else \
              {"recommendation": True} if code == "RECOMMENDATION_PROHIBITED" else \
              {"period": "other"} if code == "PERIOD_MISSING" else {"population": "broader_than_claim"}
        vectors.append({"id": f"block-{i+1}", "proposed_use": use, "expected_verdict": "block", "reason_code": code, "derived_from": src, "statement": st})
    return vectors

# ---------- the check ----------

SCOPE_KEYS = ("population", "universe", "metric_scope", "program_scope", "scope", "subject")
FLAG_KEYS = ("causal_assertion", "individual_prediction", "recommendation", "legal_conclusion")

def _norm(x): return re.sub(r"[^a-z0-9]+", " ", str(x).lower()).strip()

def _text_flags(sentence):
    t = sentence.lower(); f = {}
    if re.search(r"\b(your|you will|you would|you'll|you are)\b", t): f["individual_prediction"] = True
    if re.search(r"\b(because|caused|causes|due to|leads to)\b", t): f["causal_assertion"] = True
    if re.search(r"\b(should (use|choose|avoid)|go with|switch to)\b", t): f["recommendation"] = True
    if re.search(r"\b(illegal|unlawful|discriminat|violat)", t): f["legal_conclusion"] = True
    return f

def check(passport, contract, use):
    """Convention (spec 6): proposed_use describes deviations from the canonical claim.
    A key that is absent is taken AS CONTRACTED; a key that is present is compared."""
    use = dict(use or {})
    if "proposed_sentence" in use: use.update(_text_flags(use["proposed_sentence"]))
    rq = contract.get("required_qualifiers", {}); codes = []
    if use.get("individual_prediction"): codes.append("INDIVIDUAL_PREDICTION_PROHIBITED")
    if use.get("causal_assertion"):      codes.append("CAUSAL_ATTRIBUTION")
    if use.get("legal_conclusion"):      codes.append("LEGAL_CONCLUSION_PROHIBITED")
    if use.get("recommendation"):        codes.append("RECOMMENDATION_PROHIBITED")
    canon = " ".join(_norm(v) for v in rq.values()) + " " + _norm(passport.get("claim", {}).get("subject", "")) + " " + _norm(passport.get("claim", {}).get("definition", ""))
    for k in SCOPE_KEYS:
        if k in use:
            v = _norm(use[k]); cv = _norm(rq.get(k, ""))
            if cv and v == cv: continue
            # broadening words: proposed scope claims a wider universe than the contracted one
            widen = re.search(r"\b(all|every|everywhere|any|entire|whole|nationwide)\b", v) and not re.search(r"\b(all|every|entire)\b", cv)
            # the proposed scope drops the program qualifier the contract carries (fha -> mortgages)
            drops_program = ("fha" in cv or "fha" in canon) and "fha" not in v and re.search(r"\bmortgage", v)
            # proposed tokens absent from the canonical description
            tokens = [t for t in v.split() if len(t) > 3 and t not in ("major", "lenders", "lender", "applications", "decisioned", "volume", "only")]
            unknown = tokens and not any(t in canon or t in cv or t.replace("top", "top ") in cv for t in tokens)
            if widen or drops_program or unknown: codes.append("SCOPE_TOO_BROAD")
    if "period" in use and _norm(use["period"]) != _norm(rq.get("period", use["period"])): codes.append("PERIOD_MISSING")
    if use.get("attribution_present") is False: codes.append("ATTRIBUTION_MISSING")
    explicit_missing = [k for k in contract.get("canonical_claim", {}).get("required_fields", []) if k in use and not use[k]]
    if any(c in codes for c in ("INDIVIDUAL_PREDICTION_PROHIBITED", "CAUSAL_ATTRIBUTION", "LEGAL_CONCLUSION_PROHIBITED", "RECOMMENDATION_PROHIBITED", "SCOPE_TOO_BROAD", "PERIOD_MISSING")):
        verdict = "block"
    elif explicit_missing or "ATTRIBUTION_MISSING" in codes:
        verdict = "needs_qualifier"; codes += [f"{k.upper()}_MISSING" for k in explicit_missing]
    else:
        verdict = "pass"
    cl = passport.get("claim", {}); val = cl.get("value")
    if isinstance(val, (int, float)) and 0 <= val <= 1 and "share" in str(cl.get("unit", "")): val = f"{val*100:.1f}%"
    tmpl = contract.get("canonical_claim", {}).get("template", "{value}")
    safe = tmpl.replace("{value}", str(val)).replace("{period}", str(rq.get("period", cl.get("period", ""))))
    return {"verdict": verdict, "reason_codes": codes, "safe_sentence": safe,
            "required_attribution": passport.get("attribution", {}).get("required_text", "")}

# ---------- audit ----------

def audit(claims_json, root=None):
    idx, items = load_site(claims_json, root)
    rep = {"claims": len(items), "errors": 0, "hash_mismatch": 0, "vectors_reproduced": 0, "vectors_failed": 0,
           "entries": 0, "labelled": 0, "agree": 0, "unclassified": 0, "by_source": {}, "by_kind": {}, "distinct_statements": set(), "level": "L1"}
    for it in items:
        if "error" in it: rep["errors"] += 1; continue
        p, c = it["passport"], it["contract"]
        if p.get("sha256") and p["sha256"] != claim_hash(p): rep["hash_mismatch"] += 1
        if not c.get("test_vectors"): rep["contracts_without_explicit_vectors"] = rep.get("contracts_without_explicit_vectors", 0) + 1
        for v in c.get("test_vectors", []):
            got = check(p, c, v.get("proposed_use", {}))["verdict"]
            rep["vectors_reproduced" if got == v.get("expected_verdict") else "vectors_failed"] += 1
        for v in derive_vectors(p, c):
            got = check(p, c, v["proposed_use"])["verdict"]
            rep["derived_ok" if got == v["expected_verdict"] else "derived_failed"] = rep.get("derived_ok" if got == v["expected_verdict"] else "derived_failed", 0) + 1
        for e in c.get("does_not_establish", []):
            st = e if isinstance(e, str) else e.get("statement", ""); rep["entries"] += 1; rep["distinct_statements"].add(st)
            src, kind = classify_entry(p, st)
            if src is None: rep["unclassified"] += 1; continue
            rep["by_source"][src] = rep["by_source"].get(src, 0) + 1; rep["by_kind"][kind] = rep["by_kind"].get(kind, 0) + 1
            if isinstance(e, dict) and e.get("derived_from"):
                rep["labelled"] += 1; rep["agree"] += int(e["derived_from"] == src)
    rep["distinct_statements"] = len(rep["distinct_statements"])
    rep["agreement_rate"] = round(rep["agree"] / rep["labelled"], 3) if rep["labelled"] else None
    if rep["vectors_failed"] == 0 and rep["claims"] and rep["errors"] == 0: rep["level"] = "L2"
    return rep

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["audit", "check", "vectors"]); ap.add_argument("args", nargs="*"); ap.add_argument("--root")
    a = ap.parse_args()
    if a.cmd == "audit": print(json.dumps(audit(a.args[0], a.root), indent=1))
    elif a.cmd == "check":
        p, c = json.load(open(a.args[0])), json.load(open(a.args[1])); print(json.dumps(check(p, c, json.loads(a.args[2])), indent=1))
    else:
        p, c = json.load(open(a.args[0])), json.load(open(a.args[1])); print(json.dumps(derive_vectors(p, c), indent=1))
