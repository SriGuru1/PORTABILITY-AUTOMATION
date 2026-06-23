"""
Plan Matcher Tool
Compares extracted customer policy with Prudential plans and recommends the best match.
"""
import json
import logging
import os
from typing import Optional

from config.settings import PLANS_FILE

logger = logging.getLogger(__name__)


def load_prudential_plans() -> list:
    """Load Prudential plan catalogue from JSON file."""
    try:
        with open(PLANS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("plans", [])
    except Exception as e:
        logger.error(f"Could not load plans: {e}")
        return []


def _safe_int(val, default: int = 0) -> int:
    if val is None or val == "Not Found" or val == "null" or val == "N/A":
        return default
    try:
        if isinstance(val, str):
            val = val.replace(",", "")
        return int(float(val))
    except (ValueError, TypeError):
        return default


def match_best_plan(extracted_data: dict) -> dict:
    """
    Match customer profile to best Prudential plan.

    Args:
        extracted_data: Output from llm_parser.extract_fields_with_llm()

    Returns:
        dict with recommended plan, comparison, savings, verdict
    """
    plans = load_prudential_plans()
    if not plans:
        return {"error": "No plans loaded"}

    age = _safe_int(extracted_data.get("age"), 35)
    sum_insured = _safe_int(extracted_data.get("sum_insured"), 500000)
    ncb = _safe_int(extracted_data.get("ncb_amount"), 0)
    total_coverage = sum_insured + ncb
    current_premium = _safe_int(extracted_data.get("premium_gross"), 0)
    policy_type = str(extracted_data.get("policy_type") or "Individual").lower()
    years_covered = _safe_int(extracted_data.get("continuous_years_covered"), 1)
    family_members = extracted_data.get("family_members") or []
    
    peds_raw = extracted_data.get("pre_existing_diseases") or []
    peds = [p for p in peds_raw if p and p != "Not Found"]
    
    ped_waiting_done = _safe_int(extracted_data.get("ped_waiting_period_months"), 36)

    # Filter plans by type
    is_family = "family" in policy_type or "floater" in policy_type or len(family_members) > 1
    candidate_plans = [p for p in plans if
                       ("Family" in p["plan_type"]) == is_family or
                       p["plan_type"] == "Individual/Family Floater"]

    if not candidate_plans:
        candidate_plans = plans  # fallback to all

    # Score each plan
    scored = []
    for plan in candidate_plans:
        score = 0
        reasons = []

        # 1. Sum insured match — prefer equal or better coverage
        available_sis = plan.get("sum_insured_options", [500000])
        best_si = min([s for s in available_sis if s >= sum_insured], default=max(available_sis))
        if best_si >= total_coverage:
            score += 30
            reasons.append(f"Covers full {total_coverage:,} INR (SI + NCB)")
        elif best_si >= sum_insured:
            score += 15
            reasons.append(f"Covers base SI of {sum_insured:,} INR")

        # 2. Portability PED credit
        if plan.get("portability_ped_credit") and peds:
            credited_months = min(years_covered * 12, ped_waiting_done)
            remaining = max(0, plan["ped_waiting_period_months"] - credited_months)
            score += 25
            reasons.append(f"PED waiting period credited: {credited_months} months done, only {remaining} months remaining")

        # 3. Premium estimate
        premium_key = f"base_premium_age_{_age_band(age)}"
        est_premium_base = plan.get(premium_key) or plan.get("base_premium_age_36_45", 15000)
        # Scale for sum insured
        est_premium = int(est_premium_base * (best_si / 500000) ** 0.7)
        est_premium_with_gst = int(est_premium * 1.18)

        if current_premium > 0 and est_premium_with_gst < current_premium:
            savings = current_premium - est_premium_with_gst
            score += 20
            reasons.append(f"Premium savings of ₹{savings:,}/year")
        elif current_premium > 0:
            premium_increase = est_premium_with_gst - current_premium
            reasons.append(f"Premium increases by ₹{premium_increase:,} for enhanced coverage")

        # 4. Better features
        if plan.get("restore_benefit"):
            score += 10
            reasons.append("Restore benefit — sum insured refilled after major claim")
        if plan.get("domiciliary_hospitalization"):
            score += 5
            reasons.append("Domiciliary hospitalization covered")
        if plan.get("room_rent_limit_percent", 1) > 1 or plan.get("room_rent_limit_percent") == 0:
            score += 5
            reasons.append("Better room rent limit")

        scored.append({
            "plan": plan,
            "score": score,
            "reasons": reasons,
            "recommended_si": best_si,
            "estimated_premium_gross": est_premium_with_gst,
            "estimated_premium_net": est_premium,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0]

    savings = current_premium - best["estimated_premium_gross"] if current_premium > 0 else 0
    verdict = _verdict(best["score"], savings, best["plan"])

    return {
        "recommended_plan": best["plan"]["plan_name"],
        "plan_id": best["plan"]["plan_id"],
        "recommended_sum_insured": best["recommended_si"],
        "estimated_premium_gross": best["estimated_premium_gross"],
        "estimated_premium_net": best["estimated_premium_net"],
        "annual_savings": savings,
        "match_score": best["score"],
        "reasons": best["reasons"],
        "verdict": verdict,
        "plan_highlights": best["plan"].get("highlights", []),
        "all_options": [
            {
                "plan_name": s["plan"]["plan_name"],
                "recommended_si": s["recommended_si"],
                "estimated_premium": s["estimated_premium_gross"],
                "score": s["score"],
            }
            for s in scored
        ]
    }


def _age_band(age: int) -> str:
    if age <= 35:
        return "30_35"
    elif age <= 45:
        return "36_45"
    else:
        return "46_55"


def _verdict(score: int, savings: int, plan: dict) -> str:
    if score >= 60:
        if savings > 0:
            return "STRONGLY RECOMMENDED — Better coverage at lower premium"
        return "RECOMMENDED — Significantly better coverage"
    elif score >= 40:
        return "RECOMMENDED — Good match with portability benefits"
    elif score >= 20:
        return "CONSIDER — Moderate improvement over current plan"
    else:
        return "REVIEW NEEDED — Manual underwriter review recommended"
