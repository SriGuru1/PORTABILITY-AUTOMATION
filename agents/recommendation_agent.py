"""
Recommendation Agent (Google ADK)
Recommends the best Prudential plan based on customer profile and analysis.
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.plan_matcher import match_best_plan
from tools.report_generator import generate_report


def tool_match_prudential_plan(extracted_fields_json: str) -> dict:
    """
    Match customer profile to the best Prudential plan.
    Args:
        extracted_fields_json: JSON string of extracted policy fields.
    Returns:
        dict with recommended_plan, estimated_premium, annual_savings, verdict, reasons
    """
    try:
        fields = json.loads(extracted_fields_json) if isinstance(extracted_fields_json, str) else extracted_fields_json
    except Exception:
        return {"error": "Invalid JSON in extracted_fields_json"}
    return match_best_plan(fields)


def tool_generate_portability_report(extracted_fields_json: str, recommendation_json: str) -> dict:
    """
    Generate a full portability report (JSON + HTML).
    Args:
        extracted_fields_json: JSON string of extracted policy fields.
        recommendation_json: JSON string of recommendation from plan matcher.
    Returns:
        dict with json_report path, html_report path
    """
    try:
        extracted = json.loads(extracted_fields_json) if isinstance(extracted_fields_json, str) else extracted_fields_json
        recommendation = json.loads(recommendation_json) if isinstance(recommendation_json, str) else recommendation_json
    except Exception as e:
        return {"error": f"JSON parse error: {e}"}
    return generate_report(extracted, recommendation)


RECOMMENDATION_AGENT_INSTRUCTION = """
You are the Recommendation Agent for AntiGravity — Prudential's portability system.

Your job:
1. Receive extracted policy fields (as JSON string) and coverage analysis.
2. Call `tool_match_prudential_plan` with the extracted fields JSON.
3. Call `tool_generate_portability_report` with both the fields and recommendation.
4. Present the recommendation clearly: plan name, sum insured, premium, verdict, top 3 reasons.

Always mention:
- Annual premium comparison (current vs recommended)
- PED waiting period credit (how many months are waived due to portability)
- Whether the customer saves money or gets more for their money
- The report file path so the user can access it
"""

recommendation_agent = Agent(
    name="recommendation_agent",
    model="gemini-1.5-flash",
    description="Recommends the best Prudential health insurance plan for portability customers.",
    instruction=RECOMMENDATION_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(tool_match_prudential_plan),
        FunctionTool(tool_generate_portability_report),
    ],
)
