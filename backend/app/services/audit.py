"""
Audit Logging Service
Logs all user actions for compliance and security tracking.
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import AuditLog

logger = logging.getLogger(__name__)


async def log_action(
    db: AsyncSession,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    username: str = "anonymous",
    ip_address: str = "",
) -> AuditLog:
    """
    Record an audit log entry.

    Actions: login, logout, register, upload, view, search, download, delete, export, update
    Resource types: document, user, system
    """
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()  # flush so the caller's commit picks it up
    logger.info(f"AUDIT: [{username}] {action} {resource_type}/{resource_id}")
    return entry


def get_client_ip(request) -> str:
    """Extract client IP from request (handles proxies)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if hasattr(request, "client") and request.client:
        return request.client.host
    return ""
