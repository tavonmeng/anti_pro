"""Shared context window preparation for AI agents."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Any

from app.config import settings
from app.services.ai_client import post_chat_completion
from app.utils.log_setup import get_module_logger

logger = get_module_logger("ai")

AGENT_CONTEXT_MAX_MESSAGES = 8
AGENT_CONTEXT_MAX_MESSAGE_CHARS = 700
AGENT_CONTEXT_SUMMARY_CHARS = 620
AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES = 2
AGENT_CONTEXT_WINDOW_VERSION = 2


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _message_fingerprint(role: str, content: str) -> str:
    digest = hashlib.sha1(f"{role}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"fp:{digest}"


def empty_agent_context_window() -> dict[str, Any]:
    return {
        "version": AGENT_CONTEXT_WINDOW_VERSION,
        "max_messages": AGENT_CONTEXT_MAX_MESSAGES,
        "max_chars_per_message": AGENT_CONTEXT_MAX_MESSAGE_CHARS,
        "preserve_latest_messages": AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES,
        "messages": [],
    }


def ensure_agent_context_window(state: dict[str, Any] | None) -> dict[str, Any]:
    next_state = deepcopy(state or {})
    window = next_state.get("agent_context_window")
    if not isinstance(window, dict):
        next_state["agent_context_window"] = empty_agent_context_window()
        return next_state

    messages = window.get("messages")
    if not isinstance(messages, list):
        window["messages"] = []
    window.setdefault("version", 1)
    window.setdefault("max_messages", AGENT_CONTEXT_MAX_MESSAGES)
    window.setdefault("max_chars_per_message", AGENT_CONTEXT_MAX_MESSAGE_CHARS)
    window.setdefault("preserve_latest_messages", AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES)
    return next_state


def _limit_context_text(text: str, max_chars: int = AGENT_CONTEXT_MAX_MESSAGE_CHARS) -> str:
    text = _clean_text(text)
    if len(text) <= max_chars:
        return text
    marker = "\n……（中间内容已压缩）……\n"
    available_chars = max(0, max_chars - len(marker))
    head_size = available_chars // 2
    tail_size = available_chars - head_size
    return (
        f"{text[:head_size].rstrip()}\n"
        "……（中间内容已压缩）……\n"
        f"{text[-tail_size:].lstrip()}"
    )


async def _summarize_long_context_message(role: str, content: str) -> str:
    if not settings.AI_API_KEY:
        return _limit_context_text(content)

    system_prompt = (
        "你是 Unique Vision AI 的 agent 上下文压缩器。"
        "只压缩当前这一条消息，不总结整段对话，不补充原文没有的信息。\n\n"
        "保留对后续 router、Brief、创意方向和创意评估有用的信息："
        "创意主体/主题、关键画面或动作机制、屏幕/现场/媒介关系、图片理解摘要线索、"
        "用户确认/否定/修改的方向、上一版创意方向名称和核心设定。\n"
        "输出简体中文纯文本，不要 Markdown，不要 JSON，不超过 620 字。"
    )
    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"角色：{role}\n原始消息：\n{content}"},
                ],
                "max_tokens": 700,
                "temperature": 0,
            },
            timeout=min(float(settings.AI_HTTP_TIMEOUT or 30.0), 20.0),
            attempts=1,
        )
        summary = data["choices"][0]["message"]["content"]
        return _limit_context_text(summary, AGENT_CONTEXT_MAX_MESSAGE_CHARS)
    except Exception as exc:
        logger.warning("ai_context_message_compaction_failed", extra={"error": str(exc)})
        return _limit_context_text(content)


def _find_existing_window_message(
    messages: list[dict[str, Any]],
    *,
    source_message_id: str | None,
    fingerprint: str,
) -> dict[str, Any] | None:
    if source_message_id:
        for item in messages:
            if item.get("source_message_id") == source_message_id:
                return item
        return None
    for item in messages:
        if item.get("fingerprint") == fingerprint:
            return item
    return None


async def append_agent_context_message(
    state: dict[str, Any] | None,
    *,
    role: str,
    content: str,
    source_message_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    next_state = ensure_agent_context_window(state)
    role = role if role in {"user", "assistant"} else ""
    raw_content = str(content or "").strip()
    if not role or not raw_content:
        return next_state, raw_content

    window = next_state["agent_context_window"]
    messages = window.setdefault("messages", [])
    fingerprint = _message_fingerprint(role, raw_content)
    existing = (
        _find_existing_window_message(
            messages,
            source_message_id=source_message_id,
            fingerprint=fingerprint,
        )
        if source_message_id
        else None
    )
    if existing:
        return next_state, str(existing.get("content") or "")

    messages.append(
        {
            "role": role,
            "content": raw_content,
            "source_message_id": source_message_id,
            "fingerprint": fingerprint,
            "compacted": False,
            "original_chars": len(raw_content),
        }
    )
    del messages[:-AGENT_CONTEXT_MAX_MESSAGES]

    compact_before = max(0, len(messages) - AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES)
    for item in messages[:compact_before]:
        if item.get("compacted"):
            continue
        original_chars = int(item.get("original_chars") or len(str(item.get("content") or "")))
        if original_chars <= AGENT_CONTEXT_MAX_MESSAGE_CHARS:
            continue
        item["content"] = await _summarize_long_context_message(
            str(item.get("role") or ""),
            str(item.get("content") or ""),
        )
        item["compacted"] = True

    window["version"] = AGENT_CONTEXT_WINDOW_VERSION
    window["preserve_latest_messages"] = AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES
    return next_state, raw_content


async def sync_agent_context_window_from_history(
    state: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Rebuild the bounded context window from the authoritative request history.

    A context window is an ordered suffix, not a deduplicated set. Repeated
    replies such as two separate ``user: 没有`` messages must remain separate
    because they can answer different assistant questions.
    """
    next_state = ensure_agent_context_window(state)
    recent = [
        item
        for item in (history or [])
        if item.get("role") in {"user", "assistant"} and str(item.get("content") or "").strip()
    ][-AGENT_CONTEXT_MAX_MESSAGES:]
    if not recent:
        return next_state

    existing_messages = list((next_state.get("agent_context_window") or {}).get("messages") or [])
    rebuilt_messages: list[dict[str, Any]] = []
    preserve_from = max(0, len(recent) - AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES)
    for index, item in enumerate(recent):
        role = str(item.get("role") or "")
        raw_content = str(item.get("content") or "").strip()
        source_message_id = str(item.get("client_message_id") or item.get("id") or "") or None
        fingerprint = _message_fingerprint(role, raw_content)
        preserve_full = index >= preserve_from
        compacted = not preserve_full and len(raw_content) > AGENT_CONTEXT_MAX_MESSAGE_CHARS
        existing = _find_existing_window_message(
            existing_messages,
            source_message_id=source_message_id,
            fingerprint=fingerprint,
        )
        can_reuse = bool(
            existing
            and existing.get("fingerprint") == fingerprint
            and bool(existing.get("compacted")) == compacted
        )
        context_content = (
            raw_content
            if preserve_full
            else (
                str(existing.get("content") or "")
                if can_reuse
                else (
                    await _summarize_long_context_message(role, raw_content)
                    if compacted
                    else _limit_context_text(raw_content)
                )
            )
        )
        rebuilt_messages.append(
            {
                "role": role,
                "content": context_content,
                "source_message_id": source_message_id,
                "fingerprint": fingerprint,
                "compacted": compacted,
                "original_chars": len(raw_content),
            }
        )

    window = next_state["agent_context_window"]
    window["version"] = AGENT_CONTEXT_WINDOW_VERSION
    window["preserve_latest_messages"] = AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES
    window["messages"] = rebuilt_messages
    return next_state


