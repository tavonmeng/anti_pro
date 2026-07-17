"""Helpers for interpreting attachment-only chat turns."""

from __future__ import annotations

import re

from app.services.ai_image_understanding import IMAGE_CONTEXT_MARKER


# Keep the marker value stable because it may already exist in stored agent
# context. New code treats it as a generic PDF/DOC/DOCX Brief document marker.
BRIEF_DOCUMENT_CONTEXT_MARKER = "[PDF Brief解析内容]"
PDF_BRIEF_CONTEXT_MARKER = BRIEF_DOCUMENT_CONTEXT_MARKER
_UPLOAD_SUMMARY_RE = re.compile(r"\[已上传(?:\s*\d+\s*个)?文件:\s*[^\]]+\]")


def strip_generated_upload_context(message: str, *, preserve_document_context: bool = False) -> str:
    """Return only user-authored text after removing upload markers and image summaries."""
    text = str(message or "")
    document_context = ""
    if preserve_document_context and BRIEF_DOCUMENT_CONTEXT_MARKER in text:
        document_context = BRIEF_DOCUMENT_CONTEXT_MARKER + text.split(BRIEF_DOCUMENT_CONTEXT_MARKER, 1)[1]
    if IMAGE_CONTEXT_MARKER in text:
        text = text.split(IMAGE_CONTEXT_MARKER, 1)[0]
    text = _UPLOAD_SUMMARY_RE.sub("", text)
    if not preserve_document_context and BRIEF_DOCUMENT_CONTEXT_MARKER in text:
        text = text.split(BRIEF_DOCUMENT_CONTEXT_MARKER, 1)[0]
    elif preserve_document_context and document_context:
        text = f"{text.strip()}\n\n{document_context}".strip()
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
    has_document_context = BRIEF_DOCUMENT_CONTEXT_MARKER in text
    if not has_upload_signal:
        if not has_document_context:
            return text.strip()

    user_text = strip_generated_upload_context(text)
    if IMAGE_CONTEXT_MARKER in text:
        upload_label = "[用户上传了图片素材]"
    elif has_document_context:
        upload_label = "[用户上传了文档资料]"
    else:
        upload_label = "[用户上传了文件素材]"
    if user_text:
        return f"{user_text}\n{upload_label}"
    return upload_label
