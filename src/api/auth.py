"""SiteNarrator — Authentication and authorization.

JWT-based auth with role-based access control.
Roles: superintendent, project_coordinator, project_manager, client, ops
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config import get_settings

security = HTTPBearer()


class UserToken(BaseModel):
    """Decoded JWT token payload."""
    user_id: str
    name: str
    email: str
    role: str  # superintendent | project_coordinator | project_manager | client | ops
    project_ids: list[str] = []


def create_access_token(
    user_id: str,
    name: str,
    email: str,
    role: str,
    project_ids: list[str] = None,
    expires_hours: int = 24,
) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    payload = {
        "sub": user_id,
        "name": name,
        "email": email,
        "role": role,
        "project_ids": project_ids or [],
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_token(token: str) -> UserToken:
    """Decode and validate a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
        return UserToken(
            user_id=payload["sub"],
            name=payload["name"],
            email=payload["email"],
            role=payload["role"],
            project_ids=payload.get("project_ids", []),
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserToken:
    """FastAPI dependency to get the current authenticated user."""
    return decode_token(credentials.credentials)


def require_role(*roles: str):
    """FastAPI dependency factory to require specific roles."""
    async def role_checker(user: UserToken = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' does not have access. Required: {roles}",
            )
        return user
    return role_checker
