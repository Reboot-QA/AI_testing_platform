from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.auth import get_current_admin
from app.models.user import User
from app.schemas import GrafanaLaunchIn
from app.services import log_service
from app.services.grafana_proxy_service import (
    attach_grafana_session,
    build_enter_response,
    build_launch_url,
    build_public_origin,
    proxy_to_grafana,
    resolve_user_from_cookie,
)
from app.services.log_integration_service import get_integration_status

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
    response = JSONResponse({"ok": True})
    attach_grafana_session(
        response,
        {"user_id": current_user.id, "username": current_user.username, "role": current_user.role},
    )
    return response


@router.post("/grafana/launch")
def grafana_launch(
    body: GrafanaLaunchIn,
    request: Request,
    public_origin: Optional[str] = Query(None, max_length=300),
    current_user: User = Depends(get_current_admin),
):
    origin = build_public_origin(request, (public_origin or "").strip() or None)
    url = build_launch_url(origin, current_user.id, current_user.username, current_user.role, body.redirect)
    return {"url": url}


@router.get("/grafana/enter")
def grafana_enter(token: str = Query(..., min_length=8), redirect: str = Query("/")):
    return build_enter_response(token, redirect)


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
