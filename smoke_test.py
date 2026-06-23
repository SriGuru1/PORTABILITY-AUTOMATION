import sys, os
sys.path.insert(0, '.')

from tools.pdf_extractor import extract_text_from_pdf

r = extract_text_from_pdf('INPUTFILES/individual_health_insurance_15_page_policy.pdf')
print("PDF 1: %d pages, %d chars via %s" % (r['pages'], len(r['text']), r['method']))

r2 = extract_text_from_pdf('INPUTFILES/health_insurance_policy_and_portability_kit.pdf')
print("PDF 2: %d pages, %d chars via %s" % (r2['pages'], len(r2['text']), r2['method']))

from tools.plan_matcher import match_best_plan
sample = {
    'customer_name': 'Test User',
    'age': 35,
    'sum_insured': 500000,
    'ncb_amount': 50000,
    'premium_gross': 18000,
    'continuous_years_covered': 2,
    'pre_existing_diseases': ['Diabetes'],
    'policy_type': 'Individual'
}
rec = match_best_plan(sample)
print("Plan: %s | Score: %s | %s" % (rec['recommended_plan'], rec['match_score'], rec['verdict']))

from tools.report_generator import generate_report
os.makedirs('reports', exist_ok=True)
extracted = {
    'customer_name': 'Test User',
    'sum_insured': 500000,
    'ncb_amount': 0,
    'premium_gross': 18000,
    'insurer_name': 'Test Co',
    'policy_number': 'TEST/001',
    'continuous_years_covered': 2,
    'ped_waiting_period_months': 36,
}
r3 = generate_report(extracted, rec, 'reports')
print("JSON report: " + os.path.basename(r3['json_report']))
print("HTML report: " + os.path.basename(r3['html_report']))

from tools.form_filler import fill_portability_form
r4 = fill_portability_form(extracted, rec, 'reports')
if r4.get('form_pdf'):
    print("Form PDF: " + os.path.basename(r4['form_pdf']))
else:
    print("Form error: " + str(r4.get('error')))

print("ALL TOOLS OK")
