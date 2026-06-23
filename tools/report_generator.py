"""
Report Generator Tool
Generates JSON and HTML portability reports.
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prudential Portability Report — {customer_name}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #f4f6f9; color: #222; margin: 0; padding: 20px; }}
  .container {{ max-width: 900px; margin: auto; }}
  .header {{ background: linear-gradient(135deg, #003087, #0060b1); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
  .header h1 {{ margin: 0; font-size: 24px; }}
  .header p {{ margin: 5px 0 0; opacity: 0.85; }}
  .card {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .card h2 {{ margin-top: 0; color: #003087; font-size: 18px; border-bottom: 2px solid #e0e7ff; padding-bottom: 10px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .field {{ background: #f8f9ff; padding: 10px 14px; border-radius: 6px; }}
  .field label {{ font-size: 11px; text-transform: uppercase; color: #666; display: block; margin-bottom: 3px; }}
  .field span {{ font-weight: 600; font-size: 15px; }}
  .verdict {{ padding: 16px 20px; border-radius: 8px; font-weight: 700; font-size: 16px; text-align: center; margin: 16px 0; }}
  .verdict.recommended {{ background: #d4edda; color: #155724; border: 2px solid #28a745; }}
  .verdict.consider {{ background: #fff3cd; color: #856404; border: 2px solid #ffc107; }}
  .verdict.review {{ background: #f8d7da; color: #721c24; border: 2px solid #dc3545; }}
  .comparison-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  .comparison-table th {{ background: #003087; color: white; padding: 10px 14px; text-align: left; }}
  .comparison-table td {{ padding: 10px 14px; border-bottom: 1px solid #eee; }}
  .comparison-table tr:nth-child(even) {{ background: #f8f9ff; }}
  .better {{ color: #155724; font-weight: 600; }}
  .tag {{ display: inline-block; background: #e0e7ff; color: #003087; padding: 3px 10px; border-radius: 20px; font-size: 12px; margin: 3px; }}
  .reasons li {{ margin-bottom: 6px; }}
  .savings-box {{ background: linear-gradient(135deg, #d4edda, #c3e6cb); border-radius: 8px; padding: 16px; text-align: center; }}
  .savings-box .amount {{ font-size: 32px; font-weight: 800; color: #155724; }}
  .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 30px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🏥 Prudential Health — Portability Report</h1>
    <p>Generated on {generated_at} | Policy Ref: {policy_number}</p>
  </div>

  <div class="card">
    <h2>👤 Customer Profile</h2>
    <div class="grid">
      <div class="field"><label>Name</label><span>{customer_name}</span></div>
      <div class="field"><label>Date of Birth</label><span>{dob}</span></div>
      <div class="field"><label>Age / Gender</label><span>{age} / {gender}</span></div>
      <div class="field"><label>Mobile</label><span>{mobile}</span></div>
    </div>
  </div>

  <div class="card">
    <h2>📄 Current Policy</h2>
    <div class="grid">
      <div class="field"><label>Insurer</label><span>{insurer_name}</span></div>
      <div class="field"><label>Policy Number</label><span>{policy_number}</span></div>
      <div class="field"><label>Sum Insured</label><span>₹{sum_insured:,}</span></div>
      <div class="field"><label>No Claim Bonus</label><span>₹{ncb:,}</span></div>
      <div class="field"><label>Total Coverage</label><span>₹{total_coverage:,}</span></div>
      <div class="field"><label>Annual Premium</label><span>₹{premium_gross:,}</span></div>
      <div class="field"><label>Policy Expiry</label><span>{policy_end_date}</span></div>
      <div class="field"><label>Years Covered</label><span>{years_covered} year(s)</span></div>
    </div>
    {ped_section}
  </div>

  <div class="card">
    <h2>⭐ Recommended: {recommended_plan}</h2>
    <div class="{verdict_class} verdict">{verdict}</div>
    {savings_section}
    <table class="comparison-table">
      <tr><th>Feature</th><th>Current Policy</th><th>Prudential {recommended_plan}</th></tr>
      {comparison_rows}
    </table>
    <h3>Why this plan?</h3>
    <ul class="reasons">
      {reasons_html}
    </ul>
    <h3>Plan Highlights</h3>
    {highlights_html}
  </div>

  <div class="card">
    <h2>📊 All Available Options</h2>
    <table class="comparison-table">
      <tr><th>Plan</th><th>Sum Insured</th><th>Est. Premium/yr</th><th>Match Score</th></tr>
      {all_options_html}
    </table>
  </div>

  <div class="footer">
    AntiGravity Agent — Powered by Google ADK &amp; Claude AI<br>
    ⚠️ Premiums are indicative. Final premium subject to Prudential underwriting.
  </div>
</div>
</body>
</html>"""


def _safe_int(val, default: int = 0) -> int:
    if val is None or val == "Not Found" or val == "null" or val == "N/A":
        return default
    try:
        if isinstance(val, str):
            val = val.replace(",", "")
        return int(float(val))
    except (ValueError, TypeError):
        return default


