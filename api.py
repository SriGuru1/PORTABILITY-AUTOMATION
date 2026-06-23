"""
AntiGravity FastAPI REST API
Exposes the portability pipeline over HTTP with CORS support.

Endpoints:
  POST /analyse          — upload PDF file or pass ?url=  → JSON report
  GET  /report/{id}      — fetch a saved report by report_id
  GET  /reports          — list all saved reports (summaries)
  GET  /health           — health check
"""
import json
import logging
import os
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("antigravity.api")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AntiGravity — Prudential Health Portability Analyzer",
    description=(
        "REST API for Prudential Health India's AI-powered health insurance "
        "portability analyzer. Upload a policy PDF to get extraction, gap analysis, "
        "plan recommendation, and a pre-filled IRDAI Annexure A form."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (allow all origins for frontend dev) ─────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend if it exists
_frontend_dir = Path(__file__).parent / "frontend"
if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_pipeline(pdf_path: str) -> dict:
    """Run the full pipeline on a PDF path and return results dict."""
    from tools.pdf_extractor import extract_text_from_pdf
    from tools.llm_parser import extract_fields_with_llm
    from tools.plan_matcher import match_best_plan
    from tools.report_generator import generate_report
    from tools.form_filler import fill_portability_form

    # Step 1: Extract
    extraction = extract_text_from_pdf(pdf_path)
    if extraction.get("error") and not extraction.get("text"):
        raise ValueError(f"PDF extraction failed: {extraction['error']}")

    # Step 2: LLM parse
    extracted = extract_fields_with_llm(extraction["text"])
    if "error" in extracted:
        raise ValueError(f"LLM extraction failed: {extracted['error']}")

    # Step 3: Plan match
    recommendation = match_best_plan(extracted)
    if "error" in recommendation:
        raise ValueError(f"Plan matching failed: {recommendation['error']}")

    # Step 4: Generate report
    report_result = generate_report(extracted, recommendation, REPORTS_DIR)

    # Step 5: Form fill
    form_result = fill_portability_form(extracted, recommendation, REPORTS_DIR)
    report_result["form_pdf"] = form_result.get("form_pdf")

    return {
        "report": report_result["report"],
        "json_report_path": report_result["json_report"],
        "html_report_path": report_result["html_report"],
        "form_pdf_path": report_result.get("form_pdf"),
        "extraction_meta": {
            "pages": extraction.get("pages"),
            "method": extraction.get("method"),
            "warning": extraction.get("error"),
        },
    }


def _cleanup_temp(path: str):
    """Background task: delete temp file."""
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "AntiGravity Portability Analyzer",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/analyse", tags=["Analysis"], summary="Analyse a health insurance PDF")
async def analyse(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Query(default=None, description="URL to a public PDF"),
):
    """
    Analyse a health insurance PDF for portability.

    Provide **either**:
    - `file` — PDF uploaded as multipart/form-data
    - `url` — public URL to a PDF (query param)

    Returns JSON with extraction results, coverage analysis, plan recommendation,
    and paths to the generated HTML report and pre-filled IRDAI form.
    """
    if not file and not url:
        raise HTTPException(
            status_code=422,
            detail="Provide either a PDF file upload (file=) or a PDF URL (?url=)"
        )

    tmp_path = None
    try:
        if file:
            # Save uploaded file to temp
            suffix = Path(file.filename or "policy.pdf").suffix or ".pdf"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="antigrav_upload_")
            os.close(fd)
            content = await file.read()
            with open(tmp_path, "wb") as f:
                f.write(content)
            logger.info(f"Uploaded file: {file.filename} ({len(content):,} bytes) → {tmp_path}")
            pdf_path = tmp_path

        else:
            # Download from URL
            from tools.pdf_extractor import extract_text_from_url
            # Download into temp file
            import httpx
            fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="antigrav_url_")
            os.close(fd)
            with httpx.Client(follow_redirects=True, timeout=60) as client:
                resp = client.get(url)
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    f.write(resp.content)
            logger.info(f"Downloaded URL PDF: {url} ({len(resp.content):,} bytes)")
            pdf_path = tmp_path

        # Run pipeline
        result = _run_pipeline(pdf_path)

        # Queue cleanup
        if tmp_path:
            background_tasks.add_task(_cleanup_temp, tmp_path)

        # Build API response
        report = result["report"]
        rec = report.get("recommendation", {})
        cp = report.get("current_policy", {})

        return JSONResponse(content={
            "success": True,
            "report_id": report.get("report_id"),
            "customer": report.get("customer"),
            "current_policy": cp,
            "recommendation": rec,
            "portability_eligibility": report.get("portability_eligibility"),
            "files": {
                "json_report": result["json_report_path"],
                "html_report": result["html_report_path"],
                "form_pdf": result.get("form_pdf_path"),
            },
            "extraction_meta": result["extraction_meta"],
            "generated_at": report.get("generated_at"),
        })

    except ValueError as e:
        if tmp_path:
            background_tasks.add_task(_cleanup_temp, tmp_path)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        if tmp_path:
            background_tasks.add_task(_cleanup_temp, tmp_path)
        logger.error(f"Pipeline error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/report/{report_id}", tags=["Reports"], summary="Fetch a saved report by ID")
