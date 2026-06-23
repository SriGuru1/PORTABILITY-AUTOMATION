"""
PDF Extractor Tool
Extracts raw text from health insurance PDFs.
Handles digital PDFs (pdfplumber/PyPDF2) and scanned PDFs (pytesseract OCR fallback).
"""
import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> dict:
    """
    Extract raw text from a PDF file.
    Tries pdfplumber → PyPDF2 → Tesseract OCR (if available).

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict with keys: text (str), pages (int), method (str), error (str|None)
    """
    if not os.path.exists(pdf_path):
        return {"text": "", "pages": 0, "method": "none", "error": f"File not found: {pdf_path}"}

    # Try pdfplumber first (best for structured PDFs with tables)
    result = _extract_with_pdfplumber(pdf_path)
    if result["text"].strip() and len(result["text"].strip()) > 50:
        return result

    # Fallback to PyPDF2
    result2 = _extract_with_pypdf2(pdf_path)
    if result2["text"].strip() and len(result2["text"].strip()) > 50:
        return result2

    # Combine whatever partial text we got
    partial_text = result["text"] + result2["text"]

    # OCR fallback for scanned PDFs
    ocr_result = _extract_with_ocr(pdf_path)
    if ocr_result["text"].strip() and len(ocr_result["text"].strip()) > 50:
        return ocr_result

    if partial_text.strip():
        # Return partial text with a warning
        return {
            "text": partial_text,
            "pages": result.get("pages") or result2.get("pages") or 0,
            "method": "partial",
            "error": "Limited text extracted — PDF may be partially scanned."
        }

    return {
        "text": "",
        "pages": 0,
        "method": "failed",
        "error": (
            "Could not extract text. PDF appears to be a scanned image. "
            "Install Tesseract OCR (https://github.com/tesseract-ocr/tesseract) "
            "and pytesseract for full OCR support."
        )
    }


def _extract_with_pdfplumber(pdf_path: str) -> dict:
    """Extract text using pdfplumber (handles tables well)."""
    try:
        import pdfplumber
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                # Also extract tables as text
                for table in page.extract_tables():
                    for row in table:
                        row_text = " | ".join(str(cell) for cell in row if cell)
                        if row_text.strip():
                            pages_text.append(row_text)

        full_text = "\n".join(pages_text)
        return {"text": full_text, "pages": num_pages, "method": "pdfplumber", "error": None}

    except ImportError:
        logger.warning("pdfplumber not installed")
        return {"text": "", "pages": 0, "method": "pdfplumber", "error": "Not installed"}
    except Exception as e:
        logger.error(f"pdfplumber error: {e}")
        return {"text": "", "pages": 0, "method": "pdfplumber", "error": str(e)}


def _extract_with_pypdf2(pdf_path: str) -> dict:
    """Fallback extraction using PyPDF2."""
    try:
        import PyPDF2
        pages_text = []
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            for page in reader.pages:
                pages_text.append(page.extract_text() or "")

        full_text = "\n".join(pages_text)
        return {"text": full_text, "pages": num_pages, "method": "pypdf2", "error": None}

    except ImportError:
        logger.warning("PyPDF2 not installed")
        return {"text": "", "pages": 0, "method": "pypdf2", "error": "Not installed"}
    except Exception as e:
        logger.error(f"PyPDF2 error: {e}")
        return {"text": "", "pages": 0, "method": "pypdf2", "error": str(e)}


def _extract_with_ocr(pdf_path: str) -> dict:
    """
    OCR fallback using pytesseract + pdf2image for scanned PDFs.
    Requires: pip install pytesseract pdf2image
              + Tesseract binary: https://github.com/tesseract-ocr/tesseract
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path

        logger.info(f"Attempting OCR on: {pdf_path}")
        images = convert_from_path(pdf_path, dpi=300)
        pages_text = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="eng")
            pages_text.append(text)

        full_text = "\n".join(pages_text)
        logger.info(f"OCR extracted {len(full_text)} characters from {len(images)} pages")
        return {"text": full_text, "pages": len(images), "method": "ocr_tesseract", "error": None}

    except ImportError:
        logger.debug("pytesseract/pdf2image not installed — OCR skipped")
        return {"text": "", "pages": 0, "method": "ocr_tesseract", "error": "OCR libraries not installed"}
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return {"text": "", "pages": 0, "method": "ocr_tesseract", "error": str(e)}


def extract_text_from_url(pdf_url: str) -> dict:
    """
    Download a PDF from URL and extract text.
    Uses a cross-platform temp file (fixes Windows /tmp/ issue).

    Args:
        pdf_url: Publicly accessible URL to the PDF

    Returns:
        dict with keys: text, pages, method, error
    """
    tmp_path = None
    try:
        import httpx

        logger.info(f"Downloading PDF from: {pdf_url}")

        # Create temp file in system temp dir (cross-platform)
        fd, tmp_path = tempfile.mkstemp(suffix=".pdf", prefix="antigrav_policy_")
        os.close(fd)

        with httpx.Client(follow_redirects=True, timeout=60) as client:
            response = client.get(pdf_url)
            response.raise_for_status()
            with open(tmp_path, "wb") as f:
                f.write(response.content)

        logger.info(f"Downloaded {len(response.content):,} bytes to {tmp_path}")
        result = extract_text_from_pdf(tmp_path)
        return result

    except Exception as e:
        logger.error(f"URL download failed: {e}")
        return {"text": "", "pages": 0, "method": "url_download", "error": str(e)}
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
