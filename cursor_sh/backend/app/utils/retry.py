"""Retry helpers for outbound integrations."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from app.config import settings
from app.utils.business_log import log_business_event


T = TypeVar("T")


class RetryableExternalError(RuntimeError):
    """Raised when a provider response is safe to retry."""


def _attempt_count(value: int | None) -> int:
    return max(1, int(value if value is not None else settings.EXTERNAL_API_RETRY_ATTEMPTS))


def _delay(attempt_index: int) -> float:
    base = max(0.0, float(settings.EXTERNAL_API_RETRY_INITIAL_DELAY))
    cap = max(base, float(settings.EXTERNAL_API_RETRY_MAX_DELAY))
    raw = min(cap, base * (2 ** max(0, attempt_index - 1)))
    jitter = random.uniform(0, raw * 0.2) if raw > 0 else 0
    return raw + jitter


def _should_retry_default(exc: BaseException) -> bool:
    return not isinstance(exc, (KeyboardInterrupt, SystemExit))


def retry_sync(
    operation: Callable[[], T],
    *,
    logger,
    event: str,
    attempts: int | None = None,
    fields: dict[str, Any] | None = None,
    should_retry: Callable[[BaseException], bool] | None = None,
) -> T:
    max_attempts = _attempt_count(attempts)
    retry_predicate = should_retry or _should_retry_default
    fields = fields or {}

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt >= max_attempts or not retry_predicate(exc):
                log_business_event(
                    logger,
                    f"{event}_failed",
                    level="error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    **fields,
                )
                raise

            delay_seconds = _delay(attempt)
            log_business_event(
                logger,
                f"{event}_retrying",
                level="warning",
                attempt=attempt,
                max_attempts=max_attempts,
                delay_seconds=round(delay_seconds, 3),
                error_type=type(exc).__name__,
                error=str(exc),
                **fields,
            )
            time.sleep(delay_seconds)

    raise RuntimeError("unreachable retry state")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    logger,
    event: str,
    attempts: int | None = None,
    fields: dict[str, Any] | None = None,
    should_retry: Callable[[BaseException], bool] | None = None,
) -> T:
    max_attempts = _attempt_count(attempts)
    retry_predicate = should_retry or _should_retry_default
    fields = fields or {}

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_attempts or not retry_predicate(exc):
                log_business_event(
                    logger,
                    f"{event}_failed",
                    level="error",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_type=type(exc).__name__,
                    error=str(exc),
                    **fields,
                )
                raise

            delay_seconds = _delay(attempt)
            log_business_event(
                logger,
                f"{event}_retrying",
                level="warning",
                attempt=attempt,
                max_attempts=max_attempts,
                delay_seconds=round(delay_seconds, 3),
                error_type=type(exc).__name__,
                error=str(exc),
                **fields,
            )
            await asyncio.sleep(delay_seconds)

    raise RuntimeError("unreachable retry state")
