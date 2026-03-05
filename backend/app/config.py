"""
Enterprise Document Intelligence & Secure Data Extraction Platform
Configuration – v2 (LLM + SHAP + Supabase + Streamlit)
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# ── Database ──────────────────────────────────────────────────────────
# Supabase PostgreSQL (production) or SQLite (local dev)
_raw_db_url = os.getenv("DATABASE_URL", "")
if _raw_db_url:
    # Render / Supabase supply postgres:// – SQLAlchemy needs postgresql+asyncpg://
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif _raw_db_url.startswith("postgresql://"):
        _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    DATABASE_URL = _raw_db_url
else:
    DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR / 'documents.db'}"

# ── Encryption ────────────────────────────────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", None)  # Auto-generated if not set

# ── OCR Configuration ─────────────────────────────────────────────────
# PaddleOCR is preferred; Tesseract is a fallback
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
PADDLEOCR_LANG = os.getenv("PADDLEOCR_LANG", "en")

# ── LLM Configuration ────────────────────────────────────────────────
LLM_REPO_ID = os.getenv(
    "LLM_REPO_ID",
    "cuongbuift/invoice-extraction-v2-llama-2-7b-v2-Q4_0-GGUF",
)
LLM_FILENAME = os.getenv(
    "LLM_FILENAME",
    "invoice-extraction-v2-llama-2-7b-v2.Q4_0.gguf",
)
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# ── Confidence / Explainability ───────────────────────────────────────
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.6"))

# ── PII entity types to redact ────────────────────────────────────────
PII_ENTITIES = [
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
    "CREDIT_CARD", "US_SSN", "IBAN_CODE",
    "IP_ADDRESS", "US_PASSPORT", "US_DRIVER_LICENSE",
    "SSN", "EMAIL", "PHONE",
]

# ── Compliance rules ─────────────────────────────────────────────────
COMPLIANCE_RULES = {
    "required_fields": ["date", "amount", "name"],
    "max_document_age_days": 365,
    "allowed_formats": [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
}

# ── CORS ──────────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8501,http://localhost:5173",
).split(",")

# ── JWT / Auth ────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ── Supabase (optional, for direct API calls) ────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
