"""
Unit tests for AntiGravity extraction and matching pipeline.
Run: python -m pytest tests/ -v
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# ── Sample data (mimics Apex General / Niva Bupa type policies) ───────────────

SAMPLE_POLICY_TEXT = """
APEX GENERAL INSURANCE COMPANY INDIA LIMITED
Policy Number: APX/HLTH/IND/2026/884729
UIN: APXHLIP21143V022122

Insured Name: Shreyas Hegde
Date of Birth: 15-01-1992
Age: 34 | Gender: Male

Period of Cover: 24-Jun-2026 to 23-Jun-2027
Inception Date (First Policy): 24-Jun-2024

Base Sum Insured: Rs. 5,00,000
Cumulative Bonus: Rs. 50,000

Net Premium: Rs. 14,250
GST (18%): Rs. 2,565
Total Premium: Rs. 16,815

Pre-Existing Diseases: Hypertension (declared)
PED Waiting Period: 36 months
Specific Disease Waiting Period: 24 months
Initial Waiting Period: 30 days
"""

SAMPLE_EXTRACTED = {
    "customer_name": "Shreyas Hegde",
    "dob": "15-01-1992",
    "age": 34,
    "gender": "Male",
    "mobile": None,
    "email": None,
    "policy_number": "APX/HLTH/IND/2026/884729",
    "insurer_name": "Apex General Insurance",
    "product_name": "Apex Secure Individual Health Policy",
    "policy_start_date": "24-06-2026",
    "policy_end_date": "23-06-2027",
    "sum_insured": 500000,
    "ncb_amount": 50000,
    "total_coverage": 550000,
    "premium_net": 14250,
    "premium_gross": 16815,
    "family_members": [],
    "pre_existing_diseases": ["Hypertension"],
    "ped_waiting_period_months": 36,
    "specific_disease_waiting_months": 24,
    "initial_waiting_period_days": 30,
    "continuous_years_covered": 2,
    "room_rent_limit_percent": 1.0,
    "icu_limit_percent": 2.0,
    "pre_hospitalization_days": 60,
    "post_hospitalization_days": 90,
    "policy_type": "Individual",
    "co_payment_percent": 0,
    "uin": "APXHLIP21143V022122"
}

# ── Tests ─────────────────────────────────────────────────────────────────────

class TestPdfExtractor:
    def test_missing_file_returns_error(self):
        from tools.pdf_extractor import extract_text_from_pdf
        result = extract_text_from_pdf("/nonexistent/path/policy.pdf")
        assert result["error"] is not None
        assert result["text"] == ""

    def test_returns_dict_with_required_keys(self):
        from tools.pdf_extractor import extract_text_from_pdf
        result = extract_text_from_pdf("/nonexistent/path/policy.pdf")
        assert "text" in result
        assert "pages" in result
        assert "method" in result
        assert "error" in result

    def test_real_pdf_individual(self):
        """Test extraction on the actual INPUTFILES PDF."""
        from tools.pdf_extractor import extract_text_from_pdf
        pdf_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "INPUTFILES", "individual_health_insurance_15_page_policy.pdf"
        )
        if not os.path.exists(pdf_path):
            pytest.skip("INPUTFILES PDF not found")
        result = extract_text_from_pdf(pdf_path)
        assert result["text"], f"No text extracted. Error: {result.get('error')}"
        assert result["pages"] > 0

    def test_real_pdf_portability_kit(self):
        """Test extraction on the portability kit PDF."""
        from tools.pdf_extractor import extract_text_from_pdf
        pdf_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "INPUTFILES", "health_insurance_policy_and_portability_kit.pdf"
        )
        if not os.path.exists(pdf_path):
            pytest.skip("INPUTFILES PDF not found")
        result = extract_text_from_pdf(pdf_path)
        assert result["text"], f"No text extracted. Error: {result.get('error')}"


class TestLLMParser:
    def test_parse_json_response_valid(self):
        from tools.llm_parser import _parse_json_response
        raw = '{"name": "John", "age": 30}'
        result = _parse_json_response(raw)
        assert result["name"] == "John"
        assert result["age"] == 30

    def test_parse_json_response_strips_markdown(self):
        from tools.llm_parser import _parse_json_response
        raw = '```json\n{"name": "Jane"}\n```'
        result = _parse_json_response(raw)
        assert result["name"] == "Jane"

    def test_parse_json_response_invalid_returns_error(self):
        from tools.llm_parser import _parse_json_response
        raw = "This is not JSON"
        result = _parse_json_response(raw)
        assert "error" in result


class TestPlanMatcher:
    def test_match_returns_recommendation(self):
        from tools.plan_matcher import match_best_plan
        result = match_best_plan(SAMPLE_EXTRACTED)
        assert "recommended_plan" in result
        assert "verdict" in result
        assert "estimated_premium_gross" in result
        assert result["recommended_plan"] is not None

    def test_match_includes_all_options(self):
        from tools.plan_matcher import match_best_plan
        result = match_best_plan(SAMPLE_EXTRACTED)
        assert "all_options" in result
        assert len(result["all_options"]) >= 1

    def test_match_score_is_positive(self):
        from tools.plan_matcher import match_best_plan
        result = match_best_plan(SAMPLE_EXTRACTED)
        assert result.get("match_score", 0) >= 0

    def test_age_band_function(self):
        from tools.plan_matcher import _age_band
        assert _age_band(30) == "30_35"
        assert _age_band(35) == "30_35"
        assert _age_band(36) == "36_45"
        assert _age_band(46) == "46_55"

    def test_family_floater_matching(self):
        from tools.plan_matcher import match_best_plan
        family_fields = {**SAMPLE_EXTRACTED, "policy_type": "Family Floater",
                         "family_members": [{"name": "Priya Hegde", "age": 30, "relationship": "Spouse", "gender": "Female"}]}
        result = match_best_plan(family_fields)
        assert "recommended_plan" in result


class TestAnalysisTools:
    def test_portability_check_valid_date(self):
        from agents.analysis_agent import tool_check_portability_eligibility
        result = tool_check_portability_eligibility("23-06-2027", 2, "Apex General")
        assert "eligible" in result
        assert "days_until_expiry" in result

    def test_coverage_gap_analysis(self):
        from agents.analysis_agent import tool_analyse_coverage_gaps
        result = tool_analyse_coverage_gaps(SAMPLE_EXTRACTED)
        assert "coverage_score" in result
        assert "gaps" in result
        assert "strengths" in result
        assert 0 <= result["coverage_score"] <= 100

    def test_low_sum_insured_flags_gap(self):
        from agents.analysis_agent import tool_analyse_coverage_gaps
        low_coverage = {**SAMPLE_EXTRACTED, "sum_insured": 200000, "ncb_amount": 0}
        result = tool_analyse_coverage_gaps(low_coverage)
        gap_texts = " ".join(result["gaps"])
        assert "below" in gap_texts.lower() or "inadequate" in gap_texts.lower()

    def test_co_payment_flags_gap(self):
        from agents.analysis_agent import tool_analyse_coverage_gaps
        co_pay_policy = {**SAMPLE_EXTRACTED, "co_payment_percent": 20}
        result = tool_analyse_coverage_gaps(co_pay_policy)
        gap_texts = " ".join(result["gaps"])
        assert "co-payment" in gap_texts.lower() or "copay" in gap_texts.lower()


class TestReportGenerator:
    def test_generate_report_creates_files(self, tmp_path):
        from tools.report_generator import generate_report
        from tools.plan_matcher import match_best_plan
        rec = match_best_plan(SAMPLE_EXTRACTED)
        result = generate_report(SAMPLE_EXTRACTED, rec, str(tmp_path))
        assert os.path.exists(result["json_report"])
        assert os.path.exists(result["html_report"])

    def test_json_report_has_required_keys(self, tmp_path):
        from tools.report_generator import generate_report
        from tools.plan_matcher import match_best_plan
        rec = match_best_plan(SAMPLE_EXTRACTED)
        result = generate_report(SAMPLE_EXTRACTED, rec, str(tmp_path))
        with open(result["json_report"]) as f:
            data = json.load(f)
        assert "customer" in data
        assert "current_policy" in data
        assert "recommendation" in data
        assert "report_id" in data

    def test_html_report_has_content(self, tmp_path):
        from tools.report_generator import generate_report
        from tools.plan_matcher import match_best_plan
        rec = match_best_plan(SAMPLE_EXTRACTED)
        result = generate_report(SAMPLE_EXTRACTED, rec, str(tmp_path))
        with open(result["html_report"], encoding="utf-8") as f:
            html = f.read()
        assert "Prudential" in html
        assert "Shreyas Hegde" in html


class TestFormFiller:
    def test_form_filler_creates_pdf(self, tmp_path):
        from tools.form_filler import fill_portability_form
        from tools.plan_matcher import match_best_plan
        rec = match_best_plan(SAMPLE_EXTRACTED)
        result = fill_portability_form(SAMPLE_EXTRACTED, rec, str(tmp_path))
        if result.get("error") and "reportlab" in result["error"]:
            pytest.skip("reportlab not installed")
        assert result.get("form_pdf") is not None
        assert os.path.exists(result["form_pdf"])

    def test_form_filler_pdf_has_content(self, tmp_path):
        from tools.form_filler import fill_portability_form
        from tools.plan_matcher import match_best_plan
        rec = match_best_plan(SAMPLE_EXTRACTED)
        result = fill_portability_form(SAMPLE_EXTRACTED, rec, str(tmp_path))
        if result.get("error") and "reportlab" in result["error"]:
            pytest.skip("reportlab not installed")
        if result.get("form_pdf"):
            size = os.path.getsize(result["form_pdf"])
            assert size > 5000, f"PDF too small ({size} bytes) — likely empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
