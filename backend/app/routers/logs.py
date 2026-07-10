from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.auth import get_current_admin
from app.models.user import User
from app.services import log_service
from app.services.grafana_proxy_service import (
    COOKIE_NAME,
    GRAFANA_PROXY_PREFIX,
    SESSION_TTL,
    build_public_origin,
    create_session_cookie,
    proxy_to_grafana,
    resolve_user_from_cookie,
)
from app.services.log_integration_service import get_integration_status
from app.services.loki_query_service import query_loki

router = APIRouter(prefix="/logs", tags=["日志监控"])


@router.get("/integrations")
def log_integrations(
    request: Request,
    public_host: Optional[str] = Query(None, max_length=200),
    public_origin: Optional[str] = Query(None, max_length=300),
    _: User = Depends(get_current_admin),
):
    host = (public_host or "").strip()
    if not host:
        forwarded = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
        raw_host = forwarded or (request.headers.get("host") or "")
        host = raw_host.split(":")[0].strip()
    origin = build_public_origin(request, (public_origin or "").strip() or None)
    return get_integration_status(public_host=host or None, public_origin=origin)


@router.post("/grafana/session")
def grafana_session(current_user: User = Depends(get_current_admin)):
    user_ctx = {"user_id": current_user.id, "username": current_user.username, "role": current_user.role}
    embed_token = create_session_cookie(user_ctx)
    response = JSONResponse(
        {
            "ok": True,
            "embed_token": embed_token,
            "proxy_prefix": GRAFANA_PROXY_PREFIX,
        }
    )
    response.set_cookie(
        COOKIE_NAME,
        embed_token,
        httponly=True,
        max_age=SESSION_TTL,
        path=GRAFANA_PROXY_PREFIX,
        samesite="lax",
    )
    return response


@router.api_route("/grafana", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@router.api_route("/grafana/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def grafana_proxy(request: Request, path: str = ""):
    user_ctx = resolve_user_from_cookie(request)
    if not user_ctx:
        raise HTTPException(
            status_code=401,
            detail="请从平台「日志监控」页面打开 Grafana",
            headers={"X-Grafana-Proxy": "auth-required"},
        )
    return await proxy_to_grafana(path, request, user_ctx)


@router.get("/loki/query")
async def loki_query(
    query: Optional[str] = Query(None, max_length=500),
    limit: int = Query(200, ge=1, le=1000),
    hours: int = Query(6, ge=1, le=168),
    _: User = Depends(get_current_admin),
):
    return await query_loki(expr=query, limit=limit, hours=hours)


@router.get("/sources")
def list_log_sources(_: User = Depends(get_current_admin)):
    return {
        "log_dir": str(log_service.get_log_dir()),
        "sources": log_service.list_sources(),
    }


@router.get("/tail")
def tail_logs(
    source: str = Query(..., description="backend | frontend | ensure"),
    lines: int = Query(200, ge=1, le=2000),
    keyword: Optional[str] = Query(None, max_length=200),
    level: Optional[str] = Query(None, pattern="^(ERROR|WARN|INFO|DEBUG)$"),
    offset: int = Query(0, ge=0),
    _: User = Depends(get_current_admin),
):
    try:
        return log_service.tail_log(source, lines=lines, keyword=keyword, level=level, offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/stream")
def stream_logs(
    source: str = Query(..., description="backend | frontend | ensure"),
    _: User = Depends(get_current_admin),
):
    try:
        log_service._resolve_source_path(source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    def event_generator():
        yield from log_service.stream_log_events(source)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/download")
def download_log(
    source: str = Query(..., description="backend | frontend | ensure"),
    _: User = Depends(get_current_admin),
):
    try:
        path, filename = log_service.get_download_path(source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not path.exists():
        raise HTTPException(status_code=404, detail="日志文件不存在")

    return FileResponse(
        path,
        media_type="text/plain; charset=utf-8",
        filename=filename,
    )
