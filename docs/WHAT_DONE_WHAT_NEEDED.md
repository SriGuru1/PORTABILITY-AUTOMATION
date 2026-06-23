# AntiGravity Agent — Status Board

## ✅ WHAT'S DONE

### Architecture
- [x] Google ADK multi-agent architecture (Orchestrator → 3 sub-agents)
- [x] Modular tool layer (pdf_extractor, llm_parser, plan_matcher, report_generator)
- [x] Config management (.env, settings.py)

### Extraction Pipeline
- [x] PDF text extraction via pdfplumber (primary) and PyPDF2 (fallback)
- [x] URL-based PDF download and extraction
- [x] LLM-based field extraction using Claude claude-sonnet-4-6 or Gemini 1.5 Flash
- [x] Extracts 25+ fields: name, DOB, policy number, sum insured, NCB, premium, PEDs, waiting periods, family members, room rent limits, etc.
- [x] Handles both Annexure A portability form format AND full policy wording PDFs (like the 15-page Apex policy)

### Analysis
- [x] IRDAI portability eligibility check (45-day rule, minimum 1 year coverage)
- [x] Coverage gap analysis with scoring (0-100)
- [x] PED waiting period credit calculation
- [x] Co-payment, room rent cap, sum insured adequacy checks

### Plan Matching
- [x] Prudential plan catalogue (4 plans: Basic, Plus, Elite, Family Floater)
- [x] Scoring algorithm: SI match, PED credit, premium comparison, feature bonuses
- [x] Verdict generation (STRONGLY RECOMMENDED / RECOMMENDED / CONSIDER / REVIEW)
- [x] All-options comparison table

### Reporting
- [x] Structured JSON report with full customer + policy + recommendation data
- [x] HTML report with visual comparison table, verdict badge, savings box
- [x] Report saved to /reports/ directory with timestamp

### Testing
- [x] Unit tests for all tools (pdf_extractor, llm_parser, plan_matcher, analysis, report_generator)
- [x] pytest-compatible test suite

---

## 🔧 WHAT'S NEEDED (Next Steps)

### Priority 1 — Critical for Production
- [ ] **Real Prudential Product API** — Replace `plans.json` with live API for accurate premiums and plan details
- [ ] **OCR for Scanned PDFs** — Integrate Google Document AI or Tesseract; many uploaded policies are image-based scans
- [ ] **ANTHROPIC_API_KEY / GOOGLE_API_KEY setup** — Teams need to add .env credentials before running

### Priority 2 — Integration
- [ ] **Group A Integration** — Accept pre-digitized PDF output from Group A's document digitization pipeline
- [ ] **Group B Integration** — Accept PII-redacted PDFs from Group B; handle masked fields gracefully
- [ ] **Webhook / REST API** — Expose `/analyse` endpoint so other systems can call AntiGravity

### Priority 3 — Features
- [ ] **Underwriter Review Flag** — Auto-flag cases with complex PEDs or high sum insured for human review
- [ ] **Premium Calculator** — Live premium quotes from Prudential underwriting rules engine
- [ ] **Email/SMS Report Delivery** — Send report to customer's email/mobile after analysis
- [ ] **Portability Form Auto-fill** — Auto-fill IRDAI Annexure A portability form from extracted data
- [ ] **Multi-language Support** — Extract from Hindi/regional language PDFs

### Priority 4 — Infrastructure
- [ ] **Database** — Persist all extractions and recommendations (PostgreSQL / Firestore)
- [ ] **Frontend UI** — Customer-facing web interface for PDF upload and report viewing
- [ ] **Authentication** — Customer login, agent login, role-based access
- [ ] **Audit Log** — Track all extractions for compliance and IRDAI reporting

---

## HOW TO RUN NOW

```bash
# Install dependencies
pip install -r requirements.txt

# Set up credentials
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY

# Run on a local PDF
python main.py --pdf path/to/policy.pdf --mode direct

# Run on URL
python main.py --pdf https://storage.googleapis.com/test_sa_1/individual_health_insurance_15_page_policy.pdf --mode direct

# Run tests
python -m pytest tests/ -v
```
