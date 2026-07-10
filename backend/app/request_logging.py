import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
    request_validation_exception_handler as default_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.config import settings

logger = logging.getLogger("app.api")
errors_logger = logging.getLogger("app.errors")
api_errors_logger = logging.getLogger("app.api_errors")

_error_log_handlers_ready = False


def _format_detail(detail: Union[str, dict, list]) -> str:
    if isinstance(detail, str):
        return detail
    return str(detail)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


def _resolve_log_dir() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    configured = (settings.log_dir or "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = (project_root / path).resolve()
        return path
    return (project_root / ".deploy" / "logs").resolve()


def setup_error_log_handlers() -> None:
    global _error_log_handlers_ready
    if _error_log_handlers_ready:
        return

    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

    for target_logger, filename in (
        (errors_logger, "errors.log"),
        (api_errors_logger, "api_errors.log"),
    ):
        target_logger.setLevel(logging.INFO)
        target_logger.propagate = True
        handler = logging.FileHandler(log_dir / filename, encoding="utf-8")
        handler.setFormatter(formatter)
        target_logger.addHandler(handler)

    _error_log_handlers_ready = True


def _write_api_error_record(
    request: Request,
    status_code: int,
    detail: Union[str, dict, list, None] = None,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "client_ip": _client_ip(request),
        "method": request.method,
        "path": request.url.path,
        "status": status_code,
        "detail": _format_detail(detail) if detail is not None else "",
    }
    api_errors_logger.warning(json.dumps(payload, ensure_ascii=False))


def register_request_logging(app: FastAPI) -> None:
    setup_error_log_handlers()

    @app.exception_handler(HTTPException)
    async def log_http_exception(request: Request, exc: HTTPException) -> Response:
        if exc.status_code >= 400:
            message = (
                f"{_client_ip(request)} {request.method} {request.url.path} "
                f"-> HTTP {exc.status_code} | {_format_detail(exc.detail)}"
            )
            if exc.status_code >= 500:
                logger.error(message)
                errors_logger.error(message)
            else:
                logger.warning(message)
            _write_api_error_record(request, exc.status_code, exc.detail)
        return await default_http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def log_validation_exception(request: Request, exc: RequestValidationError) -> Response:
        detail = exc.errors()
        logger.warning(
            "%s %s %s -> HTTP 422 | validation: %s",
            _client_ip(request),
            request.method,
            request.url.path,
            detail,
        )
        _write_api_error_record(request, 422, detail)
        return await default_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def log_unhandled_exception(request: Request, exc: Exception) -> Response:
        message = f"Unhandled {request.method} {request.url.path}: {exc}"
        logger.exception(
            "Unhandled %s %s %s: %s",
            _client_ip(request),
            request.method,
            request.url.path,
            exc,
        )
        errors_logger.exception(message)
        _write_api_error_record(request, 500, "服务器内部错误")
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
