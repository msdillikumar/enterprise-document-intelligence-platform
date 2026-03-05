"""
Auth Router – Registration, Login, User management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..database import get_db
from ..models import User
from ..auth import (  # type: ignore[import-not-found]
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_auth,
    require_role,
    ROLE_PERMISSIONS,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response Schemas ────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = ""
    role: Optional[str] = "user"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")

    valid_roles = list(ROLE_PERMISSIONS.keys())
    role = req.role if req.role in valid_roles else "user"

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name or "",
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login and receive a JWT token."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    token = create_access_token({"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@router.get("/me")
async def get_me(user: User = Depends(require_auth)):
    """Get current authenticated user profile."""
    return user.to_dict()


@router.get("/users")
async def list_users(
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {"users": [u.to_dict() for u in users]}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    update: UserUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if update.full_name is not None:
        target.full_name = update.full_name
    if update.role is not None and update.role in ROLE_PERMISSIONS:
        target.role = update.role
    if update.is_active is not None:
        target.is_active = update.is_active

    await db.commit()
    await db.refresh(target)
    return target.to_dict()


@router.get("/roles")
async def get_roles():
    """Get available roles and their permissions."""
    return {
        "roles": [
            {"key": role, "permissions": perms}
            for role, perms in ROLE_PERMISSIONS.items()
        ]
    }
