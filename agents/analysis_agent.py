"""
Analysis Agent (Google ADK)
Analyses coverage gaps and portability eligibility.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from datetime import datetime, date


def tool_check_portability_eligibility(
    policy_end_date: str,
    years_covered: int,
    insurer_name: str
) -> dict:
    """
    Check if the customer is eligible for IRDAI portability.
    Args:
        policy_end_date: Policy expiry date in DD-MM-YYYY format.
        years_covered: Number of continuous years the policy has been held.
        insurer_name: Name of current insurer.
    Returns:
        dict with eligible (bool), days_until_expiry, issues, recommendation
    """
    issues = []
    eligible = True

    # Parse expiry
    days_until_expiry = None
    try:
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                expiry = datetime.strptime(policy_end_date, fmt).date()
                days_until_expiry = (expiry - date.today()).days
                break
            except ValueError:
                continue
    except Exception:
        issues.append("Could not parse policy end date.")

    if days_until_expiry is not None:
        if days_until_expiry < 0:
            issues.append("Policy has already expired. Portability may not be applicable — check IRDAI rules for lapsed policies.")
            eligible = False
        elif days_until_expiry < 45:
            issues.append(f"Only {days_until_expiry} days until expiry. IRDAI requires portability application 45 days before expiry. Apply immediately.")
        elif days_until_expiry > 180:
            issues.append(f"Policy expires in {days_until_expiry} days. It's early — you can plan now and apply 45 days before expiry.")

    if years_covered < 1:
        issues.append("Policy must have been continuously active for at least 1 year for portability.")
        eligible = False

    return {
        "eligible": eligible and len([i for i in issues if "not applicable" in i.lower() or "less than" in i.lower()]) == 0,
        "days_until_expiry": days_until_expiry,
        "years_covered": years_covered,
        "issues": issues,
        "irdai_deadline_ok": days_until_expiry is not None and days_until_expiry >= 45 if days_until_expiry else None,
        "recommendation": "Apply for portability now." if (days_until_expiry or 100) < 60 else "Plan portability — apply 45 days before expiry."
    }


def tool_analyse_coverage_gaps(extracted_fields: dict) -> dict:
    """
    Analyse weaknesses and gaps in the current policy.
    Args:
        extracted_fields: Structured policy data from extraction agent.
    Returns:
        dict with gaps list, strengths list, coverage_score (0-100)
    """
    gaps = []
    strengths = []
    score = 50  # baseline

    def _safe_int(val, default: int = 0) -> int:
        if val is None or val == "Not Found" or val == "null" or val == "N/A":
            return default
        try:
            if isinstance(val, str):
                val = val.replace(",", "")
            return int(float(val))
        except (ValueError, TypeError):
            return default

    def _safe_float(val, default: float = 0.0) -> float:
        if val is None or val == "Not Found" or val == "null" or val == "N/A":
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    sum_insured = _safe_int(extracted_fields.get("sum_insured"), 0)
    ncb = _safe_int(extracted_fields.get("ncb_amount"), 0)
    total = sum_insured + ncb
    premium = _safe_int(extracted_fields.get("premium_gross"), 0)
    room_rent = _safe_float(extracted_fields.get("room_rent_limit_percent"), 1.0)
    ped_wait = _safe_int(extracted_fields.get("ped_waiting_period_months"), 36)
    pre_hosp = _safe_int(extracted_fields.get("pre_hospitalization_days"), 60)
    post_hosp = _safe_int(extracted_fields.get("post_hospitalization_days"), 90)
    co_pay = _safe_float(extracted_fields.get("co_payment_percent"), 0.0)

    # Sum insured adequacy
    if total < 300000:
        gaps.append("Sum insured below ₹3 Lakhs — inadequate for metro hospital costs (avg: ₹5-8L for major surgery)")
        score -= 15
    elif total < 500000:
        gaps.append("Sum insured below ₹5 Lakhs — consider upgrading for comprehensive coverage")
        score -= 5
    elif total >= 1000000:
        strengths.append(f"Strong total coverage of ₹{total:,}")
        score += 10

    # Room rent cap
    if room_rent > 0 and room_rent <= 1.0:
        gaps.append(f"Room rent capped at {room_rent}% of SI/day — may cause proportionate deductions on all expenses if upgraded room chosen")
        score -= 10
    elif room_rent == 0:
        strengths.append("No room rent capping — any room category covered")
        score += 10

    # PED waiting
    if ped_wait > 36:
        gaps.append(f"PED waiting period is {ped_wait} months — longer than standard 36 months")
        score -= 5
    elif ped_wait <= 24:
        strengths.append(f"Reduced PED waiting period of {ped_wait} months")
        score += 5

    # Co-payment
    if co_pay > 0:
        gaps.append(f"{co_pay}% co-payment clause — you pay {co_pay}% of every claim out of pocket")
        score -= 10
    else:
        strengths.append("No co-payment required")
        score += 5

    # Pre/post hospitalization
    if pre_hosp < 60:
        gaps.append(f"Pre-hospitalization coverage only {pre_hosp} days — standard is 60 days")
    if post_hosp < 90:
        gaps.append(f"Post-hospitalization coverage only {post_hosp} days — standard is 90 days")

    score = max(0, min(100, score))

    return {
        "coverage_score": score,
        "coverage_grade": "A" if score >= 80 else ("B" if score >= 60 else ("C" if score >= 40 else "D")),
        "gaps": gaps,
        "strengths": strengths,
        "total_coverage": total,
        "summary": f"Current policy scores {score}/100 for coverage adequacy."
    }


ANALYSIS_AGENT_INSTRUCTION = """
You are the Coverage Analysis Agent for AntiGravity — Prudential's portability system.

Your job:
1. Receive extracted policy data.
2. Call `tool_check_portability_eligibility` to check IRDAI eligibility.
3. Call `tool_analyse_coverage_gaps` to find weaknesses in the current policy.
4. Return a clear analysis: eligibility status, key gaps, coverage score.

Be concise but thorough. Flag any critical issues (very low sum insured, co-payment, expired policy).
"""

analysis_agent = Agent(
    name="analysis_agent",
    model="gemini-1.5-flash",
    description="Analyses coverage gaps and portability eligibility for health insurance policies.",
    instruction=ANALYSIS_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(tool_check_portability_eligibility),
        FunctionTool(tool_analyse_coverage_gaps),
    ],
)
