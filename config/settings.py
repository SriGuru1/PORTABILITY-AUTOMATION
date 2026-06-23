"""Central configuration for AntiGravity Agent."""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Model
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PLANS_FILE = os.path.join(DATA_DIR, "prudential_plans", "plans.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Extraction config
MAX_PDF_PAGES = 50
EXTRACTION_TEMPERATURE = 0.1   # Low temp for accurate extraction

# Portability rules (IRDAI)
IRDAI_PORTABILITY_NOTICE_DAYS = 45   # Must apply 45 days before expiry
MIN_CONTINUOUS_COVERAGE_YEARS = 1
