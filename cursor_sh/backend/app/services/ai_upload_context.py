"""Helpers for interpreting attachment-only chat turns."""

from __future__ import annotations

import re

from app.services.ai_image_understanding import IMAGE_CONTEXT_MARKER


_UPLOAD_SUMMARY_RE = re.compile(r"\[已上传(?:\s*\d+\s*个)?文件:\s*[^\]]+\]")


def strip_generated_upload_context(message: str) -> str:
    """Return only user-authored text after removing upload markers and image summaries."""
    text = str(message or "")
    if IMAGE_CONTEXT_MARKER in text:
        text = text.split(IMAGE_CONTEXT_MARKER, 1)[0]
    text = _UPLOAD_SUMMARY_RE.sub("", text)
    return text.strip()


def is_upload_only_material_message(message: str, *, has_attachments: bool = False) -> bool:
    """True when the turn only adds uploaded files/material context, with no user instruction."""
    text = str(message or "")
    has_upload_signal = bool(has_attachments or _UPLOAD_SUMMARY_RE.search(text) or IMAGE_CONTEXT_MARKER in text)
    if not has_upload_signal:
        return False
    return not re.sub(r"\s+", "", strip_generated_upload_context(text))


def state_safe_upload_message(message: str) -> str:
    """Return a persistence-safe message that removes generated upload details."""
    text = str(message or "")
    has_upload_signal = bool(_UPLOAD_SUMMARY_RE.search(text) or IMAGE_CONTEXT_MARKER in text)
    if not has_upload_signal:
        return text.strip()

    user_text = strip_generated_upload_context(text)
    if user_text:
        return f"{user_text}\n[用户上传了图片素材]"
    return "[用户上传了图片素材]"