def generate_report(extracted: dict, recommendation: dict, output_dir: str = "reports") -> dict:
    """
    Generate JSON and HTML reports.

    Returns:
        dict with paths to json_report and html_report
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    customer_name = extracted.get("customer_name") or "Customer"
    safe_name = str(customer_name).replace(" ", "_").lower()

    sum_ins = _safe_int(extracted.get("sum_insured"), 0)
    ncb_amt = _safe_int(extracted.get("ncb_amount"), 0)

    # Full report dict
    report = {
        "report_id": f"ANTIGRAV-{timestamp}",
        "generated_at": datetime.now().isoformat(),
        "customer": {
            "name": extracted.get("customer_name"),
            "dob": extracted.get("dob"),
            "age": extracted.get("age"),
            "gender": extracted.get("gender"),
            "mobile": extracted.get("mobile"),
            "email": extracted.get("email"),
        },
        "current_policy": {
            "insurer": extracted.get("insurer_name"),
            "product": extracted.get("product_name"),
            "policy_number": extracted.get("policy_number"),
            "sum_insured": sum_ins,
            "ncb": ncb_amt,
            "total_coverage": sum_ins + ncb_amt,
            "premium_net": _safe_int(extracted.get("premium_net"), 0),
            "premium_gross": _safe_int(extracted.get("premium_gross"), 0),
            "start_date": extracted.get("policy_start_date"),
            "end_date": extracted.get("policy_end_date"),
            "years_covered": _safe_int(extracted.get("continuous_years_covered"), 1),
            "pre_existing_diseases": extracted.get("pre_existing_diseases"),
            "ped_waiting_months": _safe_int(extracted.get("ped_waiting_period_months"), 36),
            "family_members": extracted.get("family_members"),
        },
        "recommendation": recommendation,
        "portability_eligibility": {
            "eligible": True,
            "irdai_rule": "Apply 45 days before expiry",
            "ped_credit_months": min(
                _safe_int(extracted.get("continuous_years_covered"), 1) * 12,
                _safe_int(extracted.get("ped_waiting_period_months"), 36)
            ),
        }
    }

    # Save JSON
    json_path = os.path.join(output_dir, f"report_{safe_name}_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    # Save HTML
    html_path = os.path.join(output_dir, f"report_{safe_name}_{timestamp}.html")
    html = _build_html(extracted, recommendation, report)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Reports saved: {json_path}, {html_path}")
    return {"json_report": json_path, "html_report": html_path, "report": report}


def _build_html(extracted: dict, rec: dict, report: dict) -> str:
    sum_insured = _safe_int(extracted.get("sum_insured"), 0)
    ncb = _safe_int(extracted.get("ncb_amount"), 0)
    premium_gross = _safe_int(extracted.get("premium_gross"), 0)
    peds = [p for p in (extracted.get("pre_existing_diseases") or []) if p and p != "Not Found"]

    ped_section = ""
    if peds:
        tags = "".join(f'<span class="tag">{p}</span>' for p in peds)
        ped_section = f"<div style='margin-top:12px'><label style='font-size:11px;text-transform:uppercase;color:#666'>Pre-Existing Diseases</label><div style='margin-top:6px'>{tags}</div></div>"

    verdict_str = rec.get("verdict", "")
    verdict_class = "recommended" if "RECOMMENDED" in verdict_str else ("consider" if "CONSIDER" in verdict_str else "review")

    savings = rec.get("annual_savings", 0)
    savings_section = ""
    if savings > 0:
        savings_section = f'<div class="savings-box"><div style="font-size:13px;color:#155724;margin-bottom:4px">Annual Premium Savings</div><div class="amount">₹{savings:,}</div></div>'

    # Comparison rows
    rec_si = rec.get("recommended_sum_insured", 0)
    rec_premium = rec.get("estimated_premium_gross", 0)
    rows = [
        ("Sum Insured", f"₹{sum_insured:,}", f'<span class="better">₹{rec_si:,}</span>' if rec_si >= sum_insured else f"₹{rec_si:,}"),
        ("Annual Premium (incl. GST)", f"₹{premium_gross:,}", f'<span class="better">₹{rec_premium:,}</span>' if rec_premium < premium_gross else f"₹{rec_premium:,}"),
        ("PED Waiting Period", f"{extracted.get('ped_waiting_period_months', 36)} months", f'<span class="better">Credited — reduced wait</span>'),
        ("Pre-Hospitalization", f"{extracted.get('pre_hospitalization_days', 60)} days", "60 days"),
        ("Post-Hospitalization", f"{extracted.get('post_hospitalization_days', 90)} days", "90 days"),
    ]
    comparison_rows = "\n".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>" for r in rows)

    reasons_html = "\n".join(f"<li>✅ {r}</li>" for r in rec.get("reasons", []))
    highlights_html = "".join(f'<span class="tag">✨ {h}</span>' for h in rec.get("plan_highlights", []))

    all_options_html = "\n".join(
        f"<tr><td>{o['plan_name']}</td><td>₹{o['recommended_si']:,}</td><td>₹{o['estimated_premium']:,}</td><td>{o['score']}/100</td></tr>"
        for o in rec.get("all_options", [])
    )

    return HTML_TEMPLATE.format(
        customer_name=extracted.get("customer_name") or "N/A",
        generated_at=datetime.now().strftime("%d %b %Y, %I:%M %p"),
        policy_number=extracted.get("policy_number") or "N/A",
        dob=extracted.get("dob") or "N/A",
        age=extracted.get("age") or "N/A",
        gender=extracted.get("gender") or "N/A",
        mobile=extracted.get("mobile") or "N/A",
        insurer_name=extracted.get("insurer_name") or "N/A",
        sum_insured=sum_insured,
        ncb=ncb,
        total_coverage=sum_insured + ncb,
        premium_gross=premium_gross,
        policy_end_date=extracted.get("policy_end_date") or "N/A",
        years_covered=extracted.get("continuous_years_covered") or "N/A",
        ped_section=ped_section,
        recommended_plan=rec.get("recommended_plan", "N/A"),
        verdict=verdict_str,
        verdict_class=verdict_class,
        savings_section=savings_section,
        comparison_rows=comparison_rows,
        reasons_html=reasons_html,
        highlights_html=highlights_html,
        all_options_html=all_options_html,
    )
