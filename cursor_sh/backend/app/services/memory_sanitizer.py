"""Sanitizers for customer-document data before it reaches Agent Memory."""

from __future__ import annotations

import copy
import re
from typing import Any


PRICE_FIELD_KEYS = {
    "list_price",
    "price",
    "prices",
    "quote",
    "quotation",
    "fee",
    "fees",
    "cost",
    "costs",
    "budget",
    "budget_range",
    "production_fee",
    "制作费",
    "刊例价",
    "报价",
    "价格",
    "费用",
    "成本",
}

PRICE_KEYWORDS = (
    "刊例价",
    "报价",
    "价格",
    "价目",
    "制作费",
    "费用",
    "成本",
    "媒介费",
    "媒体费",
    "发布费",
    "服务费",
    "代理费",
    "含税",
    "未税",
    "人民币",
    "rmb",
    "cny",
)

AMOUNT_ONLY_PRICE_KEYWORDS = (
    "预算",
    "budget",
)

PROJECT_SCHEDULE_FIELD_KEYS = {
    "online_time",
    "launch_time",
    "go_live_time",
    "publish_time",
    "publication_time",
    "delivery_time",
    "release_time",
    "上刊时间",
    "上线时间",
    "投放时间",
    "交付时间",
}

PROJECT_SCHEDULE_KEYWORDS = (
    "上刊",
    "上线",
    "投放时间",
    "活动时间",
    "交付时间",
    "发布时间",
    "发布节点",
    "上线节点",
    "上刊节点",
    "下月",
    "下个月",
    "本月",
    "月底",
    "月初",
)

_MONEY_AMOUNT_RE = re.compile(
    r"(?:[¥￥]\s*)?\d[\d,]*(?:\.\d+)?\s*(?:万|万元|元|人民币|rmb|cny|k|w)?"
    r"|[¥￥]\s*\d",
    re.IGNORECASE,
)

SOURCE_FILENAME_KEYS = {
    "filename",
    "file_name",
    "file_path",
    "file_url",
    "stored_filename",
    "original_filename",
    "object_key",
    "path",
    "url",
}

_DOC_NOTE_TITLE_RE = re.compile(r"【客户资料导入备注\s*-\s*[^】]+】")


def sanitize_document_memory_data(data: Any) -> Any:
    """Remove price-sensitive fields/text and source filenames from imported data."""
    return _sanitize_value(copy.deepcopy(data))


def sanitize_screen_resources(items: Any) -> list[dict]:
    sanitized = sanitize_document_memory_data(items)
    if not isinstance(sanitized, list):
        return []
    return [item for item in sanitized if isinstance(item, dict)]


def sanitize_agent_notes(notes: Any) -> str:
    text = str(notes or "")
    text = _DOC_NOTE_TITLE_RE.sub("【客户资料导入备注】", text)
    lines = []
    for line in text.splitlines():
        cleaned = _sanitize_text(line)
        if cleaned.strip():
            lines.append(cleaned.rstrip())
    return "\n".join(lines).strip()


def sanitize_reusable_memory_text(text: Any) -> str:
    """Remove project-specific budget and schedule fragments from reusable memory."""
    cleaned = _sanitize_text(str(text or ""))
    return _sanitize_project_schedule_text(cleaned)


def is_project_sensitive_memory_key(key: str) -> bool:
    """Return True for memory fields that should never be reused across projects."""
    normalized = str(key or "").strip().lower()
    return (
        _is_sensitive_field_key(normalized)
        or normalized in PROJECT_SCHEDULE_FIELD_KEYS
        or any(token in normalized for token in PROJECT_SCHEDULE_FIELD_KEYS)
    )


def _sanitize_value(value: Any, *, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            key_text = str(key)
            if is_project_sensitive_memory_key(key_text):
                continue
            if parent_key == "source" and key_text.lower() in SOURCE_FILENAME_KEYS:
                continue
            sanitized = _sanitize_value(child, parent_key=key_text)
            if _is_empty_after_sanitize(sanitized):
                continue
            result[key] = sanitized
        return result

    if isinstance(value, list):
        result = []
        for item in value:
            sanitized = _sanitize_value(item, parent_key=parent_key)
            if not _is_empty_after_sanitize(sanitized):
                result.append(sanitized)
        return result

    if isinstance(value, str):
        return _sanitize_text(value)

    return value


def _sanitize_text(text: str) -> str:
    text = str(text or "")
    if not text.strip():
        return ""

    text = _DOC_NOTE_TITLE_RE.sub("【客户资料导入备注】", text)
    fragments = [
        fragment.strip(" \t，,；;")
        for fragment in re.split(r"(?:[；;，,\n\r|｜]+|\s+/\s+)", text)
    ]
    kept = [fragment for fragment in fragments if fragment and not _is_sensitive_price_fragment(fragment)]
    return "，".join(kept)


def _sanitize_project_schedule_text(text: str) -> str:
    fragments = [
        fragment.strip(" \t，,；;")
        for fragment in re.split(r"(?:[；;，,\n\r|｜]+|\s+/\s+)", str(text or ""))
    ]
    kept = [
        fragment
        for fragment in fragments
        if fragment and not _is_project_schedule_fragment(fragment)
    ]
    return "，".join(kept)


def _is_sensitive_field_key(key: str) -> bool:
    normalized = str(key or "").strip().lower()
    return normalized in PRICE_FIELD_KEYS or any(token in normalized for token in PRICE_FIELD_KEYS)


def _is_sensitive_price_fragment(text: str) -> bool:
    normalized = str(text or "").lower()
    if any(keyword in normalized for keyword in PRICE_KEYWORDS):
        return True
    return any(keyword in normalized for keyword in AMOUNT_ONLY_PRICE_KEYWORDS) and bool(_MONEY_AMOUNT_RE.search(normalized))


def _is_project_schedule_fragment(text: str) -> bool:
    normalized = str(text or "").lower()
    return any(keyword.lower() in normalized for keyword in PROJECT_SCHEDULE_KEYWORDS)


def _is_empty_after_sanitize(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False
