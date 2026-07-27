#!/usr/bin/env python3
"""
FinanceRateCalc MCP Server
==========================
Serves published FHA mortgage denial statistics from the complete 2025 CFPB HMDA
record over the Model Context Protocol, so an AI agent can query the federal record
directly instead of scraping a webpage or guessing.

WHAT THIS SERVES
  Only figures already published at financeratecalc.com. Nothing is computed on the
  fly, nothing is estimated, and nothing that was withheld from publication for being
  based on too few observations is served here.

WHAT THIS DOES NOT DO
  It does not rate, rank by quality, score, or recommend lenders. It returns observed
  counts and rates from a federal file. A denial rate reflects applicant composition as
  well as lender practice, and every response carries that caveat rather than assuming
  the caller will remember it.

  It makes no prediction about any individual application. There is no endpoint that
  takes borrower details and returns an approval probability, and there will not be one.

VERIFICATION STATUS
  No figure served by this package has been independently reproduced. Every response
  carries verification_status so the caveat travels with the number rather than being
  dropped in transit. Specification for checking any figure:
  https://financeratecalc.com/reconciliation.html

LICENSE  CC BY 4.0 — reuse freely with attribution.
DATA     CFPB HMDA 2025. Derived figures: FinanceRateCalc, DOI 10.5281/zenodo.21575105
"""

import json, os, difflib
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    raise SystemExit(
        "This package requires the MCP SDK.\n"
        "  pip install mcp\n"
        "Then run:  python -m frc_mcp\n"
    )

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "frc_data.json"), encoding="utf-8") as fh:
    DATA = json.load(fh)

META = DATA["meta"]
LENDERS = DATA["lenders"]
METROS = DATA["metros"]
STATES = DATA["states"]
PEER = DATA["peer_medians"]

mcp = FastMCP("financeratecalc")


def _envelope(payload: dict) -> dict:
    """Every response carries provenance and the verification caveat."""
    return {
        **payload,
        "_source": {
            "publisher": META["publisher"],
            "data": META["source"],
            "year": META["year"],
            "universe": META["universe"],
            "method": META["method"],
            "dataset_doi": META["dataset_doi"],
            "license": META["license"],
            "verification_status": META["verification_status"],
            "caveat": META["not_a_rating"],
        },
    }


# Common abbreviations and trading names that do not match the legal entity name.
_ALIAS = {
    "uwm": "united wholesale", "united wholesale mortgage": "united wholesale",
    "dhi": "dhi mortgage", "drhorton": "dhi mortgage", "d.r. horton": "dhi mortgage",
    "quicken": "rocket", "quicken loans": "rocket",
    "ccm": "crosscountry", "cross country": "crosscountry",
    "amerisave": "amerisave", "loandepot": "loandepot", "loan depot": "loandepot",
    "pennymac": "pennymac", "penny mac": "pennymac",
    "freedom": "freedom mortgage", "guild": "guild mortgage",
    "fairway": "fairway", "movement": "movement mortgage",
    "nvr": "nvr mortgage", "pulte": "pulte", "lennar": "lennar",
    "mr cooper": "nationstar", "mr. cooper": "nationstar", "newrez": "newrez", "planet home": "planet home",
    "carrington": "carrington", "lakeview": "lakeview",
}


def _find_lender(name: str) -> dict | None:
    q = _ALIAS.get(name.lower().strip(), name.lower().strip())
    for L in LENDERS:
        if L["name"].lower() == q:
            return L
    for L in LENDERS:
        if q in L["name"].lower() or L["name"].lower().startswith(q[:8]):
            return L
    close = difflib.get_close_matches(q, [L["name"].lower() for L in LENDERS], n=1, cutoff=0.65)
    if close:
        return next(L for L in LENDERS if L["name"].lower() == close[0])
    return None


def _find_metro(name: str) -> dict | None:
    q = name.lower().strip()
    for M in METROS:
        if M["name"].lower() == q:
            return M
    for M in METROS:
        if M["name"].lower().startswith(q):
            return M
    for M in METROS:
        if q in M["name"].lower():
            return M
    close = difflib.get_close_matches(q, [M["name"].lower() for M in METROS], n=1, cutoff=0.6)
    if close:
        return next(M for M in METROS if M["name"].lower() == close[0])
    return None


