"""
AntiGravity Agent — Main Entry Point
Supports CLI, direct Python, and Google ADK Runner modes.
"""
import argparse
import json
import logging
import os
import sys

# Fix Windows console UTF-8 encoding (needed for emoji output)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("antigravity")


def run_pipeline_direct(pdf_input: str, output_dir: str = "reports") -> dict:
    """
    Run the full pipeline without ADK (useful for testing without Google API key).
    Calls tools directly in sequence: extract → parse → match → report → form-fill.
    """
    from tools.pdf_extractor import extract_text_from_pdf, extract_text_from_url
    from tools.llm_parser import extract_fields_with_llm
    from tools.plan_matcher import match_best_plan
    from tools.report_generator import generate_report
    from tools.form_filler import fill_portability_form

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print("\n🚀 AntiGravity Agent — Health Insurance Portability Analyzer")
    print("=" * 60)

    # Step 1: Extract PDF text
    print(f"\n📄 Step 1: Extracting text from PDF...")
    if pdf_input.startswith("http://") or pdf_input.startswith("https://"):
        extraction_result = extract_text_from_url(pdf_input)
    else:
        extraction_result = extract_text_from_pdf(pdf_input)

    if extraction_result.get("error") and not extraction_result.get("text"):
        print(f"❌ PDF extraction failed: {extraction_result['error']}")
        return {"error": extraction_result["error"]}

    method = extraction_result.get("method", "unknown")
    pages = extraction_result.get("pages", 0)
    text_len = len(extraction_result.get("text", ""))
    print(f"   ✅ Extracted {pages} page(s) via [{method}] — {text_len:,} characters")

    if extraction_result.get("error"):
        print(f"   ⚠️  Warning: {extraction_result['error']}")

    policy_text = extraction_result["text"]

    # Step 2: Parse fields with LLM
    print("\n🤖 Step 2: Extracting fields with LLM (Claude claude-sonnet-4-6)...")
    extracted = extract_fields_with_llm(policy_text)
    if "error" in extracted:
        print(f"❌ LLM extraction failed: {extracted['error']}")
        return {"error": extracted["error"]}

    customer = extracted.get("customer_name", "Unknown")
    insurer = extracted.get("insurer_name", "Unknown")
    si = extracted.get("sum_insured")
    print(f"   ✅ Extracted fields for: {customer}")
    print(f"   Insurer: {insurer} | SI: ₹{si:,}" if si else f"   Insurer: {insurer}")

    # Step 3: Match Prudential plan
    print("\n🔍 Step 3: Matching Prudential plan...")
    recommendation = match_best_plan(extracted)
    if "error" in recommendation:
        print(f"❌ Plan matching failed: {recommendation['error']}")
        return {"error": recommendation["error"]}
    print(f"   ✅ Recommended: {recommendation.get('recommended_plan')}")
    print(f"   Verdict: {recommendation.get('verdict')}")

    # Step 4: Generate report (JSON + HTML)
    print(f"\n📊 Step 4: Generating report...")
    report_result = generate_report(extracted, recommendation, output_dir)
    print(f"   ✅ JSON report: {report_result['json_report']}")
    print(f"   ✅ HTML report: {report_result['html_report']}")

    # Step 5: Auto-fill IRDAI Annexure A portability form
    print(f"\n📝 Step 5: Auto-filling IRDAI Annexure A portability form...")
    try:
        form_result = fill_portability_form(extracted, recommendation, output_dir)
        if form_result.get("error"):
            print(f"   ⚠️  Form fill warning: {form_result['error']}")
        else:
            print(f"   ✅ Pre-filled form: {form_result['form_pdf']}")
        report_result["form_pdf"] = form_result.get("form_pdf")
    except Exception as e:
        logger.warning(f"Form fill failed (non-critical): {e}")
        print(f"   ⚠️  Form fill skipped: {e}")
        report_result["form_pdf"] = None

    # Print summary
    print("\n" + "=" * 60)
    print("📋 PORTABILITY SUMMARY")
    print("=" * 60)
    r = report_result["report"]
    cp = r["current_policy"]
    rec = r["recommendation"]

    name = r["customer"].get("name") or "N/A"
    age = r["customer"].get("age") or "N/A"
    gender = r["customer"].get("gender") or "N/A"
    print(f"Customer      : {name} | Age: {age} | {gender}")
    si_val = cp.get("sum_insured") or 0
    ncb_val = cp.get("ncb") or 0
    prem_val = cp.get("premium_gross") or 0
    print(f"Current Policy: {cp.get('insurer', 'N/A')} — ₹{si_val:,} + NCB ₹{ncb_val:,}")
    print(f"Current Premium: ₹{prem_val:,}/yr")
    print(f"\nRecommended   : {rec.get('recommended_plan', 'N/A')}")
    rec_si = rec.get("recommended_sum_insured") or 0
    rec_prem = rec.get("estimated_premium_gross") or 0
    print(f"New SI        : ₹{rec_si:,}")
    print(f"Est. Premium  : ₹{rec_prem:,}/yr (estimated — subject to underwriting)")
    savings = rec.get("annual_savings", 0) or 0
    if savings > 0:
        print(f"💰 Annual Savings: ₹{savings:,}")
    print(f"\n🏆 VERDICT: {rec.get('verdict', 'N/A')}")
    print("=" * 60)
    print(f"\n📁 Reports saved to: {os.path.abspath(output_dir)}/")
    print(f"   • {os.path.basename(report_result['json_report'])}")
    print(f"   • {os.path.basename(report_result['html_report'])}")
    if report_result.get("form_pdf"):
        print(f"   • {os.path.basename(report_result['form_pdf'])}")

    return report_result


def run_with_adk(pdf_input: str) -> None:
    """Run using Google ADK runner (requires GOOGLE_API_KEY)."""
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from agents.orchestrator_agent import root_agent
        import asyncio

        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent,
            app_name="antigravity",
            session_service=session_service,
        )

        async def main():
            session = await session_service.create_session(
                app_name="antigravity",
                user_id="user_001"
            )
            from google.adk.types import Content, Part
            message = Content(parts=[Part(text=f"Please analyse this health insurance policy and recommend the best Prudential plan: {pdf_input}")])

            print("\n🤖 Running AntiGravity with Google ADK...\n")
            async for event in runner.run_async(
                user_id="user_001",
                session_id=session.id,
                new_message=message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(part.text, end="", flush=True)
            print()

        asyncio.run(main())

    except ImportError as e:
        logger.error(f"Google ADK not installed: {e}")
        print("⚠️  Google ADK not available. Running in direct mode instead.\n")
        run_pipeline_direct(pdf_input)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AntiGravity — Health Insurance Portability Analyzer")
    parser.add_argument("--pdf", required=True, help="Path to PDF file or URL")
    parser.add_argument("--output", default="reports", help="Output directory for reports")
    parser.add_argument("--mode", choices=["direct", "adk"], default="direct",
                        help="'direct' runs tools directly, 'adk' uses Google ADK runner")
    args = parser.parse_args()

    if args.mode == "adk":
        run_with_adk(args.pdf)
    else:
        result = run_pipeline_direct(args.pdf, args.output)
        if "error" in result:
            sys.exit(1)