def agent_context_messages(
    state: dict[str, Any] | None,
    *,
    exclude_source_message_id: str | None = None,
    fallback_history: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    state = ensure_agent_context_window(state)
    messages = []
    for item in (state.get("agent_context_window") or {}).get("messages") or []:
        if exclude_source_message_id and item.get("source_message_id") == exclude_source_message_id:
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    if messages:
        return messages[-AGENT_CONTEXT_MAX_MESSAGES:]

    fallback_messages = [
        {
            "role": item["role"],
            "content": str(item.get("content") or "").strip(),
        }
        for item in (fallback_history or [])
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ][-AGENT_CONTEXT_MAX_MESSAGES:]
    preserve_from = max(0, len(fallback_messages) - AGENT_CONTEXT_PRESERVE_LATEST_MESSAGES)
    return [
        {
            "role": item["role"],
            "content": (
                item["content"]
                if index >= preserve_from
                else _limit_context_text(item["content"])
            ),
        }
        for index, item in enumerate(fallback_messages)
    ]


def latest_user_context_message(
    state: dict[str, Any] | None,
    fallback_message: str,
    *,
    source_message_id: str | None = None,
) -> str:
    state = ensure_agent_context_window(state)
    messages = (state.get("agent_context_window") or {}).get("messages") or []
    for item in reversed(messages):
        if item.get("role") != "user":
            continue
        if source_message_id and item.get("source_message_id") != source_message_id:
            continue
        content = str(item.get("content") or "").strip()
        if content:
            return content
    return str(fallback_message or "").strip()
