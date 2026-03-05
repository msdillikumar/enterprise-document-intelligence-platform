"""
Documents Router - CRUD, search, export, and statistics endpoints.
"""
import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from ..database import get_db
from ..models import Document, ExtractedEntity, User
from ..auth import get_current_user, require_auth, require_permission  # type: ignore[import-not-found]
from ..services.audit import log_action, get_client_ip  # type: ignore[import-not-found]

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    compliance: str = Query(None),
    entity_type: str = Query(None),
    min_confidence: float = Query(None),
    search: str = Query(None),
    doc_type: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents with pagination, filtering, and enhanced search."""
    query = select(Document).options(selectinload(Document.entities)).order_by(desc(Document.upload_time))

    filters = []
    if status:
        filters.append(Document.status == status)
    if compliance:
        filters.append(Document.compliance_status == compliance)
    if min_confidence is not None:
        filters.append(Document.confidence_score >= min_confidence)
    if search:
        filters.append(
            Document.original_filename.ilike(f"%{search}%")
            | Document.raw_text.ilike(f"%{search}%")
        )
    if doc_type:
        filters.append(Document.document_type == doc_type)
    if filters:
        query = query.where(and_(*filters))

    # If filtering by entity_type, join with entities table
    if entity_type:
        query = query.where(
            Document.id.in_(
                select(ExtractedEntity.document_id).where(
                    ExtractedEntity.entity_type.ilike(f"%{entity_type}%")
                )
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    docs = result.scalars().all()

    # Total count with same filters
    count_query = select(func.count(Document.id))
    if status:
        count_query = count_query.where(Document.status == status)
    if compliance:
        count_query = count_query.where(Document.compliance_status == compliance)
    total = (await db.execute(count_query)).scalar()

    if user and search:
        await log_action(db, "search", "document", "", {"query": search},
                         user.id, user.username, get_client_ip(request))
        await db.commit()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "documents": [doc.to_dict() for doc in docs],
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get advanced dashboard statistics with analytics and chart data."""
    total = (await db.execute(select(func.count(Document.id)))).scalar()
    completed = (await db.execute(
        select(func.count(Document.id)).where(Document.status == "completed")
    )).scalar()
    failed = (await db.execute(
        select(func.count(Document.id)).where(Document.status == "failed")
    )).scalar()
    avg_confidence = (await db.execute(
        select(func.avg(Document.confidence_score)).where(Document.status == "completed")
    )).scalar()
    avg_processing = (await db.execute(
        select(func.avg(Document.processing_time_ms)).where(Document.status == "completed")
    )).scalar()
    total_entities = (await db.execute(
        select(func.count(ExtractedEntity.id))
    )).scalar()
    pii_count = (await db.execute(
        select(func.count(ExtractedEntity.id)).where(ExtractedEntity.is_pii == True)
    )).scalar()
    compliant = (await db.execute(
        select(func.count(Document.id)).where(Document.compliance_status == "compliant")
    )).scalar()
    warning_count = (await db.execute(
        select(func.count(Document.id)).where(Document.compliance_status == "warning")
    )).scalar()
    non_compliant = (await db.execute(
        select(func.count(Document.id)).where(Document.compliance_status == "non_compliant")
    )).scalar()

    # ── Advanced Analytics ──────────────────────────────────────────────
    # Compliance percentage
    compliance_pct = round((compliant / total * 100) if total else 0, 1)

    # Risk score: weighted average of anomaly scores (0-100)
    avg_anomaly_result = await db.execute(
        select(func.avg(Document.anomaly_score)).where(Document.status == "completed")
    )
    avg_anomaly = avg_anomaly_result.scalar() or 0
    risk_score = round(min(avg_anomaly * 100, 100), 1)

    # Total amounts / GST from extracted entities
    amount_entities = await db.execute(
        select(ExtractedEntity.entity_value).where(
            ExtractedEntity.entity_type.in_(["TOTAL_AMOUNT", "AMOUNT", "INVOICE_TOTAL"])
        )
    )
    total_amount = 0.0
    for row in amount_entities.all():
        try:
            import re as _re
            nums = _re.findall(r"[\d,]+\.?\d*", str(row[0]))
            if nums:
                total_amount += float(nums[0].replace(",", ""))
        except (ValueError, IndexError):
            pass

    gst_entities = await db.execute(
        select(ExtractedEntity.entity_value).where(
            ExtractedEntity.entity_type.in_(["TAX_AMOUNT", "GST_AMOUNT", "TAX"])
        )
    )
    total_gst = 0.0
    for row in gst_entities.all():
        try:
            import re as _re
            nums = _re.findall(r"[\d,]+\.?\d*", str(row[0]))
            if nums:
                total_gst += float(nums[0].replace(",", ""))
        except (ValueError, IndexError):
            pass

    # Monthly document volume (last 12 months)
    monthly_result = await db.execute(
        select(
            func.strftime("%Y-%m", Document.upload_time).label("month"),
            func.count(Document.id).label("count"),
        )
        .where(Document.status == "completed")
        .group_by("month")
        .order_by("month")
        .limit(12)
    )
    monthly_volume = [
        {"month": row[0], "count": row[1]} for row in monthly_result.all()
    ]

    # Document type distribution
    doc_type_result = await db.execute(
        select(Document.document_type, func.count(Document.id))
        .where(Document.document_type.isnot(None))
        .group_by(Document.document_type)
        .order_by(desc(func.count(Document.id)))
    )
    doc_type_distribution = [
        {"type": row[0], "count": row[1]} for row in doc_type_result.all()
    ]

    # Entity type distribution for charts
    entity_dist_result = await db.execute(
        select(ExtractedEntity.entity_type, func.count(ExtractedEntity.id))
        .group_by(ExtractedEntity.entity_type)
        .order_by(desc(func.count(ExtractedEntity.id)))
        .limit(10)
    )
    entity_distribution = [
        {"type": row[0], "count": row[1]} for row in entity_dist_result.all()
    ]

    # Confidence distribution for histogram
    conf_buckets = []
    for low, high, label in [
        (0, 0.25, "0-25%"), (0.25, 0.5, "25-50%"),
        (0.5, 0.75, "50-75%"), (0.75, 1.01, "75-100%"),
    ]:
        count = (await db.execute(
            select(func.count(Document.id)).where(
                and_(Document.confidence_score >= low, Document.confidence_score < high)
            )
        )).scalar()
        conf_buckets.append({"range": label, "count": count or 0})

    # Recent processing times
    recent_result = await db.execute(
        select(Document.original_filename, Document.processing_time_ms, Document.upload_time)
        .where(Document.status == "completed")
        .order_by(desc(Document.upload_time))
        .limit(10)
    )
    recent_processing = [
        {"name": row[0][:20], "time_ms": row[1], "date": row[2].isoformat() if row[2] else None}
        for row in recent_result.all()
    ]

    return {
        "total_documents": total,
        "completed": completed,
        "failed": failed,
        "processing": total - completed - failed,
        "avg_confidence": round(avg_confidence or 0, 3),
        "avg_processing_time_ms": round(avg_processing or 0, 0),
        "total_entities_extracted": total_entities,
        "pii_detected": pii_count,
        "compliant_documents": compliant,
        "warning_documents": warning_count or 0,
        "non_compliant_documents": non_compliant or 0,
        # ── Advanced Analytics ──
        "compliance_percentage": compliance_pct,
        "risk_score": risk_score,
        "total_amount": round(total_amount, 2),
        "total_gst": round(total_gst, 2),
        "charts": {
            "entity_distribution": entity_distribution,
            "confidence_distribution": conf_buckets,
            "compliance_breakdown": [
                {"name": "Compliant", "value": compliant or 0},
                {"name": "Warning", "value": warning_count or 0},
                {"name": "Non-Compliant", "value": non_compliant or 0},
            ],
            "recent_processing_times": recent_processing,
            "monthly_volume": monthly_volume,
            "document_type_distribution": doc_type_distribution,
        },
    }


