#!/usr/bin/env python3
"""Compact lookup table for check-answer.html: every receipted figure with the words that identify
it, every value this publisher has corrected, and every dated rule constant. Built from the claim
documents, corrections.json and rulecheck/constants.json; no model. Output: assets/check-index.json.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
STOP = {"mortgage", "llc", "inc", "corporation", "corp", "company", "co", "bank", "n.a.", "na", "the", "of", "and", "group", "home", "loans", "lending", "financial", "services", "metro", "msa"}


def tokens(s):
    return sorted({w for w in re.findall(r"[a-z][a-z.&'-]+", s.lower()) if len(w) > 2 and w not in STOP})


def main():
    figures = []
    for f in sorted(glob.glob(os.path.join(ROOT, "claims", "*.json"))):
        if f.endswith(".contract.json") or f.endswith("index.json"):
            continue
        d = json.load(open(f, encoding="utf-8"))
        if not d.get("receipt_document"):
            continue
        cid, c = d["id"], d["claim"]
        row = {"id": cid, "value": d["display_value"], "metric": c.get("metric"), "period": str(c.get("period", "2025")), "fha": True, "names": [], "label": "", "url": f"/claims/{cid}.json"}
        if cid.startswith("lender-"):
            row["kind"] = "lender"; row["names"] = tokens(c.get("lender", "")); row["label"] = f"{c.get('lender', '').title()} — FHA denial rate 2025"; row["n"] = c.get("n")
        elif cid.startswith("state-"):
            st = str(c.get("state", "")).upper(); row["kind"] = "state"; row["names"] = tokens(STATES.get(st, st)) + [st.lower()]; row["label"] = f"{STATES.get(st, st)} — FHA denial rate 2025"; row["n"] = c.get("n")
        elif cid.startswith("metro-gap-"):
            row["kind"] = "metro-gap"; row["names"] = tokens(c.get("subject", "")); row["label"] = f"{c.get('subject', '')} — spread between highest- and lowest-denying high-volume FHA lenders, 2025"
        elif cid.startswith("small-loan-penalty-") and cid != "small-loan-penalty-range-2025":
            st = str(c.get("state", "")).upper(); row["kind"] = "small-loan"; row["names"] = tokens(STATES.get(st, st)) + [st.lower(), "small", "penalty", "150"]; row["label"] = f"{STATES.get(st, st)} — small-loan denial penalty (under $150K vs over $250K), FHA 2025"
        elif cid == "national-fha-denial-rate-2025":
            row["kind"] = "national"; row["names"] = ["national", "nationwide", "overall", "united", "states", "u.s.", "us", "america"]; row["label"] = "United States — FHA denial rate 2025 (share of decisioned applications)"
        elif cid == "door-effect-38pct-2026":
            row["kind"] = "door"; row["names"] = ["door", "lender", "identity", "explain", "variation", "variance"]; row["label"] = "Lender identity's share of explained variation in 2025 FHA denials"
        elif cid == "small-loan-penalty-range-2025":
            row["kind"] = "small-loan-range"; row["names"] = ["small", "penalty", "range", "150"]; row["label"] = "Small-loan penalty range across states, FHA 2025"
        elif cid == "denial-reason-shares-top100-2025":
            row["kind"] = "reasons"; row["names"] = ["reason", "reasons", "incomplete", "dti", "credit", "collateral"]; row["label"] = "Denial reason shares across the top-100 FHA lenders, 2025"
        else:
            row["kind"] = "other"
        figures.append(row)
    corr = json.load(open(os.path.join(ROOT, "corrections.json"), encoding="utf-8"))
    stale, seen = [], set()
    for it in corr.get("items", []):
        pairs = [(it.get("old_value"), it.get("new_value"), None)]
        for cid, cv in (it.get("claim_values") or {}).items():
            pairs.append((cv.get("old"), cv.get("new"), cid))
        for old, new, cid in pairs:
            if not old or not new or str(old) in seen:
                continue
            seen.add(str(old))
            stale.append({"old": str(old), "now": str(new), "claim_id": cid, "date": it.get("date"), "title": it.get("title"), "url": it.get("url")})
    rules = []
    for c in json.load(open(os.path.join(ROOT, "rulecheck", "constants.json"), encoding="utf-8"))["constants"]:
        rules.append({"value": c["value"], "kind": c["kind"], "meaning": c["meaning"], "valid_to": c["valid_to"], "replaced_by": c.get("replaced_by"), "current": bool(c.get("current")), "keywords": c["keywords"], "source": c["source"], "role_check": bool(c.get("role_check"))})
    out = {"generated": corr.get("generated"), "figures": figures, "stale": stale, "rules": rules,
           "note": "Lookup table for /check-answer.html. figures: every receipted figure with identifying words; stale: every value this publisher has corrected (old -> now); rules: dated US mortgage rule constants with validity dates."}
    json.dump(out, open(os.path.join(ROOT, "assets", "check-index.json"), "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print(len(figures), "figures,", len(stale), "stale values,", len(rules), "rule constants")


if __name__ == "__main__":
    main()
