from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.auth import get_current_admin
from app.models.user import User
from app.services import log_service

router = APIRouter(prefix="/logs", tags=["日志监控"])


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
