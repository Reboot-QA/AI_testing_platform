import gzip
import hashlib
import hmac
import logging
import re
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException, Request, Response

from app.config import settings
from app.services.log_integration_service import resolve_grafana_upstream

logger = logging.getLogger(__name__)

GRAFANA_PROXY_PREFIX = "/api/v1/logs/grafana"
COOKIE_NAME = "grafana_proxy_sess"
EMBED_QUERY_PARAM = "_pt"
SESSION_TTL = 8 * 3600
GRAFANA_UPSTREAM_SESSION_TTL = 50 * 60

_grafana_upstream_cookies: Optional[httpx.Cookies] = None
_grafana_upstream_expires: float = 0

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
    "cookie",
}

REWRITABLE_CONTENT_TYPES = {
    "text/html",
    "application/javascript",
    "text/javascript",
    "text/css",
    "application/json",
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


def create_session_cookie(user_ctx: dict) -> str:
    payload = f"{user_ctx['user_id']}:{user_ctx['username']}:{user_ctx['role']}:{int(time.time()) + SESSION_TTL}"
    return _sign_payload(payload)


def create_embed_token(user_id: int, username: str, role: str) -> str:
    return create_session_cookie({"user_id": user_id, "username": username, "role": role})


def resolve_user_from_cookie(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        token = request.query_params.get(EMBED_QUERY_PARAM)
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


def build_public_proxy_base(request: Request) -> str:
    return f"{build_public_origin(request)}{GRAFANA_PROXY_PREFIX}"


def attach_grafana_session(response: Response, user_ctx: dict) -> str:
    session = create_session_cookie(user_ctx)
    response.set_cookie(
        COOKIE_NAME,
        session,
        httponly=True,
        max_age=SESSION_TTL,
        path=GRAFANA_PROXY_PREFIX,
        samesite="lax",
    )
    return session


def _admin_credentials() -> Tuple[str, str]:
    user = (settings.grafana_admin_user or "admin").strip()
    password = settings.grafana_admin_password or ""
    return user, password


async def _clear_upstream_session() -> None:
    global _grafana_upstream_cookies, _grafana_upstream_expires
    _grafana_upstream_cookies = None
    _grafana_upstream_expires = 0


async def _ensure_upstream_session(client: httpx.AsyncClient, force: bool = False) -> httpx.Cookies:
    global _grafana_upstream_cookies, _grafana_upstream_expires
    now = time.time()
    if not force and _grafana_upstream_cookies and now < _grafana_upstream_expires:
        return _grafana_upstream_cookies

    user, password = _admin_credentials()
    if not password:
        raise HTTPException(status_code=502, detail="未配置 GRAFANA_ADMIN_PASSWORD，无法代理 Grafana")

    base = resolve_grafana_upstream().rstrip("/")
    login_resp = await client.post(f"{base}/login", json={"user": user, "password": password})
    if login_resp.status_code != 200:
        await _clear_upstream_session()
        raise HTTPException(
            status_code=502,
            detail="Grafana 管理员密码不正确，请在服务器执行: docker exec ai-platform-grafana grafana-cli admin reset-admin-password '新密码' 并同步 .env.docker",
        )

    user_resp = await client.get(f"{base}/api/user", cookies=login_resp.cookies)
    if user_resp.status_code != 200:
        await _clear_upstream_session()
        raise HTTPException(status_code=502, detail="Grafana 登录失败，请检查监控栈配置")

    _grafana_upstream_cookies = login_resp.cookies
    _grafana_upstream_expires = now + GRAFANA_UPSTREAM_SESSION_TTL
    return _grafana_upstream_cookies


def _decompress_body(content: bytes, content_encoding: str) -> Tuple[bytes, bool]:
    encoding = (content_encoding or "").lower()
    if "gzip" in encoding:
        return gzip.decompress(content), True
    return content, False


def _is_login_page(content: bytes, content_type: str, path: str) -> bool:
    lower_path = (path or "").lower().strip("/")
    if lower_path in {"login", "login/"}:
        return True
    if "text/html" not in (content_type or "").lower():
        return False
    try:
        text = content.decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        return False
    return "Welcome to Grafana" in text and ('name="password"' in text or 'type="password"' in text)


def _rewrite_grafana_body(content: bytes, content_type: str, public_proxy_base: str) -> bytes:
    lower_type = (content_type or "").lower().split(";", 1)[0].strip()
    if lower_type not in REWRITABLE_CONTENT_TYPES:
        return content
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content

    base_path = f"{GRAFANA_PROXY_PREFIX}/"
    text = re.sub(
        r'(<base\s+href=")([^"]*)(")',
        rf"\1{base_path}\3",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(<base\s+href=')([^']*)(')",
        rf"\1{base_path}\3",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf'https?://[^"\'\s<>]+{re.escape(GRAFANA_PROXY_PREFIX)}',
        public_proxy_base,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r'"appSubUrl"\s*:\s*"[^"]*"',
        f'"appSubUrl":"{GRAFANA_PROXY_PREFIX}"',
        text,
    )
    text = re.sub(
        r'"appUrl"\s*:\s*"[^"]*"',
        f'"appUrl":"{public_proxy_base}/"',
        text,
    )
    text = re.sub(
        r'"disableLoginForm"\s*:\s*false',
        '"disableLoginForm":true',
        text,
    )
    return text.encode("utf-8")


def _rewrite_grafana_location(value: str) -> str:
    upstream_base = resolve_grafana_upstream().rstrip("/")
    if value.startswith(upstream_base):
        suffix = value[len(upstream_base) :] or "/"
        return f"{GRAFANA_PROXY_PREFIX}{suffix}"
    if value.startswith("/"):
        return f"{GRAFANA_PROXY_PREFIX}{value}"
    return value


async def proxy_to_grafana(path: str, request: Request, user_ctx: dict) -> Response:
    del user_ctx  # 平台侧鉴权已在路由层完成；上游统一使用 Grafana 服务账号
    upstream_base = resolve_grafana_upstream().rstrip("/") + "/"
    target_url = urljoin(upstream_base, path or "")
    if request.url.query:
        query = str(request.url.query)
        if EMBED_QUERY_PARAM in request.query_params:
            parts = [part for part in query.split("&") if not part.startswith(f"{EMBED_QUERY_PARAM}=")]
            query = "&".join(parts)
        if query:
            target_url = f"{target_url}?{query}"

    public_origin = build_public_origin(request)
    public_proxy_base = f"{public_origin}{GRAFANA_PROXY_PREFIX}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    headers["X-Forwarded-Host"] = (
        request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    ).split(",")[0].strip()
    headers["X-Forwarded-Proto"] = request.headers.get("x-forwarded-proto", request.url.scheme)
    headers["X-Forwarded-Prefix"] = GRAFANA_PROXY_PREFIX

    body = await request.body()

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0), follow_redirects=False) as client:
        upstream_cookies = await _ensure_upstream_session(client)
        upstream = await client.request(
            request.method,
            target_url,
            headers=headers,
            content=body,
            cookies=upstream_cookies,
        )

        if upstream.status_code in {401, 403} or _is_login_page(upstream.content, upstream.headers.get("content-type", ""), path):
            await _clear_upstream_session()
            upstream_cookies = await _ensure_upstream_session(client, force=True)
            upstream = await client.request(
                request.method,
                target_url,
                headers=headers,
                content=body,
                cookies=upstream_cookies,
            )

    if _is_login_page(upstream.content, upstream.headers.get("content-type", ""), path):
        raise HTTPException(
            status_code=502,
            detail="Grafana 认证失败：请确认 .env.docker 中 GRAFANA_ADMIN_PASSWORD 与 Grafana 实际密码一致",
        )

    if upstream.status_code in {301, 302, 303, 307, 308}:
        location = upstream.headers.get("location", "")
        if "/login" in location:
            raise HTTPException(
                status_code=502,
                detail="Grafana 会话失效，请检查 GRAFANA_ADMIN_USER / GRAFANA_ADMIN_PASSWORD 配置",
            )

    response_body = upstream.content
    content_type = upstream.headers.get("content-type", "")
    content_encoding = upstream.headers.get("content-encoding", "")
    if response_body and request.method.upper() == "GET":
        decoded_body, was_gzip = _decompress_body(response_body, content_encoding)
        rewritten = _rewrite_grafana_body(decoded_body, content_type, public_proxy_base)
        if rewritten != decoded_body:
            response_body = rewritten
            content_encoding = ""
        elif was_gzip:
            response_body = decoded_body
            content_encoding = ""

    response_headers = {}
    for key, value in upstream.headers.items():
        lower = key.lower()
        if lower in HOP_BY_HOP_HEADERS:
            continue
        if lower in {"x-frame-options", "content-security-policy", "set-cookie"}:
            continue
        if lower in {"content-encoding", "content-length"} and (
            content_encoding != upstream.headers.get("content-encoding", "")
            or response_body is not upstream.content
        ):
            continue
        if lower == "location":
            value = _rewrite_grafana_location(value)
        response_headers[key] = value
    return Response(content=response_body, status_code=upstream.status_code, headers=response_headers)
