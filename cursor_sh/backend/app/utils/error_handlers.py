"""FastAPI exception handlers that preserve user-safe responses and log internals."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger


logger = get_module_logger("system")


def _cause_fields(exc: BaseException) -> dict:
    cause = exc.__cause__ or exc.__context__
    if not cause:
        return {}
    return {
        "cause_type": type(cause).__name__,
        "cause": str(cause),
    }


async def _http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        log_business_event(
            logger,
            "http_exception_5xx",
            level="error",
            status_code=exc.status_code,
            detail=exc.detail,
            **_cause_fields(exc),
        )
    elif exc.status_code >= 400:
        log_business_event(
            logger,
            "http_exception_4xx",
            level="warning",
            status_code=exc.status_code,
            detail=exc.detail,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    locations = [
        ".".join(str(part) for part in error.get("loc", []))
        for error in exc.errors()
    ]
    log_business_event(
        logger,
        "request_validation_failed",
        level="warning",
        status_code=422,
        error_count=len(exc.errors()),
        locations=locations,
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


async def _unhandled_exception_handler(request: Request, exc: Exception):
    log_business_event(
        logger,
        "unhandled_exception",
        level="error",
        error_type=type(exc).__name__,
        error=str(exc),
    )
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
