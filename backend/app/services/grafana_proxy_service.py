import hashlib
import hmac
import logging
import secrets
import time
from typing import Dict, Optional
from urllib.parse import quote, urljoin

import httpx
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.config import settings
from app.services.log_integration_service import resolve_grafana_upstream

logger = logging.getLogger(__name__)

GRAFANA_PROXY_PREFIX = "/api/v1/logs/grafana"
COOKIE_NAME = "grafana_proxy_sess"
LAUNCH_TTL = 120
SESSION_TTL = 8 * 3600

_launch_tokens: Dict[str, dict] = {}

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def _sign_payload(payload: str) -> str:
    signature = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def _verify_signed(token: str) -> Optional[str]:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    return payload


def create_launch_token(user_id: int, username: str, role: str) -> str:
    token = secrets.token_urlsafe(32)
    _launch_tokens[token] = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": time.time() + LAUNCH_TTL,
    }
    return token


def consume_launch_token(token: str) -> dict:
    data = _launch_tokens.pop(token, None)
    if not data or data["exp"] < time.time():
        raise HTTPException(status_code=400, detail="链接已失效，请从平台重新打开")
    return data


def create_session_cookie(user_ctx: dict) -> str:
    payload = f"{user_ctx['user_id']}:{user_ctx['username']}:{user_ctx['role']}:{int(time.time()) + SESSION_TTL}"
    return _sign_payload(payload)


def resolve_user_from_cookie(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    payload = _verify_signed(token)
    if not payload:
        return None
    try:
        user_id, username, role, exp = payload.split(":", 3)
        if int(exp) < time.time():
            return None
        return {"user_id": int(user_id), "username": username, "role": role}
    except (TypeError, ValueError):
        return None


def build_public_origin(request: Request, fallback_origin: Optional[str] = None) -> str:
    if fallback_origin:
        return fallback_origin.rstrip("/")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    return f"{scheme}://{host}"


def build_launch_url(origin: str, user_id: int, username: str, role: str, redirect: str) -> str:
    token = create_launch_token(user_id, username, role)
    redirect_path = redirect if redirect.startswith("/") else f"/{redirect}"
    return (
        f"{origin}{GRAFANA_PROXY_PREFIX}/enter"
        f"?token={quote(token)}&redirect={quote(redirect_path)}"
    )


def build_enter_response(token: str, redirect: str) -> RedirectResponse:
    user_ctx = consume_launch_token(token)
    redirect_path = redirect if redirect.startswith("/") else f"/{redirect}"
    if not redirect_path.startswith("/"):
        redirect_path = f"/{redirect_path}"
    session = create_session_cookie(user_ctx)
    response = RedirectResponse(url=f"{GRAFANA_PROXY_PREFIX}{redirect_path}")
    response.set_cookie(
        COOKIE_NAME,
        session,
        httponly=True,
        max_age=SESSION_TTL,
        path=GRAFANA_PROXY_PREFIX,
        samesite="lax",
    )
    return response


def _grafana_role(platform_role: str) -> str:
    return "Admin" if platform_role == "admin" else "Viewer"


async def proxy_to_grafana(path: str, request: Request, user_ctx: dict) -> Response:
    upstream_base = resolve_grafana_upstream().rstrip("/") + "/"
    target_url = urljoin(upstream_base, path or "")
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    headers["X-WEBAUTH-USER"] = user_ctx["username"]
    headers["X-WEBAUTH-ROLE"] = _grafana_role(user_ctx["role"])

    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0), follow_redirects=False) as client:
            upstream = await client.request(request.method, target_url, headers=headers, content=body)
    except httpx.RequestError as exc:
        logger.warning("Grafana 代理失败: %s", exc)
        raise HTTPException(status_code=502, detail="无法连接 Grafana，请确认监控栈已启动") from exc

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in {"x-frame-options", "content-security-policy"}
    }
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)
