from __future__ import annotations

from fastapi import Depends, Header

from core.errors import ApiException
from core.store import store


async def require_bearer(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiException(401, "AUTH_401_UNAUTHORIZED", "missing or invalid bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiException(401, "AUTH_401_UNAUTHORIZED", "missing or invalid bearer token")
    user_id = store.resolve_user_id_by_access(token)
    if user_id is None:
        raise ApiException(401, "AUTH_401_TOKEN_EXPIRED", "access token expired", retriable=True)
    return str(user_id)


async def require_admin(user_id: str = Depends(require_bearer)) -> str:
    if not store.is_admin_user(user_id):
        raise ApiException(403, "AUTH_403_FORBIDDEN", "admin role required")
    return user_id


async def require_audit_reviewer(user_id: str = Depends(require_bearer)) -> str:
    if not store.is_audit_reviewer(user_id):
        raise ApiException(403, "AUTH_403_FORBIDDEN", "audit reviewer role required")
    return user_id