@mcp.tool()
def get_lender_record(lender: str) -> dict[str, Any]:
    """Return a lender's observed 2025 FHA record: decisioned applications, denial and
    approval rate, its peer-adjusted ratio, and the distribution of its cited denial
    reasons against peer medians.

    Args:
        lender: Institution name or a recognisable fragment, e.g. "Rocket", "UWM".
    """
    L = _find_lender(lender)
    if not L:
        return _envelope({
            "found": False,
            "query": lender,
            "note": "No institution matched. This package covers institutions with at "
                    "least 1,500 decisioned FHA applications in 2025; smaller lenders are "
                    "not published because the figures would be unstable.",
        })
    dev = None
    if L["denial_reason_shares_pct"]:
        dev = {k: round(L["denial_reason_shares_pct"].get(k, 0) - PEER[k], 1) for k in PEER if k != "denial_rate_pct"}
    adj_reading = None
    if L["peer_adjusted_ratio"] is not None:
        r = L["peer_adjusted_ratio"]
        adj_reading = (
            "denies more often than its own applicant mix predicts" if r > 1.15
            else "denies less often than its own applicant mix predicts" if r < 0.85
            else "denies close to what its own applicant mix predicts"
        )
    return _envelope({
        "found": True,
        "lender": L["name"],
        "lei": L["lei"],
        "decisioned_applications": L["decisioned_applications"],
        "denials": L["denials"],
        "denial_rate_pct": L["denial_rate_pct"],
        "approval_rate_pct": L["approval_rate_pct"],
        "peer_median_denial_rate_pct": PEER["denial_rate_pct"],
        "in_top_100_by_volume": L["in_top_100"],
        "peer_adjusted_ratio": L["peer_adjusted_ratio"],
        "peer_adjusted_reading": adj_reading,
        "expected_denial_rate_pct": L["expected_denial_rate_pct"],
        "profile_coverage_pct": L["profile_coverage_pct"],
        "denial_reason_shares_pct": L["denial_reason_shares_pct"],
        "deviation_from_peer_median_pts": dev,
        "page": "https://financeratecalc.com/fha-denial-rates-top-100.html",
    })


@mcp.tool()
def get_metro_record(metro: str) -> dict[str, Any]:
    """Return a metropolitan area's observed 2025 FHA record, including the highest-volume
    lenders active there and the spread between them.

    Args:
        metro: Metro name or fragment, e.g. "Cleveland", "Dallas".
    """
    M = _find_metro(metro)
    if not M:
        return _envelope({"found": False, "query": metro,
                          "note": "No metro matched. 319 metropolitan areas are published."})
    doors = sorted([d for d in M["lenders"] if d["decisioned_applications_here"] >= 100],
                   key=lambda d: d["denial_rate_pct"])
    spread = round(doors[-1]["denial_rate_pct"] - doors[0]["denial_rate_pct"], 1) if len(doors) >= 2 else None
    return _envelope({
        "found": True,
        "metro": M["name"],
        "msa_code": M["msa_code"],
        "decisioned_applications": M["decisioned_applications"],
        "denial_rate_pct": M["denial_rate_pct"],
        "national_denial_rate_pct": META["national_denial_rate_pct"],
        "small_loan_denial_pct": M["small_loan_denial_pct"],
        "big_loan_denial_pct": M["big_loan_denial_pct"],
        "small_loan_penalty": M["small_loan_penalty"],
        "lenders_here": doors,
        "spread_between_lenders_pts": spread,
        "page": "https://financeratecalc.com/fha-denial-rates-by-metro.html",
    })


@mcp.tool()
def get_state_record(state: str) -> dict[str, Any]:
    """Return a state's observed 2025 FHA denial rate and its small-loan penalty — the
    ratio between denial rates on applications under $150,000 and those at $250,000 or more.

    Args:
        state: Two-letter state code, e.g. "TX", "OH".
    """
    q = state.strip().upper()[:2]
    S = next((s for s in STATES if s["state"] == q), None)
    if not S:
        return _envelope({"found": False, "query": state,
                          "note": "Use a two-letter state code. 52 jurisdictions are published."})
    return _envelope({
        "found": True, **S,
        "national_denial_rate_pct": META["national_denial_rate_pct"],
        "page": "https://financeratecalc.com/salary-vs-denial-risk-by-state.html",
    })


