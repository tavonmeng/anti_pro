"""API 限流中间件"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from app.config import settings


# 创建限流器
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"] if settings.RATE_LIMIT_ENABLED else []
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """限流异常处理"""
    raise HTTPException(
        status_code=429,
        detail="请求过于频繁，请稍后再试"
    )

