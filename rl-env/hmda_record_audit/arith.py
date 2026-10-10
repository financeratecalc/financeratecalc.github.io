"""Regulatory arithmetic for an FHA forward-loan record (task A).

Sources, stated so a reader can check them:
  * LTV = loan_amount / property_value (both as reported in the public HMDA LAR; the public
    loan_amount is the CFPB's published value for the record, not the exact note amount).
  * FHA upfront MIP: 1.75% of the base loan amount (HUD Handbook 4000.1, Appendix 1.0).
  * FHA annual MIP: HUD Mortgagee Letter 2023-05 (effective for case numbers assigned on or after
    2023-03-20), base loan amount threshold $726,200. Rates in basis points:
        term > 15 years:  <= $726,200: LTV <= 90% 50; 90 < LTV <= 95% 50; LTV > 95% 55
                           > $726,200: LTV <= 90% 70; 90 < LTV <= 95% 70; LTV > 95% 75
        term <= 15 years: <= $726,200: LTV <= 90% 15; LTV > 90% 40
                           > $726,200: LTV <= 78% 15; 78 < LTV <= 90% 40; LTV > 90% 65
  * Monthly MIP = base loan amount x annual rate / 12 (first-year approximation; HUD amortises
    the annual premium on the average outstanding balance, which this task deliberately ignores
    and says so in the prompt).
Everything here is deterministic; no model is involved.
"""
from __future__ import annotations

UPFRONT_RATE = 0.0175
THRESHOLD = 726_200.0


def ltv(loan_amount: float, property_value: float) -> float:
    return round(loan_amount / property_value, 4)


def annual_mip_rate(loan_amount: float, ltv_ratio: float, term_months: int) -> float:
    big = loan_amount > THRESHOLD
    if term_months > 180:
        if not big:
            bp = 55 if ltv_ratio > 0.95 else 50
        else:
            bp = 75 if ltv_ratio > 0.95 else 70
    else:
        if not big:
            bp = 40 if ltv_ratio > 0.90 else 15
        else:
            bp = 65 if ltv_ratio > 0.90 else (40 if ltv_ratio > 0.78 else 15)
    return bp / 10_000.0


def arithmetic_answer(loan_amount: float, property_value: float, term_months: int) -> dict:
    r = ltv(loan_amount, property_value)
    rate = annual_mip_rate(loan_amount, r, term_months)
    return {
        "ltv": r,
        "mip_upfront": round(loan_amount * UPFRONT_RATE, 2),
        "mip_annual_rate": rate,
        "mip_monthly": round(loan_amount * rate / 12.0, 2),
    }
