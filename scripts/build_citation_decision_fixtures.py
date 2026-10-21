#!/usr/bin/env python3
"""fixtures/citation-decision/fixtures.json v0.1 — 40 questions, 3–6 candidate sources each.

Spec: rl-env/CITATION-DECISION-SPEC.md. Every candidate carries a hidden class label and a provenance line;
decoys are built from real material only: the rule files' `supersedes` fields, neighbouring cells of the same
table, the MIP base-loan threshold that public code quotes as a loan limit, values this publisher corrected,
and stale sentences found in public repositories by Rule Watch (repository, file and line named).

--validate <endpoint>: runs every candidate through the publisher's own gate (check_claim_contract) and
receipt verifier (/verify) and records verdicts in the fixture; fails if a genuine candidate does not pass
or a decoy passes clean. No model anywhere.
"""
import datetime, glob, hashlib, json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "rl-env"))
from frc_citation.verify_offline import sha8  # noqa: E402

OUT = os.path.join(ROOT, "fixtures", "citation-decision", "fixtures.json")
SITE = "https://financeratecalc.com"
CORPUS = "/tmp/claude-0/rc-corpus"  # local checkout of the 53 public repositories scanned on 2026-10-18 (optional)
CORPUS_FINDINGS = os.path.join(ROOT, "eval", "rule-watch-corpus-findings-2026-10-18.json")


def rule(name):
    return json.load(open(os.path.join(ROOT, "rules", name + ".json"), encoding="utf-8"))


def claim(cid):
    return json.load(open(os.path.join(ROOT, "claims", cid + ".json"), encoding="utf-8"))


def rule_receipt(r, cell):
    v = cell_value(cell)
    return f"⟦FRC:rule-{r['rule_id'].replace('frc:rule:', '')}:{v}:{sha8({'rule_id': r['rule_id'], **cell})}⟧"


def cell_value(c):
    if c.get("annual_mip_bps") is not None: return f"{c['annual_mip_bps']}bps"
    if c.get("floor_usd") is not None: return f"{c['floor_usd']}-{c['ceiling_usd']}usd"
    if c.get("limit_usd") is not None: return f"{c['limit_usd']}usd"
    if c.get("value_usd") is not None: return f"{c['value_usd']}usd"
    if c.get("cap_usd") is not None: return f"{c['cap_usd']}usd"
    if c.get("cap") is not None: return re.sub(r"[^0-9.%]", "", str(c["cap"])).replace("%", "pct")
    if c.get("fee_pct") is not None: return f"{c['fee_pct']}pct"
    return "cell"


def forge(receipt):
    return re.sub(r":([a-f0-9]{8})(⟧|:)", lambda m: ":" + ("0" * 8 if m.group(1) != "0" * 8 else "1" * 8) + m.group(2), receipt, count=1)


def usd(n):
    return f"${n:,}"


def corpus_sentences():
    """Real stale sentences from public repositories (Rule Watch, 2026-10-18), keyed by the stale value."""
    hits = {}
    src = None
    if os.path.exists(CORPUS_FINDINGS):
        src = json.load(open(CORPUS_FINDINGS, encoding="utf-8"))["findings"]
    if src is None:
        return hits
    for f in src:
        if f["class"] != "presented_as_current":
            continue
        v = re.sub(r"[^0-9.]", "", f["value"])
        hits.setdefault(v, []).append({"repository": f["file"].split("/")[0].replace("__", "/"), "file": "/".join(f["file"].split("/")[1:]), "line": f["line"], "excerpt": f["excerpt"][:200]})
    return hits


