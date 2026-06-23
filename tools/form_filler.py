"""
Form Filler Tool — IRDAI Annexure A Portability Application
Generates a pre-filled PDF portability form using extracted policy fields.
Uses ReportLab to render a professional A4 form layout.
"""
import logging
import os
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


def fill_portability_form(
    extracted_fields: dict,
    recommendation: dict,
    output_dir: str = "reports"
) -> dict:
    """
    Generate a pre-filled IRDAI Annexure A portability application form as PDF.

    Args:
        extracted_fields: Structured data extracted from the current policy PDF
        recommendation: Plan recommendation output from plan_matcher
        output_dir: Directory to save the generated form PDF

    Returns:
        dict with 'form_pdf' (path) or 'error'
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return {"error": "reportlab not installed. Run: pip install reportlab"}

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    customer_name = extracted_fields.get("customer_name") or "Customer"
    safe_name = customer_name.replace(" ", "_").lower()
    form_path = os.path.join(output_dir, f"annexure_a_{safe_name}_{timestamp}.pdf")

    try:
        _draw_form(form_path, extracted_fields, recommendation)
        logger.info(f"Annexure A form saved: {form_path}")
        return {"form_pdf": form_path, "error": None}
    except Exception as e:
        logger.error(f"Form generation failed: {e}")
        return {"error": str(e), "form_pdf": None}


def _draw_form(path: str, fields: dict, rec: dict):
    """Draw the full IRDAI Annexure A form on PDF canvas."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    W, H = A4  # 595.27 x 841.89 points
    c = pdf_canvas.Canvas(path, pagesize=A4)

    # ── Color palette ─────────────────────────────────────────────────────────
    PRUD_BLUE   = colors.HexColor("#003087")
    PRUD_LIGHT  = colors.HexColor("#E8EEF8")
    FILL_YELLOW = colors.HexColor("#FFFBEA")
    BORDER_GRAY = colors.HexColor("#CCCCCC")
    TEXT_DARK   = colors.HexColor("#1A1A2E")
    GREEN       = colors.HexColor("#155724")
    LABEL_GRAY  = colors.HexColor("#555555")

    def header():
        """Draw page header with Prudential branding."""
        # Blue banner
        c.setFillColor(PRUD_BLUE)
        c.rect(0, H - 55*mm, W, 55*mm, fill=1, stroke=0)

        # Logo area — white box
        c.setFillColor(colors.white)
        c.rect(10*mm, H - 50*mm, 45*mm, 42*mm, fill=1, stroke=0)
        c.setFillColor(PRUD_BLUE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(12*mm, H - 28*mm, "PRUDENTIAL")
        c.setFont("Helvetica", 7)
        c.drawString(12*mm, H - 34*mm, "Health India")

        # Title
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(62*mm, H - 22*mm, "IRDAI PORTABILITY APPLICATION")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(62*mm, H - 32*mm, "ANNEXURE A — Health Insurance Portability Form")
        c.setFont("Helvetica", 9)
        c.drawString(62*mm, H - 41*mm, "As per IRDAI (Health Insurance) Regulations 2016 | Submit 45 days before policy expiry")

        # Date stamp
        c.setFont("Helvetica", 8)
        c.drawString(62*mm, H - 49*mm, f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

        # IRDAI notice banner
        c.setFillColor(FILL_YELLOW)
        c.rect(10*mm, H - 64*mm, W - 20*mm, 8*mm, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#FFC107"))
        c.rect(10*mm, H - 64*mm, W - 20*mm, 8*mm, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#856404"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(14*mm, H - 59.5*mm,
                     "⚠  This form must be submitted to Prudential Health India at least 45 days before your current policy expires.")

    def section_title(y_pt: float, title: str) -> float:
        """Draw a section header bar and return new y position."""
        c.setFillColor(PRUD_BLUE)
        c.rect(10*mm, y_pt - 7*mm, W - 20*mm, 7*mm, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(13*mm, y_pt - 5*mm, title)
        return y_pt - 9*mm

    def field_row(y_pt: float, label: str, value: str,
                  label_w: float = 60*mm, full_width: bool = False) -> float:
        """Draw a labeled field row. Returns new y position."""
        row_h = 8*mm
        row_w = W - 20*mm if full_width else W - 20*mm

        # Background
        c.setFillColor(PRUD_LIGHT)
        c.rect(10*mm, y_pt - row_h, label_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(BORDER_GRAY)
        c.rect(10*mm, y_pt - row_h, label_w, row_h, fill=0, stroke=1)

        # Label
        c.setFillColor(LABEL_GRAY)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(12*mm, y_pt - 5.5*mm, label)

        # Value box
        val_x = 10*mm + label_w
        val_w = row_w - label_w
        c.setFillColor(colors.white)
        c.rect(val_x, y_pt - row_h, val_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(BORDER_GRAY)
        c.rect(val_x, y_pt - row_h, val_w, row_h, fill=0, stroke=1)

        # Value text
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 8.5)
        disp = str(value) if value else "—"
        # Truncate if too long
        if len(disp) > 80:
            disp = disp[:77] + "..."
        c.drawString(val_x + 2*mm, y_pt - 5.5*mm, disp)

        return y_pt - row_h - 1*mm

    def two_col_row(y_pt: float,
                    label1: str, val1: str,
                    label2: str, val2: str) -> float:
        """Draw two side-by-side fields. Returns new y position."""
        row_h = 8*mm
        half = (W - 20*mm) / 2

        for i, (lbl, val) in enumerate([(label1, val1), (label2, val2)]):
            ox = 10*mm + i * half
            # Label bg
            c.setFillColor(PRUD_LIGHT)
            c.rect(ox, y_pt - row_h, 55*mm, row_h, fill=1, stroke=0)
            c.setStrokeColor(BORDER_GRAY)
            c.rect(ox, y_pt - row_h, 55*mm, row_h, fill=0, stroke=1)
            c.setFillColor(LABEL_GRAY)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(ox + 2*mm, y_pt - 5.5*mm, lbl)
            # Value box
            vx = ox + 55*mm
            vw = half - 55*mm
            c.setFillColor(colors.white)
            c.rect(vx, y_pt - row_h, vw, row_h, fill=1, stroke=0)
            c.setStrokeColor(BORDER_GRAY)
            c.rect(vx, y_pt - row_h, vw, row_h, fill=0, stroke=1)
            c.setFillColor(TEXT_DARK)
            c.setFont("Helvetica", 8.5)
            disp = str(val) if val else "—"
            c.drawString(vx + 2*mm, y_pt - 5.5*mm, disp)

        return y_pt - row_h - 1*mm

    def multiline_field(y_pt: float, label: str, value: str, lines: int = 2) -> float:
        """Draw a multi-line field. Returns new y position."""
        row_h = lines * 6*mm
        lbl_w = 60*mm

        c.setFillColor(PRUD_LIGHT)
        c.rect(10*mm, y_pt - row_h, lbl_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(BORDER_GRAY)
        c.rect(10*mm, y_pt - row_h, lbl_w, row_h, fill=0, stroke=1)
        c.setFillColor(LABEL_GRAY)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(12*mm, y_pt - 6*mm, label)

        val_x = 10*mm + lbl_w
        val_w = W - 20*mm - lbl_w
        c.setFillColor(colors.white)
        c.rect(val_x, y_pt - row_h, val_w, row_h, fill=1, stroke=0)
        c.setStrokeColor(BORDER_GRAY)
        c.rect(val_x, y_pt - row_h, val_w, row_h, fill=0, stroke=1)

        # Wrap text
        c.setFillColor(TEXT_DARK)
        c.setFont("Helvetica", 8.5)
        if value:
            # Simple word wrap
            words = str(value).split()
            line_buf, cur_y = [], y_pt - 5*mm
            max_chars = int(val_w / 4.8)
            for word in words:
                test = " ".join(line_buf + [word])
                if len(test) > max_chars and line_buf:
                    c.drawString(val_x + 2*mm, cur_y, " ".join(line_buf))
                    line_buf = [word]
                    cur_y -= 6*mm
                else:
                    line_buf.append(word)
            if line_buf:
                c.drawString(val_x + 2*mm, cur_y, " ".join(line_buf))

        return y_pt - row_h - 1*mm

    # ── Helpers for formatting ─────────────────────────────────────────────────
    def fmt_inr(val) -> str:
        if val is None:
            return "—"
        try:
            return f"Rs. {int(val):,}"
        except Exception:
            return str(val)

    def fmt_list(lst) -> str:
        if not lst:
            return "None declared"
        if isinstance(lst, list):
            return ", ".join(str(x) for x in lst) if lst else "None"
        return str(lst)

    def days_until(date_str: str) -> str:
        if not date_str or date_str == "—":
            return ""
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                exp = datetime.strptime(date_str, fmt).date()
                d = (exp - date.today()).days
                if d < 0:
                    return " (EXPIRED)"
                return f" ({d} days remaining)"
            except ValueError:
                continue
        return ""

    # ═══════════════════════ PAGE 1 ═══════════════════════════════════════════
    header()
    y = H - 68*mm

    # ── PART A: Proposer / Customer Details ───────────────────────────────────
    y = section_title(y, "PART A — PROPOSER DETAILS (Person Applying for Portability)")
    y = two_col_row(y,
                    "Full Name (as per policy)",
                    fields.get("customer_name") or "",
                    "Date of Birth",
                    fields.get("dob") or "")
    y = two_col_row(y,
                    "Age",
                    str(fields.get("age") or ""),
                    "Gender",
                    fields.get("gender") or "")
    y = two_col_row(y,
                    "Mobile Number",
                    str(fields.get("mobile") or ""),
                    "Email Address",
                    fields.get("email") or "")
    y = multiline_field(y, "Residential Address", fields.get("address") or "", lines=2)
    y -= 2*mm

    # ── PART B: Existing Policy Details ───────────────────────────────────────
    y = section_title(y, "PART B — EXISTING POLICY DETAILS (Policy Being Ported FROM)")
    y = two_col_row(y,
                    "Current Insurer Name",
                    fields.get("insurer_name") or "",
                    "Product / Plan Name",
                    fields.get("product_name") or "")
    y = two_col_row(y,
                    "Policy Number",
                    fields.get("policy_number") or "",
                    "UIN (IRDAI Ref No.)",
                    fields.get("uin") or "")
    y = two_col_row(y,
                    "Policy Start Date",
                    fields.get("policy_start_date") or "",
                    "Policy Expiry Date",
                    (fields.get("policy_end_date") or "") + days_until(fields.get("policy_end_date") or ""))
    y = two_col_row(y,
                    "Continuous Years Covered",
                    str(fields.get("continuous_years_covered") or "") + " year(s)",
                    "Policy Type",
                    fields.get("policy_type") or "")
    y = two_col_row(y,
                    "Sum Insured (Base)",
                    fmt_inr(fields.get("sum_insured")),
                    "No Claim Bonus (NCB)",
                    fmt_inr(fields.get("ncb_amount")))
    y = two_col_row(y,
                    "Total Coverage (SI + NCB)",
                    fmt_inr((fields.get("sum_insured") or 0) + (fields.get("ncb_amount") or 0)),
                    "Annual Premium (incl. GST)",
                    fmt_inr(fields.get("premium_gross")))
    y -= 2*mm

    # ── PART C: Pre-existing Diseases ─────────────────────────────────────────
    y = section_title(y, "PART C — PRE-EXISTING DISEASES (PEDs) DECLARATION")
    peds = fields.get("pre_existing_diseases") or []
    y = field_row(y, "Declared Pre-Existing Diseases", fmt_list(peds), full_width=True)
    y = two_col_row(y,
                    "PED Waiting Period (Current)",
                    str(fields.get("ped_waiting_period_months") or 36) + " months",
                    "Waiting Period Credit (Ported)",
                    str(min((fields.get("continuous_years_covered") or 1) * 12,
                            fields.get("ped_waiting_period_months") or 36)) + " months credited")
    y = two_col_row(y,
                    "Specific Disease Waiting",
                    str(fields.get("specific_disease_waiting_months") or 24) + " months",
                    "Initial Waiting Period",
                    str(fields.get("initial_waiting_period_days") or 30) + " days")
    y -= 2*mm

    # ── PART D: Family Members ────────────────────────────────────────────────
    y = section_title(y, "PART D — FAMILY MEMBERS TO BE COVERED (if applicable)")
    family = fields.get("family_members") or []
    if family:
        for i, member in enumerate(family[:5], 1):
            name_m = member.get("name", f"Member {i}")
            age_m = str(member.get("age", ""))
            rel_m = member.get("relationship", "")
            gen_m = member.get("gender", "")
            y = field_row(y,
                          f"Member {i}: {rel_m}",
                          f"{name_m}  |  Age: {age_m}  |  Gender: {gen_m}",
                          full_width=True)
    else:
        y = field_row(y, "Family Members", "Individual policy / No additional members declared", full_width=True)
    y -= 2*mm

    # ── PART E: Requested Prudential Plan ────────────────────────────────────
    y = section_title(y, "PART E — REQUESTED PRUDENTIAL PLAN (Policy to be Ported TO)")
    y = two_col_row(y,
                    "Proposed Insurer",
                    "Prudential Health India",
                    "Proposed Plan",
                    rec.get("recommended_plan") or "")
    y = two_col_row(y,
                    "Proposed Sum Insured",
                    fmt_inr(rec.get("recommended_sum_insured")),
                    "Est. Annual Premium",
                    fmt_inr(rec.get("estimated_premium_gross")) + " (estimated*)")
    y = two_col_row(y,
                    "Annual Savings",
                    fmt_inr(rec.get("annual_savings")) if (rec.get("annual_savings") or 0) > 0 else "—",
                    "Match Score",
                    str(rec.get("match_score") or "") + "/100")
    y = field_row(y, "Recommendation Verdict", rec.get("verdict") or "", full_width=True)
    y -= 3*mm

    # ── Page footer ───────────────────────────────────────────────────────────
    _draw_footer(c, W, H, 1)
    c.showPage()

    # ═══════════════════════ PAGE 2 ═══════════════════════════════════════════
    header()
    y = H - 68*mm

    # ── PART F: Portability Declaration ──────────────────────────────────────
    y = section_title(y, "PART F — PORTABILITY ELIGIBILITY DECLARATION")

    # IRDAI rule box
    c.setFillColor(colors.HexColor("#D4EDDA"))
    c.rect(10*mm, y - 22*mm, W - 20*mm, 22*mm, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#28A745"))
    c.rect(10*mm, y - 22*mm, W - 20*mm, 22*mm, fill=0, stroke=1)

    ped_credit = min(
        (fields.get("continuous_years_covered") or 1) * 12,
        fields.get("ped_waiting_period_months") or 36
    )
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(14*mm, y - 6*mm, "✅ PORTABILITY ELIGIBILITY — IRDAI RULES")
    c.setFont("Helvetica", 8.5)
    c.drawString(14*mm, y - 12*mm,
                 f"✔  Policy has been continuously active for {fields.get('continuous_years_covered') or 1} year(s) (minimum 1 year required)")
    c.drawString(14*mm, y - 17*mm,
                 f"✔  PED waiting period credit: {ped_credit} months will be waived on porting to Prudential")
    c.drawString(14*mm, y - 22*mm,
                 f"✔  Apply at least 45 days before policy expiry: {fields.get('policy_end_date') or 'check expiry date'}")

    y -= 24*mm

    # ── PART G: Declaration & Signature ──────────────────────────────────────
    y = section_title(y, "PART G — DECLARATION BY PROPOSER")
    y -= 3*mm

    declaration = (
        "I/We hereby declare that all the information provided above is true, complete, and correct "
        "to the best of my/our knowledge. I/We understand that any concealment of material facts "
        "may lead to cancellation of the policy. I/We hereby apply for portability of my/our existing "
        "health insurance policy to Prudential Health India as per IRDAI (Health Insurance) Regulations "
        "2016 and agree to abide by the terms and conditions of the proposed policy."
    )
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 8)

    # Word-wrap declaration
    words = declaration.split()
    line_buf, cur_y = [], y
    max_w = W - 20*mm
    char_per_line = 105
    for word in words:
        test = " ".join(line_buf + [word])
        if len(test) > char_per_line and line_buf:
            c.drawString(10*mm, cur_y, " ".join(line_buf))
            line_buf = [word]
            cur_y -= 5*mm
        else:
            line_buf.append(word)
    if line_buf:
        c.drawString(10*mm, cur_y, " ".join(line_buf))
    y = cur_y - 10*mm

    # Signature section
    sig_y = y - 20*mm
    # Proposer signature box
    c.setStrokeColor(BORDER_GRAY)
    c.rect(10*mm, sig_y, 70*mm, 20*mm, fill=0, stroke=1)
    c.setFillColor(LABEL_GRAY)
    c.setFont("Helvetica", 7.5)
    c.drawString(12*mm, sig_y + 16*mm, "Signature of Proposer")
    c.drawString(12*mm, sig_y + 2*mm, f"Name: {fields.get('customer_name') or ''}")

    # Date box
    c.rect(90*mm, sig_y, 40*mm, 20*mm, fill=0, stroke=1)
    c.drawString(92*mm, sig_y + 16*mm, "Date of Application")
    c.drawString(92*mm, sig_y + 2*mm, "  /  /  ")

    # Agent/Intermediary box
    c.rect(140*mm, sig_y, 55*mm, 20*mm, fill=0, stroke=1)
    c.drawString(142*mm, sig_y + 16*mm, "Prudential Agent / Intermediary")
    c.drawString(142*mm, sig_y + 10*mm, "Name: ___________________")
    c.drawString(142*mm, sig_y + 4*mm, "Code: ___________________")

    y = sig_y - 10*mm

    # ── PART H: Documents Checklist ──────────────────────────────────────────
    y = section_title(y, "PART H — DOCUMENTS TO BE SUBMITTED ALONG WITH THIS FORM")
    y -= 2*mm

    docs = [
        "☐  Copy of current insurance policy document (all pages)",
        "☐  Copy of last 3 years claim history / no-claim certificate from current insurer",
        "☐  Copy of Aadhaar Card / PAN Card (identity proof)",
        "☐  Recent passport-size photograph of proposer",
        "☐  Medical reports (if any pre-existing conditions are declared above)",
        "☐  Proposal form (to be filled separately with Prudential agent)",
    ]
    c.setFillColor(TEXT_DARK)
    c.setFont("Helvetica", 9)
    for doc in docs:
        c.drawString(14*mm, y, doc)
        y -= 6*mm

    y -= 5*mm

    # ── Disclaimer ────────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#FFF3CD"))
    c.rect(10*mm, y - 20*mm, W - 20*mm, 20*mm, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#FFC107"))
    c.rect(10*mm, y - 20*mm, W - 20*mm, 20*mm, fill=0, stroke=1)
    c.setFillColor(colors.HexColor("#856404"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(14*mm, y - 5*mm, "IMPORTANT DISCLAIMER")
    c.setFont("Helvetica", 7.5)
    c.drawString(14*mm, y - 10*mm,
                 "* Estimated premiums shown are indicative only and subject to final underwriting by Prudential Health India.")
    c.drawString(14*mm, y - 15*mm,
                 "  Final premium may vary based on age, health status, sum insured, and other underwriting factors.")
    c.drawString(14*mm, y - 20*mm,
                 "  This form was auto-generated by AntiGravity Agent. Verify all fields before submission.")

    _draw_footer(c, W, H, 2)
    c.save()


def _draw_footer(c, W, H, page_num: int):
    """Draw page footer."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    PRUD_BLUE = colors.HexColor("#003087")
    c.setFillColor(PRUD_BLUE)
    c.rect(0, 0, W, 12*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7)
    c.drawString(10*mm, 4*mm,
                 "AntiGravity Agent — Powered by Google ADK & Claude AI  |  Prudential Health India")
    c.drawRightString(W - 10*mm, 4*mm, f"Page {page_num} of 2")
    c.drawCentredString(W / 2, 4*mm,
                        "IRDAI Reg. No. TBD  |  www.prudentialhealth.in  |  1800-XXX-XXXX")
