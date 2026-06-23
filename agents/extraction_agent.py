"""
Extraction Agent (Google ADK)
Sub-agent responsible for extracting structured data from the insurance PDF.
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from tools.pdf_extractor import extract_text_from_pdf, extract_text_from_url
from tools.llm_parser import extract_fields_with_llm

logger = logging.getLogger(__name__)

# ── Tool wrappers (ADK FunctionTool requires plain functions) ──────────────────

def tool_extract_pdf_text(pdf_path: str) -> dict:
    """
    Extract raw text from a local PDF file.
    Args:
        pdf_path: Absolute or relative path to the PDF file.
    Returns:
        dict with keys: text, pages, method, error
    """
    return extract_text_from_pdf(pdf_path)


def tool_extract_pdf_from_url(pdf_url: str) -> dict:
    """
    Download a PDF from a URL and extract its text.
    Args:
        pdf_url: Publicly accessible URL to the PDF.
    Returns:
        dict with keys: text, pages, method, error
    """
    return extract_text_from_url(pdf_url)


def tool_parse_policy_fields(policy_text: str) -> dict:
    """
    Use LLM to extract structured insurance fields from raw PDF text.
    Args:
        policy_text: Raw text extracted from the PDF.
    Returns:
        dict with all extracted policy fields (name, DOB, sum insured, PEDs, etc.)
    """
    return extract_fields_with_llm(policy_text)


# ── Agent definition ──────────────────────────────────────────────────────────

EXTRACTION_AGENT_INSTRUCTION = """
You are the Policy Extraction Agent for AntiGravity — Prudential's health insurance portability system.

Your job:
1. Accept a PDF file path or URL from the user.
2. Call `tool_extract_pdf_text` (for file path) or `tool_extract_pdf_from_url` (for URL) to get raw text.
3. If text is empty, report an error — the PDF may be scanned and needs OCR (not yet supported).
4. Call `tool_parse_policy_fields` with the extracted text to get structured fields.
5. Return the structured fields as a clean JSON object.

Always report the insurer name, policy number, sum insured, NCB, premium, and PED details.
If a field is missing, say so clearly — do not guess.
"""

extraction_agent = Agent(
    name="extraction_agent",
    model="gemini-1.5-flash",
    description="Extracts structured data from health insurance PDF documents.",
    instruction=EXTRACTION_AGENT_INSTRUCTION,
    tools=[
        FunctionTool(tool_extract_pdf_text),
        FunctionTool(tool_extract_pdf_from_url),
        FunctionTool(tool_parse_policy_fields),
    ],
)