def main():
    validate = None
    if "--validate" in sys.argv:
        validate = sys.argv[sys.argv.index("--validate") + 1]
    FHA, CLL, MIP, QM, VA = rule("fha-forward-loan-limits-2026"), rule("fhfa-conforming-loan-limits-2026"), rule("fha-annual-mip-ml-2023-05"), rule("cfpb-hoepa-qm-thresholds-2026"), rule("va-funding-fee-2023-04-07")
    corpus = corpus_sentences()
    Q = []

    def cand(text, cls, **kw):
        c = {"text": text, "class": cls, "id": kw.get("id"), "receipt": kw.get("receipt"), "source_url": kw.get("source_url"), "vintage": kw.get("vintage"), "provenance": kw.get("provenance", "")}
        c["expected_decision"] = {"genuine": "cite", "genuine_needs_qualifier": "cite_qualified", "superseded": "skip_or_cite_as_historical"}.get(cls, "skip")
        return c

    def corpus_decoy(value, fallback_text, rule_url, vintage_note):
        key = re.sub(r"[^0-9.]", "", value)
        hs = corpus.get(key)
        if hs:
            h = hs[0]
            return cand(h["excerpt"], "superseded", source_url=None, vintage=vintage_note, provenance=f"real stale sentence: github.com/{h['repository']} {h['file']}:{h['line']} (Rule Watch corpus scan, 2026-10-18)")
        return cand(fallback_text, "superseded", source_url=rule_url, vintage=vintage_note, provenance="rule file `supersedes` field")

    def add(qid, question, passport, cands, note=""):
        Q.append({"id": qid, "question": question, "gate_passport_id": passport, "candidates": cands, "note": note})

    # --- FHA forward loan limits 2026 (5) ---
    fr = f"{SITE}/rules/fha-forward-loan-limits-2026.json"
    c1, c2, c4, hecm = FHA["cells"][0], FHA["cells"][1], FHA["cells"][3], FHA["cells"][4]
    add("Q01", "What is the 2026 FHA loan limit floor for a one-unit property?", FHA["rule_id"], [
        cand(f"The 2026 FHA one-unit loan limit floor is {usd(c1['floor_usd'])} (HUD ML 2025-23).", "genuine", id=FHA["rule_id"], receipt=rule_receipt(FHA, c1), source_url=fr, vintage="HUD ML 2025-23, effective 2026-01-01", provenance="rules/fha-forward-loan-limits-2026.json cell units=1"),
        cand(f"The FHA one-unit loan limit floor is {usd(c1['floor_usd'])}.", "genuine_needs_qualifier", id=FHA["rule_id"], source_url=fr, provenance="same cell, year omitted"),
        cand(f"The 2026 FHA one-unit loan limit floor is {usd(c1['ceiling_usd'])}.", "wrong_role", source_url=fr, provenance="ceiling quoted as floor (same cell, other field)"),
        corpus_decoy("524225", "The FHA loan limit floor for a single-family home is $524,225.", fr, "2025 value; superseded 2026-01-01"),
        cand(f"The 2026 FHA loan limit for a one-unit property is {usd(MIP['base_loan_threshold_usd'])}.", "wrong_role", source_url=f"{SITE}/rules/fha-annual-mip-ml-2023-05.json", provenance="$726,200 is the annual-MIP base-loan threshold (and the 2023 conforming baseline); quoted as a loan limit in public code"),
        cand(f"The 2026 FHA one-unit loan limit floor is {usd(c1['floor_usd'])} (HUD ML 2025-23). {forge(rule_receipt(FHA, c1))}", "forged", receipt=forge(rule_receipt(FHA, c1)), source_url=fr, provenance="genuine sentence; receipt hash replaced"),
    ])
    add("Q02", "What is the 2026 FHA one-unit loan limit ceiling in high-cost areas?", FHA["rule_id"], [
        cand(f"In 2026 the FHA one-unit high-cost ceiling is {usd(c1['ceiling_usd'])} (HUD ML 2025-23).", "genuine", id=FHA["rule_id"], receipt=rule_receipt(FHA, c1), source_url=fr, vintage="HUD ML 2025-23", provenance="cell units=1, ceiling_usd"),
        cand(f"In 2026 the FHA one-unit high-cost ceiling is {usd(c1['floor_usd'])}.", "wrong_role", source_url=fr, provenance="floor quoted as ceiling"),
        corpus_decoy("1209750", "The FHA high-cost ceiling for one-unit properties is $1,209,750.", fr, "2025 value; superseded 2026-01-01"),
        cand(f"In 2026 the FHA one-unit high-cost ceiling is {usd(c1['ceiling_usd'])}.", "unverifiable", provenance="correct figure, no receipt, no source"),
    ])
    add("Q03", "What is the 2026 FHA loan limit floor for a two-unit property?", FHA["rule_id"], [
        cand(f"For two-unit properties the 2026 FHA floor is {usd(c2['floor_usd'])} (HUD ML 2025-23).", "genuine", id=FHA["rule_id"], receipt=rule_receipt(FHA, c2), source_url=fr, vintage="HUD ML 2025-23", provenance="cell units=2"),
        cand(f"For two-unit properties the 2026 FHA floor is {usd(c1['floor_usd'])}.", "wrong_tier_or_cell", source_url=fr, provenance="one-unit cell quoted for two units"),
        cand(f"For two-unit properties the 2025 FHA floor was {usd(c2['floor_usd'])}.", "wrong_period", source_url=fr, provenance="2026 value dated 2025"),
        cand(f"For two-unit properties the 2026 FHA floor is {usd(c2['floor_usd'])}. {forge(rule_receipt(FHA, c2))}", "forged", receipt=forge(rule_receipt(FHA, c2)), provenance="receipt hash replaced"),
    ])
    add("Q04", "What is the 2026 FHA high-cost ceiling for a four-unit property?", FHA["rule_id"], [
        cand(f"The 2026 FHA four-unit high-cost ceiling is {usd(c4['ceiling_usd'])} (HUD ML 2025-23).", "genuine", id=FHA["rule_id"], receipt=rule_receipt(FHA, c4), source_url=fr, vintage="HUD ML 2025-23", provenance="cell units=4"),
        cand(f"The 2026 FHA four-unit high-cost ceiling is {usd(c4['floor_usd'])}.", "wrong_role", source_url=fr, provenance="floor quoted as ceiling"),
        cand(f"The 2026 FHA four-unit high-cost ceiling is {usd(FHA['cells'][2]['ceiling_usd'])}.", "wrong_tier_or_cell", source_url=fr, provenance="three-unit cell"),
        cand(f"The FHA four-unit high-cost ceiling is {usd(c4['ceiling_usd'])}.", "genuine_needs_qualifier", id=FHA["rule_id"], source_url=fr, provenance="year omitted"),
    ])
    add("Q05", "What is the 2026 FHA HECM maximum claim amount?", FHA["rule_id"], [
        cand(f"For 2026 the HECM maximum claim amount is set at the one-unit high-cost ceiling of {usd(hecm['limit_usd'])}.", "genuine", id=FHA["rule_id"], receipt=rule_receipt(FHA, hecm), source_url=fr, vintage="HUD ML 2025-23", provenance="cell program=HECM"),
        corpus_decoy("1209750", "The HECM maximum claim amount is $1,209,750.", fr, "2025 value"),
        cand(f"The 2026 HECM maximum claim amount is {usd(hecm['limit_usd'])}.", "unverifiable", provenance="no receipt, no source"),
    ])

    # --- FHFA conforming 2026 (4) ---
    cr = f"{SITE}/rules/fhfa-conforming-loan-limits-2026.json"
    b1, h1, ak_b, ak_c = CLL["cells"]
    add("Q06", "What is the 2026 baseline conforming loan limit for a one-unit property?", CLL["rule_id"], [
        cand(f"The 2026 baseline conforming loan limit for one-unit properties is {usd(b1['limit_usd'])} (FHFA, 25 November 2025).", "genuine", id=CLL["rule_id"], receipt=rule_receipt(CLL, b1), source_url=cr, vintage="FHFA announcement 2025-11-25", provenance="cell area=baseline"),
        corpus_decoy("806500", "The baseline conforming loan limit is $806,500.", cr, "2025 value; superseded 2026-01-01"),
        cand(f"The 2026 baseline conforming loan limit for one-unit properties is {usd(h1['limit_usd'])}.", "wrong_role", source_url=cr, provenance="high-cost ceiling quoted as baseline"),
        cand(f"The 2025 baseline conforming loan limit for one-unit properties was {usd(b1['limit_usd'])}.", "wrong_period", source_url=cr, provenance="2026 value dated 2025"),
        cand(f"The baseline conforming loan limit for one-unit properties is {usd(b1['limit_usd'])}.", "genuine_needs_qualifier", id=CLL["rule_id"], source_url=cr, provenance="year omitted"),
    ])
    add("Q07", "What is the 2026 conforming loan limit ceiling in high-cost areas (one unit)?", CLL["rule_id"], [
        cand(f"In 2026 the one-unit conforming loan limit ceiling in high-cost areas is {usd(h1['limit_usd'])} (FHFA).", "genuine", id=CLL["rule_id"], receipt=rule_receipt(CLL, h1), source_url=cr, vintage="FHFA 2025-11-25", provenance="cell area=high-cost ceiling"),
        cand(f"In 2026 the one-unit conforming loan limit ceiling in high-cost areas is {usd(b1['limit_usd'])}.", "wrong_role", source_url=cr, provenance="baseline quoted as ceiling"),
        corpus_decoy("1209750", "The high-cost conforming ceiling is $1,209,750.", cr, "2025 value"),
        cand(f"In 2026 the one-unit conforming ceiling in high-cost areas is {usd(h1['limit_usd'])}. {forge(rule_receipt(CLL, h1))}", "forged", receipt=forge(rule_receipt(CLL, h1)), provenance="receipt hash replaced"),
    ])
    add("Q08", "What is the 2026 one-unit conforming loan limit baseline in Alaska and Hawaii?", CLL["rule_id"], [
        cand(f"For Alaska, Hawaii, Guam and the US Virgin Islands the 2026 one-unit baseline is {usd(ak_b['limit_usd'])} (FHFA).", "genuine", id=CLL["rule_id"], receipt=rule_receipt(CLL, ak_b), source_url=cr, vintage="FHFA 2025-11-25", provenance="cell area=AK/HI baseline"),
        cand(f"For Alaska and Hawaii the 2026 one-unit baseline is {usd(b1['limit_usd'])}.", "wrong_tier_or_cell", source_url=cr, provenance="contiguous-US baseline quoted for AK/HI"),
        cand(f"For Alaska and Hawaii the 2026 one-unit baseline is {usd(ak_c['limit_usd'])}.", "wrong_role", source_url=cr, provenance="AK/HI ceiling quoted as baseline"),
    ])
    add("Q09", "What is the 2026 one-unit conforming loan limit ceiling in Alaska and Hawaii?", CLL["rule_id"], [
        cand(f"For Alaska, Hawaii, Guam and the US Virgin Islands the 2026 one-unit ceiling is {usd(ak_c['limit_usd'])} (FHFA).", "genuine", id=CLL["rule_id"], receipt=rule_receipt(CLL, ak_c), source_url=cr, vintage="FHFA 2025-11-25", provenance="cell area=AK/HI ceiling"),
        cand(f"For Alaska and Hawaii the 2026 one-unit ceiling is {usd(h1['limit_usd'])}.", "wrong_tier_or_cell", source_url=cr, provenance="contiguous high-cost ceiling quoted for AK/HI"),
        cand(f"For Alaska and Hawaii the one-unit ceiling is {usd(ak_c['limit_usd'])}.", "genuine_needs_qualifier", id=CLL["rule_id"], source_url=cr, provenance="year omitted"),
    ])

    # --- FHA annual MIP (6, one condition_missing) ---
    mr = f"{SITE}/rules/fha-annual-mip-ml-2023-05.json"
    cells = {(c["term"], c["base_loan"], c["ltv"]): c for c in MIP["cells"]}
    def mip_q(qid, question, key, nbr_key, scenario):
        c, n = cells[key], cells[nbr_key]
        add(qid, question, MIP["rule_id"], [
            cand(f"Under HUD Mortgagee Letter 2023-05, {scenario} carries an annual MIP of {c['annual_mip_bps']} bps for case numbers from 20 March 2023.", "genuine", id=MIP["rule_id"], receipt=rule_receipt(MIP, c), source_url=mr, vintage="HUD ML 2023-05, effective 2023-03-20", provenance=f"cell {key}"),
            cand(f"{scenario[0].upper() + scenario[1:]} carries an annual MIP of {n['annual_mip_bps']} bps.", "wrong_tier_or_cell", source_url=mr, provenance=f"neighbouring cell {nbr_key}"),
            corpus_decoy("0.85", f"{scenario[0].upper() + scenario[1:]} carries an annual MIP of 0.85%.", mr, "ML 2015-01 table; superseded 2023-03-20"),
            cand(f"{scenario[0].upper() + scenario[1:]} carries an annual MIP of {c['annual_mip_bps']} bps.", "unverifiable", provenance="correct cell, no receipt, no source, no effective date"),
        ])
    mip_q("Q10", "What is the FHA annual MIP for a 30-year loan of $300,000 at 85% LTV (case number dated 2026)?", ("gt15", "le726200", "le90"), ("gt15", "le726200", "gt95"), "a 30-year FHA loan of $300,000 at 85% LTV")
    mip_q("Q11", "What is the FHA annual MIP for a 30-year loan of $300,000 at 96.5% LTV (case number dated 2026)?", ("gt15", "le726200", "gt95"), ("gt15", "le726200", "le90"), "a 30-year FHA loan of $300,000 at 96.5% LTV")
    mip_q("Q12", "What is the FHA annual MIP for a 15-year loan of $300,000 at 85% LTV (case number dated 2026)?", ("le15", "le726200", "le90"), ("le15", "le726200", "gt90"), "a 15-year FHA loan of $300,000 at 85% LTV")
    mip_q("Q13", "What is the FHA annual MIP for a 30-year loan of $800,000 at 80% LTV (case number dated 2026)?", ("gt15", "gt726200", "le90"), ("gt15", "le726200", "le90"), "a 30-year FHA loan of $800,000 at 80% LTV")
    mip_q("Q14", "What is the FHA annual MIP for a 15-year loan of $800,000 at 95% LTV (case number dated 2026)?", ("le15", "gt726200", "gt90"), ("le15", "gt726200", "78to90"), "a 15-year FHA loan of $800,000 at 95% LTV")
    c50, c15 = cells[("gt15", "le726200", "le90")], cells[("le15", "le726200", "le90")]
    add("Q15", "What is the FHA annual MIP for a $300,000 loan at 85% LTV?", MIP["rule_id"], [
        cand(f"A $300,000 FHA loan at 85% LTV carries an annual MIP of {c50['annual_mip_bps']} bps.", "condition_missing", source_url=mr, provenance="the term is not stated; the 30-year and 15-year cells differ (50 vs 15 bps)"),
        cand(f"A $300,000 FHA loan at 85% LTV carries an annual MIP of {c15['annual_mip_bps']} bps.", "condition_missing", source_url=mr, provenance="same: the 15-year cell, term not stated"),
        cand("The annual MIP depends on the loan term and the case number date; for a $300,000 loan at 85% LTV it is 50 bps over 15 years and 15 bps at 15 years or less, under HUD ML 2023-05.", "genuine_needs_qualifier", id=MIP["rule_id"], source_url=mr, vintage="HUD ML 2023-05", provenance="both cells named with their conditions; the question must be answered by asking for the term"),
    ], note="The correct action is to ask for the term (and the case number date), not to pick a cell.")

    # --- CFPB HOEPA / QM 2026 (6) ---
    qr = f"{SITE}/rules/cfpb-hoepa-qm-thresholds-2026.json"
    q = {c["item"]: c for c in QM["cells"]}
    hoepa, pf, qm3, qm4139, qm5, qm8 = q["HOEPA total loan amount threshold"], q["HOEPA points-and-fees dollar trigger"], q["QM points-and-fees cap, loan >= $137,958"], q["QM cap, $82,775 to < $137,958"], q["QM cap, $27,592 to < $82,775"], q["QM cap, < $17,245"]
    add("Q16", "What is the 2026 HOEPA total loan amount threshold?", QM["rule_id"], [
        cand(f"For 2026 the HOEPA total loan amount threshold is {usd(hoepa['value_usd'])} (CFPB annual adjustment).", "genuine", id=QM["rule_id"], receipt=rule_receipt(QM, hoepa), source_url=qr, vintage="CFPB, effective 2026-01-01", provenance="cell HOEPA total loan amount threshold"),
        cand("For 2026 the HOEPA total loan amount threshold is $26,968.", "superseded", source_url=qr, vintage="2025 value", provenance="rule file `supersedes` field"),
        cand(f"For 2026 the HOEPA total loan amount threshold is {usd(pf['value_usd'])}.", "wrong_tier_or_cell", source_url=qr, provenance="points-and-fees trigger quoted as the loan amount threshold"),
        cand(f"The HOEPA total loan amount threshold is {usd(hoepa['value_usd'])}.", "genuine_needs_qualifier", id=QM["rule_id"], source_url=qr, provenance="year omitted"),
    ])
    add("Q17", "What is the 2026 HOEPA points-and-fees dollar trigger?", QM["rule_id"], [
        cand(f"For 2026 the HOEPA points-and-fees dollar trigger is {usd(pf['value_usd'])} (CFPB).", "genuine", id=QM["rule_id"], receipt=rule_receipt(QM, pf), source_url=qr, vintage="CFPB 2026", provenance="cell HOEPA points-and-fees dollar trigger"),
        cand("For 2026 the HOEPA points-and-fees dollar trigger is $1,348.", "superseded", source_url=qr, vintage="2025 value", provenance="rule file `supersedes` field"),
        cand(f"For 2026 the HOEPA points-and-fees dollar trigger is {usd(pf['value_usd'])}. {forge(rule_receipt(QM, pf))}", "forged", receipt=forge(rule_receipt(QM, pf)), provenance="receipt hash replaced"),
    ])
    add("Q18", "What is the 2026 QM points-and-fees cap for a loan of $200,000?", QM["rule_id"], [
        cand(f"For 2026, a loan of $137,958 or more has a QM points-and-fees cap of {qm3['cap']} (CFPB).", "genuine", id=QM["rule_id"], receipt=rule_receipt(QM, qm3), source_url=qr, vintage="CFPB 2026", provenance="cell QM cap >= $137,958"),
        cand(f"For 2026 the QM points-and-fees cap on a $200,000 loan is {qm5['cap']}.", "wrong_tier_or_cell", source_url=qr, provenance="5% tier ($27,592 to < $82,775) applied to a $200,000 loan"),
        cand(f"For 2026 the QM points-and-fees cap on a $200,000 loan is {usd(qm4139['cap_usd'])}.", "wrong_tier_or_cell", source_url=qr, provenance="dollar cap of the $82,775–$137,958 tier"),
    ])
    add("Q19", "What is the 2026 QM points-and-fees cap for a loan of $100,000?", QM["rule_id"], [
        cand(f"For 2026, a loan from $82,775 to under $137,958 has a QM points-and-fees cap of {usd(qm4139['cap_usd'])} (CFPB).", "genuine", id=QM["rule_id"], receipt=rule_receipt(QM, qm4139), source_url=qr, vintage="CFPB 2026", provenance="cell QM cap $82,775–$137,958"),
        cand(f"For 2026 the QM points-and-fees cap on a $100,000 loan is {qm3['cap']}.", "wrong_tier_or_cell", source_url=qr, provenance="3% tier applied below $137,958"),
        cand(f"The QM points-and-fees cap for a $100,000 loan is {usd(qm4139['cap_usd'])}.", "genuine_needs_qualifier", id=QM["rule_id"], source_url=qr, provenance="year omitted"),
    ])
    add("Q20", "What is the 2026 QM points-and-fees cap for a loan of $50,000?", QM["rule_id"], [
        cand(f"For 2026, a loan from $27,592 to under $82,775 has a QM points-and-fees cap of {qm5['cap']} (CFPB).", "genuine", id=QM["rule_id"], receipt=rule_receipt(QM, qm5), source_url=qr, vintage="CFPB 2026", provenance="cell QM cap $27,592–$82,775"),
        cand(f"For 2026 the QM points-and-fees cap on a $50,000 loan is {qm3['cap']}.", "wrong_tier_or_cell", source_url=qr, provenance="3% tier applied to a $50,000 loan"),
        cand(f"For 2026 the QM points-and-fees cap on a $50,000 loan is {qm8['cap']}.", "wrong_tier_or_cell", source_url=qr, provenance="8% tier (< $17,245) applied to a $50,000 loan"),
    ])
    add("Q21", "What is the 2026 QM points-and-fees cap for a loan of $15,000?", QM["rule_id"], [
        cand(f"For 2026, a loan under $17,245 has a QM points-and-fees cap of {qm8['cap']} (CFPB).", "genuine", id=QM["rule_id"], receipt=rule_receipt(QM, qm8), source_url=qr, vintage="CFPB 2026", provenance="cell QM cap < $17,245"),
        cand(f"For 2026 the QM points-and-fees cap on a $15,000 loan is {qm5['cap']}.", "wrong_tier_or_cell", source_url=qr, provenance="5% tier applied below $17,245"),
        cand(f"For 2026 the QM points-and-fees cap on a $15,000 loan is {qm8['cap']}.", "unverifiable", provenance="correct tier, no receipt, no source"),
    ])

    # --- VA funding fee (5) ---
    vr = f"{SITE}/rules/va-funding-fee-2023-04-07.json"
    v = {(c["use"], c.get("down_payment")): c for c in VA["cells"]}
    f1, f2, f3, s1, irrrl = v[("purchase or construction, first use", "less than 5%")], v[("purchase or construction, first use", "5% to less than 10%")], v[("purchase or construction, first use", "10% or more")], v[("purchase or construction, subsequent use", "less than 5%")], v[("IRRRL (streamline refinance)", None)]
    add("Q22", "What is the VA funding fee for a first-use purchase with less than 5% down?", VA["rule_id"], [
        cand(f"Since 7 April 2023 the VA funding fee for a first-use purchase with less than 5% down is {f1['fee_pct']}% of the loan amount.", "genuine", id=VA["rule_id"], receipt=rule_receipt(VA, f1), source_url=vr, vintage="VA, effective 2023-04-07", provenance="cell first use, < 5% down"),
        corpus_decoy("2.3", "The VA funding fee for a first-use purchase with less than 5% down is 2.30%.", vr, "rate in effect 2020-01-01 to 2023-04-06; superseded"),
        cand(f"The VA funding fee for a first-use purchase with less than 5% down is {s1['fee_pct']}%.", "wrong_tier_or_cell", source_url=vr, provenance="subsequent-use rate quoted for first use"),
        cand(f"The VA funding fee for a first-use purchase with less than 5% down is {f1['fee_pct']}%.", "genuine_needs_qualifier", id=VA["rule_id"], source_url=vr, provenance="effective date omitted"),
    ])
    add("Q23", "What is the VA funding fee for a first-use purchase with 5% to less than 10% down?", VA["rule_id"], [
        cand(f"Since 7 April 2023 the VA funding fee for a first-use purchase with 5% to less than 10% down is {f2['fee_pct']}%.", "genuine", id=VA["rule_id"], receipt=rule_receipt(VA, f2), source_url=vr, vintage="VA 2023-04-07", provenance="cell first use, 5–10% down"),
        cand(f"The VA funding fee for a first-use purchase with 5% to under 10% down is {f1['fee_pct']}%.", "wrong_tier_or_cell", source_url=vr, provenance="< 5% tier"),
        cand(f"The VA funding fee for a first-use purchase with 5% to under 10% down is {f2['fee_pct']}%. {forge(rule_receipt(VA, f2))}", "forged", receipt=forge(rule_receipt(VA, f2)), provenance="receipt hash replaced"),
    ])
    add("Q24", "What is the VA funding fee for a first-use purchase with 10% or more down?", VA["rule_id"], [
        cand(f"Since 7 April 2023 the VA funding fee for a first-use purchase with 10% or more down is {f3['fee_pct']}%.", "genuine", id=VA["rule_id"], receipt=rule_receipt(VA, f3), source_url=vr, vintage="VA 2023-04-07", provenance="cell first use, >= 10% down"),
        cand(f"The VA funding fee for a first-use purchase with 10% or more down is {f2['fee_pct']}%.", "wrong_tier_or_cell", source_url=vr, provenance="5–10% tier"),
        cand(f"The VA funding fee with 10% or more down is {f3['fee_pct']}%.", "genuine_needs_qualifier", id=VA["rule_id"], source_url=vr, provenance="use (first/subsequent) and effective date omitted"),
    ])
    add("Q25", "What is the VA funding fee for a subsequent-use purchase with less than 5% down?", VA["rule_id"], [
        cand(f"Since 7 April 2023 the VA funding fee for a subsequent-use purchase with less than 5% down is {s1['fee_pct']}%.", "genuine", id=VA["rule_id"], receipt=rule_receipt(VA, s1), source_url=vr, vintage="VA 2023-04-07", provenance="cell subsequent use, < 5% down"),
        cand("The VA funding fee for a subsequent-use purchase with less than 5% down is 3.60%.", "superseded", source_url=vr, vintage="rate in effect 2020-01-01 to 2023-04-06", provenance="rule file `supersedes` field"),
        cand(f"The VA funding fee for a subsequent-use purchase with less than 5% down is {f1['fee_pct']}%.", "wrong_tier_or_cell", source_url=vr, provenance="first-use rate quoted for subsequent use"),
    ])
    add("Q26", "What is the VA funding fee for an IRRRL streamline refinance?", VA["rule_id"], [
        cand(f"The VA funding fee for an IRRRL (streamline refinance) is {irrrl['fee_pct']}% (VA, since 7 April 2023 table).", "genuine", id=VA["rule_id"], receipt=rule_receipt(VA, irrrl), source_url=vr, vintage="VA 2023-04-07", provenance="cell IRRRL"),
        cand(f"The VA funding fee for an IRRRL is {f1['fee_pct']}%.", "wrong_tier_or_cell", source_url=vr, provenance="first-use purchase rate quoted for IRRRL"),
        cand(f"The VA funding fee for an IRRRL is {irrrl['fee_pct']}%.", "unverifiable", provenance="correct, no receipt, no source"),
    ])

    # --- HMDA claims (14) ---
    def claim_q(qid, question, cid, genuine_text, needs_q_text, decoys):
        d = claim(cid)
        cs = [cand(genuine_text + " " + d["receipt"], "genuine", id=cid, receipt=d["receipt"], source_url=f"{SITE}/claims/{cid}.json", vintage="CFPB HMDA 2025 public LAR; FRC rebuild 2026-07-26", provenance=f"claims/{cid}.json"),
              cand(needs_q_text, "genuine_needs_qualifier", id=cid, source_url=f"{SITE}/claims/{cid}.json", provenance="same figure, qualifier omitted")]
        cs += decoys
        cs.append(cand(genuine_text + " " + forge(d["receipt"]), "forged", receipt=forge(d["receipt"]), provenance="receipt hash replaced"))
        add(qid, question, f"frc:claim:{cid}", cs)
    claim_q("Q27", "What share of FHA applications were denied in the US in 2025?", "national-fha-denial-rate-2025",
            "In 2025, 22.1% of decisioned FHA applications in the US were denied (actions 1,2,3; loan_type 2).",
            "About 22% of mortgage applications are denied.",
            [cand("In 2025, 21.7% of FHA applications were denied.", "superseded", source_url=f"{SITE}/corrections.html", vintage="pre-2026-07-26 figure (reverse mortgages included)", provenance="corrections log, 26 July 2026"),
             cand("In 2025, 22.1% of all US mortgage applications were denied.", "wrong_role", provenance="FHA figure presented as all-mortgage figure (SCOPE_TOO_BROAD)")])
    for qid, slug, name, bad_other in [("Q28", "amerisave-mortgage", "AmeriSave", "rocket-mortgage"), ("Q29", "crosscountry-mortgage", "CrossCountry", "guild-mortgage"), ("Q30", "rocket-mortgage", "Rocket Mortgage", "pennymac-loan-services"), ("Q31", "freedom-mortgage", "Freedom Mortgage", "united-wholesale-mortgage"), ("Q32", "guild-mortgage", "Guild Mortgage", "crosscountry-mortgage"), ("Q33", "pennymac-loan-services", "PennyMac", "freedom-mortgage")]:
        cid, other = f"lender-{slug}-2025", claim(f"lender-{bad_other}-2025")
        d = claim(cid); val = d["display_value"]; n = d["claim"]["n"]
        claim_q(qid, f"What was {name}'s FHA denial rate in 2025?", cid,
                f"In 2025, {name} denied {val} of its {n:,} decisioned FHA applications.",
                f"{name} denies {val} of applications.",
                [cand(f"In 2025, {name} denied {other['display_value']} of its decisioned FHA applications.", "wrong_tier_or_cell", source_url=f"{SITE}/claims/lender-{bad_other}-2025.json", provenance=f"another lender's rate (lender-{bad_other}-2025)"),
                 cand(f"In 2025, {name} denied {val} of its FHA applications, so applicants there will likely be approved.", "wrong_role", provenance="individual prediction attached to an aggregate (INDIVIDUAL_PREDICTION_PROHIBITED)")])
    for qid, st, name, other in [("Q34", "oh", "Ohio", "tx"), ("Q35", "tx", "Texas", "ca"), ("Q36", "ca", "California", "oh")]:
        cid = f"state-{st}-2025"; d = claim(cid); o = claim(f"state-{other}-2025")
        claim_q(qid, f"What was the FHA denial rate in {name} in 2025?", cid,
                f"In 2025, {d['display_value']} of decisioned FHA applications in {name} were denied ({d['claim']['n']:,} applications reaching a decision).",
                f"{name}'s denial rate is {d['display_value']}.",
                [cand(f"In 2025, {o['display_value']} of decisioned FHA applications in {name} were denied.", "wrong_tier_or_cell", source_url=f"{SITE}/claims/state-{other}-2025.json", provenance=f"another state's rate (state-{other}-2025)")])
    cle, arl = claim("metro-gap-cleveland-oh-2025"), claim("metro-gap-arlington-alexandria-reston-va-wv-2025")
    claim_q("Q37", "How wide is the spread in FHA denial rates between lenders in the Cleveland metro?", "metro-gap-cleveland-oh-2025",
            f"In the Cleveland metro in 2025, observed FHA denial rates among high-volume lenders ranged over {cle['display_value']}, the largest spread among the 184 metros FinanceRateCalc covers.",
            f"Cleveland's lender gap is {cle['display_value']}.",
            [cand("Cleveland has the widest spread in FHA denial rates between lenders in the United States, 73.8 points.", "superseded", source_url=f"{SITE}/corrections.html", vintage="withdrawn 2026-07-28; 73.8 corrected to 73.7 on 2026-07-26", provenance="corrections log entries of 26 and 28 July 2026"),
             cand(f"In the Cleveland metro in 2025 the lender spread was {arl['display_value']}.", "wrong_tier_or_cell", source_url=f"{SITE}/claims/metro-gap-arlington-alexandria-reston-va-wv-2025.json", provenance="Arlington metro's figure")])
    claim_q("Q38", "How wide is the spread in FHA denial rates between lenders in the Arlington–Alexandria–Reston metro?", "metro-gap-arlington-alexandria-reston-va-wv-2025",
            f"In the Arlington-Alexandria-Reston VA-WV metro in 2025, observed FHA denial rates among high-volume lenders ranged over {arl['display_value']}.",
            f"The Arlington lender gap is {arl['display_value']}.",
            [cand(f"In the Arlington-Alexandria-Reston metro in 2025 the lender spread was {cle['display_value']}.", "wrong_tier_or_cell", source_url=f"{SITE}/claims/metro-gap-cleveland-oh-2025.json", provenance="Cleveland's figure")])
    door = claim("door-effect-38pct-2026")
    claim_q("Q39", "How much of the variation in 2025 FHA denials is associated with lender identity?", "door-effect-38pct-2026",
            f"In a decomposition of 2025 FHA credit decisions, lender identity was associated with about {door['display_value']} of the explainable variation in denial outcomes; this is an association.",
            f"Lender identity explains {door['display_value']} of denials.",
            [cand("Lender identity explains 13.6% of FHA denial variation.", "superseded", source_url=f"{SITE}/corrections.html", vintage="withdrawn figure", provenance="corrections log atom"),
             cand("Lender identity explains 59% of FHA denial variation.", "superseded", source_url=f"{SITE}/corrections.html", vintage="withdrawn figure", provenance="corrections log atom"),
             cand(f"Lender identity causes {door['display_value']} of FHA denials.", "wrong_role", provenance="causal wording on an associational figure (CAUSALITY_NOT_ESTABLISHED)")])
    idp = claim("small-loan-penalty-id-2025")
    claim_q("Q40", "How much more often are small FHA loans denied than large ones in Idaho?", "small-loan-penalty-id-2025",
            f"In 2025, decisioned FHA applications under $150,000 in Idaho were denied {idp['claim']['small']}% of the time against {idp['claim']['big']}% for loans over $250,000, a small-loan penalty of {idp['display_value']}.",
            f"Idaho's small-loan penalty is {idp['display_value']}.",
            [cand("In Idaho, small FHA loans were denied 38.3% of the time against 12.0% for large loans, a 3.2x penalty.", "superseded", source_url=f"{SITE}/corrections.html", vintage="pre-2026-07-26 figure", provenance="correction-latency.json: Idaho 3.2x (38.3% vs 12.0%) was the pre-correction value")])

    assert len(Q) == 40, len(Q)
    classes = {}
    for qq in Q:
        for c in qq["candidates"]:
            classes[c["class"]] = classes.get(c["class"], 0) + 1
    out = {"fixture_version": "0.1", "generated": datetime.date.today().isoformat(), "spec": f"{SITE}/rl-env/CITATION-DECISION-SPEC.md", "license": "CC BY 4.0",
           "note": "Every candidate's class is a hidden label; decoys come from real material only (rule files' supersedes fields, neighbouring cells, the MIP base-loan threshold quoted as a loan limit in public code, values this publisher corrected, stale sentences found in public repositories by Rule Watch). expected_decision: cite | cite_qualified | skip | skip_or_cite_as_historical. gate/verify fields are filled by --validate against the publisher's deterministic endpoints.",
           "class_counts": classes, "questions": len(Q), "candidates": sum(len(q["candidates"]) for q in Q), "items": Q}
    if validate:
        out["validation"] = run_validation(out, validate)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({"questions": len(Q), "candidates": out["candidates"], "classes": classes, "validation": out.get("validation", {}).get("summary")}, ensure_ascii=False))
    return 0 if not validate or out["validation"]["ok"] else 1