@mcp.tool()
def compare_lenders(lenders: list[str]) -> dict[str, Any]:
    """Compare the observed records of two or more lenders side by side.

    Args:
        lenders: Institution names, e.g. ["Rocket", "UWM", "CrossCountry"].
    """
    rows, missing = [], []
    for name in lenders:
        L = _find_lender(name)
        if not L:
            missing.append(name); continue
        rows.append({"lender": L["name"], "decisioned_applications": L["decisioned_applications"],
                     "denial_rate_pct": L["denial_rate_pct"], "approval_rate_pct": L["approval_rate_pct"],
                     "peer_adjusted_ratio": L["peer_adjusted_ratio"]})
    rows.sort(key=lambda r: r["denial_rate_pct"])
    return _envelope({
        "compared": rows, "not_found": missing,
        "peer_median_denial_rate_pct": PEER["denial_rate_pct"],
        "spread_pts": round(rows[-1]["denial_rate_pct"] - rows[0]["denial_rate_pct"], 1) if len(rows) >= 2 else None,
        "note": "A lower denial rate does not mean an institution is easier to qualify with. "
                "Some screen applicants informally before a formal application is recorded, "
                "which keeps the reported rate low without reflecting underwriting behaviour.",
    })


@mcp.tool()
def explain_denial_reason(reason: str) -> dict[str, Any]:
    """Explain how common a cited denial reason is across the 100 largest FHA lenders, and
    how concentrated it is — some reasons are near-universal, one is concentrated in a
    handful of institutions.

    Args:
        reason: One of dti, credit_history, collateral, insufficient_cash, incomplete,
                unverifiable_info, employment, other.
    """
    key = reason.lower().strip().replace(" ", "_").replace("-", "_")
    alias = {"debt_to_income": "dti", "credit": "credit_history", "appraisal": "collateral",
             "property": "collateral", "cash": "insufficient_cash",
             "incomplete_application": "incomplete", "documentation": "unverifiable_info"}
    key = alias.get(key, key)
    if key not in PEER or key == "denial_rate_pct":
        return _envelope({"found": False, "query": reason,
                          "valid_reasons": [k for k in PEER if k != "denial_rate_pct"]})
    vals = [(L["name"], L["denial_reason_shares_pct"].get(key, 0))
            for L in LENDERS if L["denial_reason_shares_pct"] and L["in_top_100"]]
    vals.sort(key=lambda v: -v[1])
    return _envelope({
        "found": True, "reason": key,
        "peer_median_share_pct": PEER[key],
        "highest_shares": [{"lender": n, "share_pct": v} for n, v in vals[:5]],
        "lowest_shares": [{"lender": n, "share_pct": v} for n, v in vals[-5:]],
        "note": "Shares are of an institution's formal denials, computed on cited reasons. "
                "HMDA allows up to four reasons per denial, so shares can sum above 100%. "
                "A median across lenders describes the typical institution; a volume-weighted "
                "share describes the typical denied borrower, and the two can differ by an "
                "order of magnitude.",
        "page": "https://financeratecalc.com/the-incomplete-wall.html",
    })


@mcp.tool()
def get_methodology() -> dict[str, Any]:
    """Return the universe definition, denominator rules, exclusions and verification
    status behind every figure this server returns."""
    return _envelope({
        "universe": META["universe"],
        "decisioned_applications": META["n"],
        "national_denial_rate_pct": META["national_denial_rate_pct"],
        "excluded_by_definition": [
            "action_taken 4 — withdrawn by applicant",
            "action_taken 5 — file closed for incompleteness",
            "action_taken 6 — purchased loan (no underwriting decision by the reporter)",
            "action_taken 7, 8 — preapproval track",
            "reverse mortgages (HECM) — FHA-insured but underwritten on age and equity",
        ],
        "not_filtered": [
            "loan purpose — purchase, refinance, cash-out refinance and other all included; "
            "filtering to purchase only drops the national rate from 22.1% to roughly 13%",
            "lien status", "occupancy", "property type",
        ],
        "known_limitations": [
            "HMDA contains no credit scores; peer adjustment controls only the profile "
            "dimensions the federal record contains",
            "Denial rates reflect applicant composition as well as lender practice",
            "Institutions below 1,500 decisioned applications are not published",
        ],
        "verification": {
            "status": META["verification_status"],
            "note": META["verification_note"],
            "how_to_check": "https://financeratecalc.com/reconciliation.html",
            "corrections": "https://financeratecalc.com/corrections.html",
        },
        "citation": "Primary data: CFPB HMDA 2025. Derived figures: Yetis, Z. (2026), "
                    "FinanceRateCalc. https://doi.org/10.5281/zenodo.21575105",
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
