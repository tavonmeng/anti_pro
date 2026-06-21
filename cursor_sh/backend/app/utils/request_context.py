"""Per-request logging context.

The audit middleware owns request-level fields such as trace id and actor. This
module makes those fields available to service-layer business logs without
passing them through every function signature.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any


_request_context: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})


def set_request_context(**fields: Any) -> Token:
    clean_fields = {key: value for key, value in fields.items() if value is not None}
    return _request_context.set(clean_fields)


def reset_request_context(token: Token) -> None:
    _request_context.reset(token)


def get_request_context() -> dict[str, Any]:
    return dict(_request_context.get() or {})
