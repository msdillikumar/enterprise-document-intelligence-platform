"""
Background Task Manager
Handles async document processing with progress tracking.
Uses in-memory state for demo; use Redis/Celery for production.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory task progress store (use Redis in production)
_task_progress: Dict[int, Dict[str, Any]] = {}

PIPELINE_STEPS = [
    "encrypting",
    "ocr_extraction",
    "entity_extraction",
    "classification",
    "confidence_scoring",
    "explainability",
    "anomaly_detection",
    "compliance_check",
    "pii_redaction",
    "storage",
]


def init_task(doc_id: int) -> None:
    """Initialize progress tracking for a document."""
    _task_progress[doc_id] = {
        "document_id": doc_id,
        "status": "processing",
        "current_step": 0,
        "total_steps": len(PIPELINE_STEPS),
        "step_name": PIPELINE_STEPS[0],
        "percent": 0,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "error": None,
    }


def update_task(doc_id: int, step: int, step_name: str = "") -> None:
    """Update the current step for a task."""
    if doc_id not in _task_progress:
        return
    _task_progress[doc_id]["current_step"] = step
    _task_progress[doc_id]["step_name"] = step_name or PIPELINE_STEPS[min(step, len(PIPELINE_STEPS) - 1)]
    _task_progress[doc_id]["percent"] = int((step / len(PIPELINE_STEPS)) * 100)


def complete_task(doc_id: int, success: bool = True, error: str = "") -> None:
    """Mark a task as completed or failed."""
    if doc_id not in _task_progress:
        return
    _task_progress[doc_id]["status"] = "completed" if success else "failed"
    _task_progress[doc_id]["percent"] = 100 if success else _task_progress[doc_id]["percent"]
    _task_progress[doc_id]["completed_at"] = datetime.utcnow().isoformat()
    _task_progress[doc_id]["error"] = error if error else None
    _task_progress[doc_id]["step_name"] = "done" if success else "failed"


def get_task_progress(doc_id: int) -> Optional[Dict[str, Any]]:
    """Get progress for a specific document processing task."""
    return _task_progress.get(doc_id)


def get_all_active_tasks() -> list:
    """Get all currently processing tasks."""
    return [
        v for v in _task_progress.values()
        if v["status"] == "processing"
    ]


def cleanup_old_tasks(max_completed: int = 100) -> None:
    """Remove old completed tasks from memory."""
    completed = [
        k for k, v in _task_progress.items()
        if v["status"] in ("completed", "failed")
    ]
    if len(completed) > max_completed:
        for k in completed[:len(completed) - max_completed]:
            del _task_progress[k]
