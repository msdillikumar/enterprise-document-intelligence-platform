"""
Audit Logs Router – View audit trail (admin/auditor only).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from ..database import get_db
from ..models import AuditLog, User
from ..auth import require_role  # type: ignore[import-not-found]

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: str = Query(None),
    username: str = Query(None),
    resource_type: str = Query(None),
    user: User = Depends(require_role("admin", "auditor", "compliance_officer")),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs with filtering (admin/auditor/compliance only)."""
    query = select(AuditLog).order_by(desc(AuditLog.timestamp))

    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if username:
        filters.append(AuditLog.username.ilike(f"%{username}%"))
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if filters:
        query = query.where(and_(*filters))

    # Total count
    count_q = select(func.count(AuditLog.id))
    if filters:
        count_q = count_q.where(and_(*filters))
    total = (await db.execute(count_q)).scalar()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": [log.to_dict() for log in logs],
    }


@router.get("/stats")
async def audit_stats(
    user: User = Depends(require_role("admin", "auditor")),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log summary statistics."""
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar()

    # Actions breakdown
    action_result = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
        .order_by(desc(func.count(AuditLog.id)))
    )
    actions = [{"action": r[0], "count": r[1]} for r in action_result.all()]

    # Top users
    user_result = await db.execute(
        select(AuditLog.username, func.count(AuditLog.id))
        .group_by(AuditLog.username)
        .order_by(desc(func.count(AuditLog.id)))
        .limit(10)
    )
    top_users = [{"username": r[0], "count": r[1]} for r in user_result.all()]

    return {
        "total_events": total,
        "actions_breakdown": actions,
        "top_users": top_users,
    }
