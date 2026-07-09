"""Website visit analytics API."""

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import get_client_ip
from app.schemas.response import ApiResponse
from app.schemas.website_analytics import (
    WebsiteVisitSummaryResponse,
    WebsiteVisitTrackRequest,
    WebsiteVisitTrackResponse,
)
from app.services.website_analytics_service import WebsiteAnalyticsService, WebsiteVisitInput
from app.utils.dependencies import AnyUser, require_internal_admin
from app.utils.log_setup import get_module_logger

router = APIRouter(prefix="/website-analytics", tags=["官网访问统计"])
analytics_service = WebsiteAnalyticsService(debounce_seconds=10)


@router.post("/visit", response_model=ApiResponse[WebsiteVisitTrackResponse])
async def track_website_visit(
    data: WebsiteVisitTrackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Record one public website page view without affecting the page flow."""
    if not _is_allowed_tracking_origin(request):
        return ApiResponse(
            code=200,
            message="已忽略",
            data=WebsiteVisitTrackResponse(counted=False, deduped=False, path=data.path or "/"),
        )

    try:
        result = await analytics_service.track_visit(
            db,
            WebsiteVisitInput(
                path=data.path,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                referrer=data.referrer,
            ),
        )
        return ApiResponse(
            code=200,
            message="记录成功",
            data=WebsiteVisitTrackResponse(counted=result.counted, deduped=result.deduped, path=result.path),
        )
    except Exception as exc:
        get_module_logger("system").warning(f"官网访问统计写入失败: {exc}")
        return ApiResponse(
            code=200,
            message="统计失败但不影响访问",
            data=WebsiteVisitTrackResponse(counted=False, deduped=False, path=data.path or "/"),
        )


@router.get("/admin/website-visits", response_model=ApiResponse[WebsiteVisitSummaryResponse])
async def get_website_visit_summary(
    days: int = Query(7, ge=1, le=90),
    current_user: AnyUser = Depends(require_internal_admin),
    db: AsyncSession = Depends(get_db),
):
    """Read website PV/UV aggregates for the admin business dashboard."""
    _ = current_user
    summary = await analytics_service.get_summary(db, days=days)
    return ApiResponse(code=200, message="获取成功", data=summary.to_dict())


def _is_allowed_tracking_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    source = origin or referer
    if not source:
        return True

    source_host = urlsplit(source).netloc.lower()
    if not source_host:
        return True

    allowed_hosts = {request.headers.get("host", "").lower()}
    cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else []
    if "*" in cors_origins:
        return True

    for configured_origin in cors_origins:
        configured_host = urlsplit(configured_origin).netloc.lower()
        if configured_host:
            allowed_hosts.add(configured_host)

    return source_host in allowed_hosts