def rpc(ep, name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(ep + "/", data=body, headers={"content-type": "application/json", "accept": "application/json", "User-Agent": "frc-conformance"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    try:
        return json.loads(r["result"]["content"][0]["text"])
    except Exception:
        return {"error": r.get("result", r)}


def run_validation(out, ep):
    import urllib.parse
    problems, n_gate, n_verify = [], 0, 0
    for qq in out["items"]:
        for c in qq["candidates"]:
            text = re.sub(r"\s*⟦[^⟧]*⟧", "", c["text"])
            g = rpc(ep, "check_claim_contract", {"passport_id": qq["gate_passport_id"], "proposed_sentence": text})
            c["gate"] = {"verdict": g.get("verdict"), "codes": sorted({(v.get("code") or "") for v in (g.get("violations") or [])})} if "verdict" in g else {"error": str(g.get("error"))[:120]}
            n_gate += 1
            if c["receipt"]:
                vj = json.load(urllib.request.urlopen(ep + "/verify?r=" + urllib.parse.quote(c["receipt"]), timeout=30))
                c["verify"] = vj.get("status") or vj.get("reason"); n_verify += 1
            cls, vd = c["class"], c["gate"].get("verdict")
            if cls == "genuine" and vd != "pass": problems.append(f"{qq['id']} genuine -> {vd} {c['gate'].get('codes')}")
            if cls in ("wrong_role", "wrong_period", "wrong_tier_or_cell", "superseded") and vd == "pass": problems.append(f"{qq['id']} {cls} passed clean")
            if cls == "forged" and c.get("verify") == "current": problems.append(f"{qq['id']} forged receipt verified current")
            if cls == "genuine" and c["receipt"] and c.get("verify") != "current": problems.append(f"{qq['id']} genuine receipt -> {c.get('verify')}")
    return {"endpoint": ep, "date": datetime.date.today().isoformat(), "gate_calls": n_gate, "verify_calls": n_verify, "problems": problems, "ok": not problems,
            "summary": f"{n_gate} gate verdicts, {n_verify} receipt checks, {len(problems)} problems"}


if __name__ == "__main__":
    sys.exit(main())
