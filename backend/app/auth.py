"""
Authentication & Authorization Module
JWT token handling, password hashing, role-based access control.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ── Lazy imports for optional deps ────────────────────────────────────
try:
    from jose import JWTError, jwt  # type: ignore[import-not-found]
except ImportError:
    jwt = None  # type: ignore
    JWTError = Exception

try:
    import bcrypt as _bcrypt  # type: ignore[import-not-found]
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

from .config import JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from .database import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ── Role hierarchy & permissions ──────────────────────────────────────
ROLE_PERMISSIONS = {
    "admin": ["upload", "view", "delete", "search", "export", "audit_logs", "manage_users"],
    "auditor": ["view", "search", "export", "audit_logs"],
    "finance_user": ["upload", "view", "search", "export"],
    "compliance_officer": ["view", "search", "export", "audit_logs"],
    "user": ["upload", "view", "search"],
}


# ═══════════════════════════════════════════════════════════════════════
#  Password Hashing
# ═══════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    if _HAS_BCRYPT:
        return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
    # Fallback: simple hash (NOT for production)
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    if _HAS_BCRYPT:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    import hashlib
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


# ═══════════════════════════════════════════════════════════════════════
#  JWT Token Management
# ═══════════════════════════════════════════════════════════════════════

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    if jwt:
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # Fallback: base64 token (NOT for production)
    import json, base64
    return base64.urlsafe_b64encode(json.dumps(to_encode, default=str).encode()).decode()


def decode_access_token(token: str) -> Optional[dict]:
    try:
        if jwt:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        # Fallback decode
        import json, base64
        payload = json.loads(base64.urlsafe_b64decode(token.encode()))
        return payload
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
#  Dependencies
# ═══════════════════════════════════════════════════════════════════════

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user from the JWT token.
    Returns None for unauthenticated requests (endpoints that allow anonymous).
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    username: str = payload.get("sub", "")
    if not username:
        return None

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    return user


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authenticated user — raises 401 if not logged in."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    return user


def require_role(*allowed_roles: str):
    """Factory: require user has one of the specified roles."""
    async def _check(user: User = Depends(require_auth)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' does not have permission. Required: {allowed_roles}",
            )
        return user
    return _check


def require_permission(permission: str):
    """Factory: require user has a specific permission."""
    async def _check(user: User = Depends(require_auth)) -> User:
        perms = ROLE_PERMISSIONS.get(user.role, [])
        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' denied for role '{user.role}'",
            )
        return user
    return _check
