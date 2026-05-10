"""Shared AI provider client with local concurrency protection."""

import asyncio
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings


_ai_semaphore: asyncio.Semaphore | None = None


def _get_ai_semaphore() -> asyncio.Semaphore:
    global _ai_semaphore
    limit = max(1, int(settings.AI_MAX_CONCURRENT_REQUESTS or 1))
    if _ai_semaphore is None:
        _ai_semaphore = asyncio.Semaphore(limit)
    return _ai_semaphore


async def post_chat_completion(
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Call the configured chat-completions API behind a bounded queue.

    This protects the app process from a burst of expensive LLM calls. In Docker
    with multiple workers the limit is per worker; use Redis/API-gateway rate
    limiting for a hard cluster-wide quota.
    """
    if not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置")

    semaphore = _get_ai_semaphore()
    queue_timeout = max(0.1, float(settings.AI_REQUEST_QUEUE_TIMEOUT or 5.0))

    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=queue_timeout)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="AI 请求繁忙，请稍后再试")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout if timeout is not None else settings.AI_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后再试")
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 429:
            raise HTTPException(status_code=429, detail="AI 服务限流，请稍后再试")
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用")
    finally:
        semaphore.release()

