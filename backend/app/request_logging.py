import logging
from typing import Union

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
    request_validation_exception_handler as default_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

logger = logging.getLogger("app.api")


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


def register_request_logging(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def log_http_exception(request: Request, exc: HTTPException) -> Response:
        if exc.status_code >= 400:
            message = (
                f"{_client_ip(request)} {request.method} {request.url.path} "
                f"-> HTTP {exc.status_code} | {_format_detail(exc.detail)}"
            )
            if exc.status_code >= 500:
                logger.error(message)
            else:
                logger.warning(message)
        return await default_http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def log_validation_exception(request: Request, exc: RequestValidationError) -> Response:
        logger.warning(
            "%s %s %s -> HTTP 422 | validation: %s",
            _client_ip(request),
            request.method,
            request.url.path,
            exc.errors(),
        )
        return await default_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def log_unhandled_exception(request: Request, exc: Exception) -> Response:
        logger.exception(
            "Unhandled %s %s %s: %s",
            _client_ip(request),
            request.method,
            request.url.path,
            exc,
        )
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
