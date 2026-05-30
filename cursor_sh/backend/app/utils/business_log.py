"""Small helpers for business event logs.

The request audit middleware records that an endpoint was called. These helpers
record what business event happened, with stable ids that let us stitch a flow
together across modules.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from app.config import settings
from app.utils.request_context import get_request_context


_SENSITIVE_KEYWORDS = ("password", "token", "code", "secret")


def _mask_phone(value: Any) -> str:
    text = str(value or "")
    if len(text) < 7:
        return "***"
    return f"{text[:3]}****{text[-4:]}"


def _mask_email(value: Any) -> str:
    text = str(value or "")
    if "@" not in text:
        return "***"
    name, domain = text.split("@", 1)
    prefix = name[:2] if len(name) > 2 else name[:1]
    return f"{prefix}***@{domain}"


def _safe_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(key, item) for item in value]
    if isinstance(value, dict):
        return {
            str(k): _safe_value(str(k), v)
            for k, v in value.items()
            if v is not None
        }
    if "phone" in key_lower:
        return _mask_phone(value)
    if "email" in key_lower:
        return _mask_email(value)
    if any(word in key_lower for word in _SENSITIVE_KEYWORDS):
        return "******"
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str) and len(value) > 180:
        return value[:180] + "...[TRUNCATED]"
    return value


def _format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def log_business_event(logger, event: str, level: str = "info", **fields: Any) -> None:
    """Write a compact, grep-friendly business event log line."""
    if not settings.LOG_ENABLED:
        return

    try:
        context = get_request_context()
        trace_id = context.get("trace_id") or fields.get("trace_id") or "-"
        context_fields = {
            "actor_id": context.get("actor_id"),
            "actor_username": context.get("actor_username"),
            "method": context.get("method"),
            "path": context.get("path"),
            "ip": context.get("ip"),
        }
        for key, value in context_fields.items():
            fields.setdefault(key, value)

        safe_fields = {
            key: _safe_value(key, value)
            for key, value in fields.items()
            if value is not None
        }
        parts = [f"event={event}"]
        parts.extend(f"{key}={_format_value(value)}" for key, value in safe_fields.items())
        logger.bind(trace_id=trace_id).log(level.upper(), " ".join(parts))
    except Exception:
        # Logging must never block the business path.
        pass