@router.get("/{doc_id}")
async def get_document(doc_id: int, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get full details of a specific document."""
    result = await db.execute(
        select(Document).options(selectinload(Document.entities)).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if user:
        await log_action(db, "view", "document", str(doc_id), {},
                         user.id, user.username, get_client_ip(request))
        await db.commit()
    return doc.to_dict()


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    request: Request,
    user: User = Depends(require_permission("delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its entities (admin only)."""
    result = await db.execute(
        select(Document).options(selectinload(Document.entities)).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await log_action(db, "delete", "document", str(doc_id),
                     {"filename": doc.original_filename},
                     user.id, user.username, get_client_ip(request))
    await db.delete(doc)
    await db.commit()
    return {"message": f"Document {doc_id} deleted"}


@router.get("/{doc_id}/entities")
async def get_entities(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Get all extracted entities for a document."""
    result = await db.execute(
        select(ExtractedEntity).where(ExtractedEntity.document_id == doc_id)
    )
    entities = result.scalars().all()
    return {"document_id": doc_id, "entities": [e.to_dict() for e in entities]}


# ── Export Endpoints ──────────────────────────────────────────────────
@router.get("/{doc_id}/export/json")
async def export_json(doc_id: int, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Export document data as downloadable JSON."""
    result = await db.execute(
        select(Document).options(selectinload(Document.entities)).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    data = doc.to_dict()
    content = json.dumps(data, indent=2, default=str)
    if user:
        await log_action(db, "export", "document", str(doc_id), {"format": "json"},
                         user.id, user.username, get_client_ip(request))
        await db.commit()
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="doc_{doc_id}_export.json"'},
    )


@router.get("/{doc_id}/export/csv")
async def export_csv(doc_id: int, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Export document entities as downloadable CSV."""
    result = await db.execute(
        select(Document).options(selectinload(Document.entities)).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Entity Type", "Value", "Confidence", "PII", "Method"])
    for e in doc.entities:
        writer.writerow([
            e.entity_type,
            e.redacted_value if e.is_pii else e.entity_value,
            f"{(e.confidence or 0) * 100:.1f}%",
            "Yes" if e.is_pii else "No",
            e.extraction_method or "",
        ])

    content = output.getvalue()
    if user:
        await log_action(db, "export", "document", str(doc_id), {"format": "csv"},
                         user.id, user.username, get_client_ip(request))
        await db.commit()
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="doc_{doc_id}_entities.csv"'},
    )
