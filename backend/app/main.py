"""
Enterprise Document Intelligence & Secure Data Extraction Platform
FastAPI Application Entry Point – v4

Pipeline: Upload → AES Encryption → PaddleOCR (Layout-aware) → LLM Entity Extraction →
          Document Classification → Confidence Scoring → SHAP Explainability →
          Anomaly Detection → Compliance Check → PII Redaction → Database Storage → Dashboard

Security: JWT/OAuth2 Authentication, RBAC, Audit Logging
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .config import CORS_ORIGINS
from .routers import upload, documents
from .routers import auth as auth_router
from .routers import audit as audit_router
from .services.task_manager import get_task_progress, get_all_active_tasks  # type: ignore[import-not-found]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Enterprise Document Intelligence Platform",
    description=(
        "AI-powered document intelligence platform using Generative AI (LLM) "
        "for entity extraction, SHAP for explainability, statistical "
        "anomaly detection, and auto document classification. "
        "Secured with AES-256 encryption, JWT/OAuth2 RBAC, PII redaction, and audit logging."
    ),
    version="4.0.0",
    lifespan=lifespan,
)

# CORS – allow Streamlit (8501) and dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload.router)
app.include_router(documents.router)
app.include_router(auth_router.router)
app.include_router(audit_router.router)


# ── Progress Tracking Endpoints ───────────────────────────────────────
@app.get("/api/documents/{doc_id}/progress")
async def document_progress(doc_id: int):
    """Get real-time processing progress for a document."""
    progress = get_task_progress(doc_id)
    if not progress:
        raise HTTPException(status_code=404, detail="No active task for this document")
    return progress


@app.get("/api/tasks/active")
async def active_tasks():
    """Get all active processing tasks."""
    return {"tasks": get_all_active_tasks()}


@app.get("/")
async def root():
    return {
        "name": "Enterprise Document Intelligence Platform",
        "version": "4.0.0",
        "pipeline": [
            "1. User Upload",
            "2. AES-256 Encryption (Fernet)",
            "3. PaddleOCR Layout-Aware Text Extraction",
            "4. LLM Entity Extraction (Transformer-based Gen-AI)",
            "5. Auto Document Classification",
            "6. Confidence Scoring",
            "7. SHAP Explainability (Feature Attribution)",
            "8. Anomaly Detection (Statistical + Rule-based + Financial)",
            "9. Authenticity & Compliance Check",
            "10. PII Redaction",
            "11. Database Storage (Supabase PostgreSQL)",
            "12. React Dashboard Visualization",
        ],
        "security": [
            "JWT/OAuth2 Authentication",
            "Role-Based Access Control (RBAC)",
            "AES-256 File Encryption",
            "PII Redaction (Presidio)",
            "Audit Logging",
        ],
        "technologies": {
            "ocr": "PaddleOCR (layout-aware, with Tesseract fallback)",
            "gen_ai": "llama-cpp-python / HuggingFace Inference",
            "explainability": "SHAP (perturbation-based)",
            "encryption": "AES-256 (Fernet / cryptography)",
            "anomaly_detection": "Isolation Forest + Z-score + Financial Rules",
            "classification": "Keyword + Entity Hybrid Classifier",
            "auth": "JWT/OAuth2 + RBAC",
            "database": "PostgreSQL (Supabase) / SQLite (dev)",
            "frontend": "React + Recharts",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "4.0.0"}
