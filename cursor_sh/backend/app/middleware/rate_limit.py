"""API 限流中间件"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from app.config import settings


def get_client_ip(request: Request) -> str:
    """Use proxy headers from the Docker Nginx frontend when present."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# 创建限流器
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"] if settings.RATE_LIMIT_ENABLED else []
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """限流异常处理"""
    raise HTTPException(
        status_code=429,
        detail="请求过于频繁，请稍后再试"
    )
