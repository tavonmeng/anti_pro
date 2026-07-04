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


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _message_fingerprint(role: str, content: str) -> str:
    digest = hashlib.sha1(f"{role}:{content}".encode("utf-8")).hexdigest()[:16]
    return f"fp:{digest}"


def empty_agent_context_window() -> dict[str, Any]:
    return {
        "version": 1,
        "max_messages": AGENT_CONTEXT_MAX_MESSAGES,
        "max_chars_per_message": AGENT_CONTEXT_MAX_MESSAGE_CHARS,
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
    return next_state


def _limit_context_text(text: str, max_chars: int = AGENT_CONTEXT_MAX_MESSAGE_CHARS) -> str:
    text = _clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip(" ，,；;。") + "..."


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
    existing = _find_existing_window_message(
        messages,
        source_message_id=source_message_id,
        fingerprint=fingerprint,
    )
    if existing:
        return next_state, str(existing.get("content") or "")

    compacted = len(raw_content) > AGENT_CONTEXT_MAX_MESSAGE_CHARS
    context_content = (
        await _summarize_long_context_message(role, raw_content)
        if compacted
        else _limit_context_text(raw_content)
    )
    messages.append(
        {
            "role": role,
            "content": context_content,
            "source_message_id": source_message_id,
            "fingerprint": fingerprint,
            "compacted": compacted,
            "original_chars": len(raw_content),
        }
    )
    del messages[:-AGENT_CONTEXT_MAX_MESSAGES]
    return next_state, context_content


async def sync_agent_context_window_from_history(
    state: dict[str, Any] | None,
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    next_state = ensure_agent_context_window(state)
    recent = [
        item
        for item in (history or [])[-AGENT_CONTEXT_MAX_MESSAGES:]
        if item.get("role") in {"user", "assistant"} and str(item.get("content") or "").strip()
    ]
    for item in recent:
        next_state, _ = await append_agent_context_message(
            next_state,
            role=str(item.get("role") or ""),
            content=str(item.get("content") or ""),
            source_message_id=str(item.get("client_message_id") or item.get("id") or "") or None,
        )
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

    return [
        {"role": item["role"], "content": _limit_context_text(str(item.get("content") or ""))}
        for item in (fallback_history or [])[-AGENT_CONTEXT_MAX_MESSAGES:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
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
    return _limit_context_text(fallback_message)
