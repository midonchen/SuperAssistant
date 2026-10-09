from __future__ import annotations

import hashlib
import os

import httpx

WECHAT_JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def exchange_code(code: str) -> str:
    """Exchange a wx.login() code for the user's openid.

    In production this calls WeChat's jscode2session API. When WECHAT_MOCK=1
    (or no AppID/AppSecret is configured) it returns a deterministic mock
    openid so the flow is testable without a live mini program.
    """
    appid = os.getenv("WECHAT_APPID", "").strip()
    secret = os.getenv("WECHAT_APPSECRET", "").strip()
    mock = os.getenv("WECHAT_MOCK", "").strip() == "1"
    if mock or not appid or not secret:
        return "mock-" + hashlib.sha256(code.encode()).hexdigest()[:40]
    try:
        resp = httpx.get(
            WECHAT_JSCODE2SESSION_URL,
            params={
                "appid": appid,
                "secret": secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — surface any transport/parse failure uniformly
        raise RuntimeError(f"wechat code2session request failed: {exc}") from exc
    if "openid" not in data:
        raise RuntimeError(f"wechat code2session failed: {data.get('errcode')} {data.get('errmsg')}")
    return data["openid"]
