"""Shared AI provider client with local concurrency protection."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings
from app.utils.log_setup import get_module_logger
from app.utils.retry import retry_async


_ai_semaphore: asyncio.Semaphore | None = None
logger = get_module_logger("ai")


def _get_ai_semaphore() -> asyncio.Semaphore:
    global _ai_semaphore
    limit = max(1, int(settings.AI_MAX_CONCURRENT_REQUESTS or 1))
    if _ai_semaphore is None:
        _ai_semaphore = asyncio.Semaphore(limit)
    return _ai_semaphore


def _responses_url() -> str:
    base_url = (settings.AI_RESPONSES_BASE_URL or settings.AI_BASE_URL or "").rstrip("/")
    if base_url.endswith("/responses"):
        return base_url
    return f"{base_url}/responses"


def should_use_responses_api() -> bool:
    """Use Responses streaming only when it is explicitly configured.

    Qwen/DashScope is configured through the OpenAI-compatible chat-completions
    endpoint in this project. Trying /responses first adds an avoidable provider
    round trip before the real stream starts.
    """
    return bool(settings.AI_RESPONSES_BASE_URL or settings.AI_PREFER_RESPONSES_API)


def _is_qwen_provider() -> bool:
    base_url = (settings.AI_BASE_URL or "").lower()
    model = (settings.AI_MODEL_NAME or "").lower()
    return "dashscope" in base_url or model.startswith("qwen")


def _prepare_chat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    provider_payload = dict(payload)
    if _is_qwen_provider() and "enable_thinking" not in provider_payload:
        provider_payload["enable_thinking"] = bool(settings.AI_ENABLE_THINKING)
    return provider_payload


def _is_retryable_ai_exception(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code if exc.response is not None else 502
        return status_code in (408, 429) or status_code >= 500
    return isinstance(exc, httpx.HTTPError)


def _extract_response_completed_text(response_payload: dict[str, Any]) -> str:
    output = response_payload.get("output") or []
    parts: list[str] = []
    for item in output:
        for content in item.get("content") or []:
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text") or ""
                if text:
                    parts.append(text)
    return "".join(parts)


async def post_chat_completion(
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
    attempts: int | None = None,
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
        async def _call_provider() -> dict[str, Any]:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.AI_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.AI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=_prepare_chat_payload(payload),
                    timeout=timeout if timeout is not None else settings.AI_HTTP_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()

        return await retry_async(
            _call_provider,
            logger=logger,
            event="ai_chat_completion_provider_call",
            attempts=attempts if attempts is not None else settings.AI_RETRY_ATTEMPTS,
            fields={
                "model": payload.get("model") or settings.AI_MODEL_NAME,
                "base_url": settings.AI_BASE_URL,
                "message_count": len(payload.get("messages") or []),
            },
            should_retry=_is_retryable_ai_exception,
        )
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


async def stream_chat_completion(
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
) -> AsyncIterator[str]:
    """Stream chat-completion text deltas behind the same bounded queue."""
    async for event in stream_chat_completion_events(payload, timeout=timeout):
        if event.get("type") == "content":
            yield event.get("content") or ""


async def stream_chat_completion_events(
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
) -> AsyncIterator[dict[str, str]]:
    """Stream chat-completion content and provider reasoning events."""
    if not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置")

    semaphore = _get_ai_semaphore()
    queue_timeout = max(0.1, float(settings.AI_REQUEST_QUEUE_TIMEOUT or 5.0))

    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=queue_timeout)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="AI 请求繁忙，请稍后再试")

    try:
        stream_payload = _prepare_chat_payload(payload)
        stream_payload["stream"] = True
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=stream_payload,
                timeout=timeout if timeout is not None else settings.AI_HTTP_TIMEOUT,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0] or {}
                    delta = choice.get("delta") or {}
                    reasoning_content = delta.get("reasoning_content") or ""
                    if reasoning_content:
                        yield {"type": "reasoning", "content": reasoning_content}
                        continue
                    content = delta.get("content") or ""
                    if content:
                        yield {"type": "content", "content": content}
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


async def stream_responses_completion(
    payload: dict[str, Any],
    *,
    timeout: float | None = None,
) -> AsyncIterator[str]:
    """Stream Responses API text deltas behind the same bounded queue."""
    if not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置")

    semaphore = _get_ai_semaphore()
    queue_timeout = max(0.1, float(settings.AI_REQUEST_QUEUE_TIMEOUT or 5.0))

    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=queue_timeout)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=429, detail="AI 请求繁忙，请稍后再试")

    try:
        stream_payload = dict(payload)
        stream_payload["stream"] = True
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                _responses_url(),
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=stream_payload,
                timeout=timeout if timeout is not None else settings.AI_HTTP_TIMEOUT,
            ) as response:
                response.raise_for_status()
                emitted_delta = False
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    event_type = chunk.get("type") or ""
                    if event_type in {"response.output_text.delta", "response.text.delta"}:
                        delta = chunk.get("delta") or ""
                        if delta:
                            emitted_delta = True
                            yield delta
                        continue

                    if event_type in {"response.output_text.done", "response.text.done"} and not emitted_delta:
                        text = chunk.get("text") or ""
                        if text:
                            emitted_delta = True
                            yield text
                        continue

                    if event_type == "response.completed" and not emitted_delta:
                        text = _extract_response_completed_text(chunk.get("response") or {})
                        if text:
                            emitted_delta = True
                            yield text
    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后再试")
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 429:
            raise HTTPException(status_code=429, detail="AI 服务限流，请稍后再试")
        raise HTTPException(status_code=502, detail="AI Responses 服务暂时不可用")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="AI Responses 服务暂时不可用")
    finally:
        semaphore.release()
