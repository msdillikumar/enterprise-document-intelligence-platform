"""
API client for communicating with the FastAPI backend.
"""
import os
import requests
from typing import Dict, List, Optional

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")


def _url(path: str) -> str:
    return f"{API_BASE}{path}"


# ── Stats ────────────────────────────────────────────────────────────

def get_stats() -> Dict:
    """Fetch dashboard statistics."""
    try:
        r = requests.get(_url("/documents/stats"), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Documents ────────────────────────────────────────────────────────

def list_documents(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict:
    """List documents with pagination/filtering."""
    params = {"skip": skip, "limit": limit}
    if status:
        params["status"] = status
    if search:
        params["search"] = search
    try:
        r = requests.get(_url("/documents"), params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "documents": [], "total": 0}


def get_document(doc_id: int) -> Dict:
    """Get full document details."""
    try:
        r = requests.get(_url(f"/documents/{doc_id}"), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def delete_document(doc_id: int) -> Dict:
    """Delete a document."""
    try:
        r = requests.delete(_url(f"/documents/{doc_id}"), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_entities(doc_id: int) -> Dict:
    """Get entities for a document."""
    try:
        r = requests.get(_url(f"/documents/{doc_id}/entities"), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "entities": []}


# ── Upload ───────────────────────────────────────────────────────────

def upload_document(file_bytes: bytes, filename: str) -> Dict:
    """Upload a single document."""
    try:
        files = {"file": (filename, file_bytes)}
        r = requests.post(_url("/upload"), files=files, timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "success": False}


def upload_batch(file_list: List) -> Dict:
    """Upload multiple documents."""
    try:
        files = [("files", (f.name, f.read())) for f in file_list]
        r = requests.post(_url("/upload/batch"), files=files, timeout=300)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "success": False}


# ── Health ───────────────────────────────────────────────────────────

def check_health() -> Dict:
    """Check API health."""
    try:
        r = requests.get(f"{API_BASE.replace('/api', '')}/health", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"status": "unreachable"}
