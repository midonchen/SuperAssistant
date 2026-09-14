from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from core.auth_dep import require_bearer
from core.response import failure, success
from core.schemas import utc_now
from core.store import store

router = APIRouter(prefix="/auth", tags=["auth"])


class SmsSendRequest(BaseModel):
    phone: str
    purpose: str


class SmsLoginRequest(BaseModel):
    phone: str
    code: str
    device_id: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str
    device_id: str


class LogoutRequest(BaseModel):
    session_id: str


class AccountDeleteRequest(BaseModel):
    verify_code: str
    reason: str | None = None


@router.post("/sms/send")
async def sms_send(payload: SmsSendRequest, request: Request):
    if len(payload.phone) < 11:
        return failure(request, 400, "VAL_400_INVALID_PARAM", "invalid phone format")
    return success(request, {"expire_in": 300, "retry_after": 60})


@router.post("/sms/login")
async def sms_login(payload: SmsLoginRequest, request: Request):
    user_id, profile = store.bootstrap_user(payload.phone)
    sid, access_token, refresh_token = store.upsert_session(user_id, payload.device_id)
    return success(
        request,
        {
            "session_id": sid,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 7200,
            "user_profile": profile.model_dump(mode="json"),
        },
    )


@router.post("/token/refresh")
async def token_refresh(payload: TokenRefreshRequest, request: Request):
    rotated = store.rotate_session_tokens_by_refresh(payload.refresh_token, payload.device_id)
    if rotated is None:
        return failure(request, 401, "AUTH_401_TOKEN_EXPIRED", "refresh token expired", retriable=True)
    session_id, access_token, refresh_token = rotated
    return success(
        request,
        {
            "session_id": session_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 7200,
        },
    )


@router.post("/logout")
async def logout(payload: LogoutRequest, request: Request, user_id: str = Depends(require_bearer)):
    revoked = store.revoke_session_owned(payload.session_id, user_id)
    return success(request, {"success": revoked})


@router.delete("/account")
async def account_delete(payload: AccountDeleteRequest, request: Request):
    cool_down_end = utc_now() + timedelta(days=7)
    return success(request, {"cool_down_end_at": cool_down_end.isoformat()})
