"""
Upload Router - Handles document upload and triggers the processing pipeline.
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..services.pipeline import process_document
from ..config import COMPLIANCE_RULES
from ..models import User
from ..auth import get_current_user  # type: ignore[import-not-found]
from ..services.audit import log_action, get_client_ip  # type: ignore[import-not-found]

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for processing.
    Triggers the full pipeline:
    Encryption → OCR → NLP → Confidence → Compliance → Redaction → Storage
    """
    # Validate file type
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed = COMPLIANCE_RULES.get("allowed_formats", [])
    if ext and ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: {allowed}",
        )

    # Read file
    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Process through pipeline
    result = await process_document(file_data, filename, db, uploaded_by=user.id if user else None)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))

    # Audit log
    if user:
        await log_action(db, "upload", "document", str(result.get("document_id", "")),
                         {"filename": filename, "size": len(file_data)},
                         user.id, user.username, get_client_ip(request))
        await db.commit()

    return result


@router.post("/upload/batch")
async def upload_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and process multiple documents."""
    results = []
    for file in files:
        file_data = await file.read()
        result = await process_document(file_data, file.filename or "unknown", db,
                                        uploaded_by=user.id if user else None)
        results.append(result)
    if user:
        await log_action(db, "upload", "document", "",
                         {"batch": True, "count": len(files)},
                         user.id, user.username, get_client_ip(request))
        await db.commit()
    return {"total": len(results), "results": results}