def get_report(report_id: str):
    """
    Fetch a previously generated report by its report_id.
    report_id format: ANTIGRAV-YYYYMMDD_HHMMSS
    """
    # Find matching JSON file in reports dir
    reports_path = Path(REPORTS_DIR)
    matches = list(reports_path.glob(f"report_*_{report_id.replace('ANTIGRAV-', '')}.json"))
    if not matches:
        # Try partial match on any JSON file containing the id
        matches = [
            p for p in reports_path.glob("report_*.json")
            if report_id in p.read_text(encoding="utf-8", errors="ignore")
        ]

    if not matches:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")

    try:
        with open(matches[0], encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading report: {e}")


@app.get("/reports", tags=["Reports"], summary="List all saved reports")
def list_reports():
    """List all generated reports with summary metadata."""
    reports_path = Path(REPORTS_DIR)
    summaries = []

    for json_file in sorted(reports_path.glob("report_*.json"), reverse=True):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            rec = data.get("recommendation", {})
            summaries.append({
                "report_id": data.get("report_id"),
                "generated_at": data.get("generated_at"),
                "customer_name": data.get("customer", {}).get("name"),
                "insurer": data.get("current_policy", {}).get("insurer"),
                "sum_insured": data.get("current_policy", {}).get("sum_insured"),
                "recommended_plan": rec.get("recommended_plan"),
                "verdict": rec.get("verdict"),
                "file": json_file.name,
            })
        except Exception:
            pass

    # Also list HTML and form PDFs
    html_files = [p.name for p in reports_path.glob("report_*.html")]
    form_files = [p.name for p in reports_path.glob("annexure_a_*.pdf")]

    return {
        "total": len(summaries),
        "reports": summaries,
        "html_files": html_files,
        "form_pdfs": form_files,
    }


@app.get("/report/{report_id}/html", tags=["Reports"], summary="Serve HTML report")
def get_html_report(report_id: str):
    """Download / view the HTML version of a report."""
    reports_path = Path(REPORTS_DIR)
    ts = report_id.replace("ANTIGRAV-", "")
    matches = list(reports_path.glob(f"report_*_{ts}.html"))
    if not matches:
        raise HTTPException(status_code=404, detail="HTML report not found")
    return FileResponse(str(matches[0]), media_type="text/html")


@app.get("/report/{report_id}/form", tags=["Reports"], summary="Download pre-filled Annexure A PDF")
def get_form_pdf(report_id: str):
    """Download the pre-filled IRDAI Annexure A portability form PDF."""
    reports_path = Path(REPORTS_DIR)
    ts = report_id.replace("ANTIGRAV-", "")
    # The form PDF uses customer name, not report_id — find by timestamp
    matches = list(reports_path.glob(f"annexure_a_*_{ts}.pdf"))
    if not matches:
        raise HTTPException(status_code=404, detail="Form PDF not found for this report")
    return FileResponse(
        str(matches[0]),
        media_type="application/pdf",
        filename=matches[0].name
    )


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
