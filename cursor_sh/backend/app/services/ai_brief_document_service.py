"""Extract Brief information from PDFs uploaded in an AI chat."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from app.config import settings
from app.services.ai_brief_state import FIELD_LABELS, MEDIA_3D_BRIEF_FIELDS
from app.services.ai_client import post_chat_completion
from app.services.document_parser_service import build_llm_text_chunks, parse_document
from app.services.ai_upload_context import PDF_BRIEF_CONTEXT_MARKER
from app.services.oss_service import extract_object_key
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger


logger = get_module_logger("ai")

MAX_PDF_ATTACHMENTS = 3
MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_FIELD_CHARS = 4000
MAX_CONTEXT_CHARS = 12000
ALLOWED_OBJECT_PREFIXES = ("site_photos/{user_id}/", "deliverables/{user_id}/")


@dataclass
class BriefDocumentExtraction:
    """The structured result used by the chat and Brief state updater."""

    updates: dict[str, str] = field(default_factory=dict)
    context: str = ""
    filenames: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def is_pdf_attachment(attachment) -> bool:
    name = str(getattr(attachment, "name", "") or getattr(attachment, "url", ""))
    mime = str(getattr(attachment, "type", "") or "").lower()
    return Path(name.split("?", 1)[0]).suffix.lower() == ".pdf" or mime == "application/pdf"


async def extract_uploaded_brief_documents(
    attachments: list,
    *,
    user_id: str,
) -> BriefDocumentExtraction:
    """Read user-owned PDFs and extract only explicit Brief information."""
    pdfs = [item for item in (attachments or []) if is_pdf_attachment(item)]
    if not pdfs:
        return BriefDocumentExtraction()

    result = BriefDocumentExtraction()
    for attachment in pdfs[:MAX_PDF_ATTACHMENTS]:
        filename = _attachment_name(attachment)
        result.filenames.append(filename)
        temp_path = ""
        try:
            temp_path, parse_path = _materialize_attachment(attachment, user_id=user_id)
            if os.path.getsize(parse_path) > MAX_PDF_BYTES:
                raise ValueError("PDF 文件过大，暂不处理")
            sections = parse_document(parse_path, filename)
            chunks = build_llm_text_chunks(
                sections,
                max_chunk_chars=settings.DOCUMENT_EXTRACT_CHUNK_CHARS,
                max_total_chars=settings.DOCUMENT_EXTRACT_MAX_TOTAL_CHARS,
            )
            if not any(chunk.strip() for chunk in chunks):
                raise ValueError("PDF 没有可提取的文本，可能是扫描件")
            updates = await _extract_brief_updates(chunks, filename)
            _merge_updates(result.updates, updates)
        except Exception as exc:
            result.failures.append(f"{filename}：{_public_failure_message(exc)}")
            log_business_event(
                logger,
                "ai_brief_pdf_extract_failed",
                level="warning",
                user_id=user_id,
                filename=filename,
                error_type=exc.__class__.__name__,
                error=str(exc),
            )
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    result.context = build_brief_document_context(result)
    return result


def build_brief_document_context(result: BriefDocumentExtraction) -> str:
    lines = [PDF_BRIEF_CONTEXT_MARKER, f"文件：{'、'.join(result.filenames)}"]
    if result.updates:
        lines.append("已从 PDF 提取的 Brief 内容（仅包含文件中明确出现的信息）：")
        for field in MEDIA_3D_BRIEF_FIELDS:
            value = result.updates.get(field)
            if value:
                lines.append(f"- {FIELD_LABELS.get(field, field)}：{value}")
    else:
        lines.append("未识别到可映射的 Brief 字段。")
    if result.failures:
        lines.append("处理提示：" + "；".join(result.failures))
    text = "\n".join(lines)
    return text[:MAX_CONTEXT_CHARS]


def build_brief_document_confirmation_reply(result: BriefDocumentExtraction) -> str:
    """Create the user-visible review message for an extracted PDF Brief."""
    if not result.updates:
        detail = "；".join(result.failures) if result.failures else "未识别到可映射的项目需求"
        return (
            f"已收到您上传的 PDF，但暂未提取到可确认的 Brief 信息（{detail}）。"
            "请上传带可复制文字的 PDF，或直接在对话中补充项目需求。"
        )

    lines = ["我已经从您上传的 PDF 中整理出以下项目需求，并纳入本次 Brief：", ""]
    for field in MEDIA_3D_BRIEF_FIELDS:
        value = result.updates.get(field)
        if value:
            lines.append(f"- **{FIELD_LABELS.get(field, field)}**：{value}")
    lines.extend(
        [
            "",
            "如有需要调整的内容，请直接告诉我对应字段和新信息；未提及的内容将保持为当前 Brief。",
        ]
    )
    return "\n".join(lines)


def build_brief_document_revision_reply(updates: dict[str, str]) -> str:
    """Acknowledge only the PDF Brief fields explicitly corrected by the user."""
    lines = ["已更新本次 Brief 中以下内容：", ""]
    for field in MEDIA_3D_BRIEF_FIELDS:
        value = str((updates or {}).get(field) or "").strip()
        if value:
            lines.append(f"- **{FIELD_LABELS.get(field, field)}**：{value}")
    return "\n".join(lines)


async def _extract_brief_updates(chunks: list[str], filename: str) -> dict[str, str]:
    if not settings.AI_API_KEY:
        return {}

    results: list[dict[str, str]] = []
    total_chunks = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        prompt_prefix = ""
        if total_chunks > 1:
            prompt_prefix = f"这是长文档的第 {index}/{total_chunks} 段。只抽取本段明确出现的信息，后续系统会合并。\n\n"
        try:
            data = await post_chat_completion(
                {
                    "model": settings.DOCUMENT_EXTRACT_MODEL or settings.AI_MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": _brief_extract_prompt()},
                        {
                            "role": "user",
                            "content": f"文件名：{filename}\n\n{prompt_prefix}PDF 文本：\n{chunk}",
                        },
                    ],
                    "response_format": {"type": "json_object"},
                    "enable_thinking": False,
                },
                timeout=settings.DOCUMENT_EXTRACT_TIMEOUT,
            )
            raw = str(data["choices"][0]["message"]["content"] or "")
            parsed = _parse_json(raw)
            normalized = _normalize_updates(parsed)
            if normalized:
                results.append(normalized)
        except Exception as exc:
            log_business_event(
                logger,
                "ai_brief_pdf_chunk_extract_failed",
                level="warning",
                filename=filename,
                chunk_index=index,
                total_chunks=total_chunks,
                error_type=exc.__class__.__name__,
                error=str(exc),
            )

    merged: dict[str, str] = {}
    for item in results:
        _merge_updates(merged, item)
    return merged


def _brief_extract_prompt() -> str:
    fields = "、".join(f"{key}（{FIELD_LABELS[key]}）" for key in MEDIA_3D_BRIEF_FIELDS)
    return (
        "你是裸眼3D户外媒体项目的 Brief 信息抽取器。"
        "请从用户上传的 PDF 文本中抽取明确出现的项目需求，供需求 Agent 使用。\n"
        "只返回严格 JSON object，不要解释，不要 Markdown。\n"
        f"只能使用这些字段：{fields}。\n"
        "字段映射：项目名称到 project_name；项目背景、媒体资源介绍到 resource_background；"
        "目标人群、观看场景到 audience_scene；媒体定位、品牌调性到 media_positioning；"
        "城市、点位、屏幕位置到 city_location；观看方向、观看距离、动线到 viewing_path；"
        "艺术风格到 art_direction；主题、主体、核心表达、动作机制到 theme_concept；"
        "屏幕尺寸、分辨率、比例、屏幕类型到 media_specs；时长、数量、频次到 timing_number；"
        "文件格式、帧率、色彩、安全区、制作或交付要求到 tech_delivery；"
        "审核禁忌、审核流程到 content_review；预算或费用范围到 budget；"
        "上线或上刊时间到 online_time；其他明确要求到 special_requirements；"
        "无法归类但与项目有关的内容到 remarks。\n"
        "只抽取 PDF 中明确写出的信息，不推测、不补全、不把公司资料或案例当成当前项目需求。"
        "没有信息的字段返回空字符串。长字段保留关键原意并适当压缩。\n"
        "返回格式示例：{\"project_name\":\"\",\"resource_background\":\"\","
        "\"audience_scene\":\"\",\"media_positioning\":\"\",\"city_location\":\"\","
        "\"viewing_path\":\"\",\"art_direction\":\"\",\"theme_concept\":\"\","
        "\"media_specs\":\"\",\"timing_number\":\"\",\"tech_delivery\":\"\","
        "\"content_review\":\"\",\"budget\":\"\",\"online_time\":\"\","
        "\"special_requirements\":\"\",\"remarks\":\"\"}"
    )


def _normalize_updates(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for field in MEDIA_3D_BRIEF_FIELDS:
        raw = value.get(field)
        if isinstance(raw, list):
            text = "；".join(str(item).strip() for item in raw if str(item).strip())
        else:
            text = str(raw or "").strip()
        text = re.sub(r"\s+", " ", text)
        if text:
            normalized[field] = text[:MAX_FIELD_CHARS]
    return normalized


def _merge_updates(target: dict[str, str], incoming: dict[str, str]) -> None:
    for field, value in incoming.items():
        if not value:
            continue
        current = target.get(field, "")
        if not current:
            target[field] = value
        elif value not in current:
            target[field] = f"{current}\n{value}"[:MAX_FIELD_CHARS]


def _parse_json(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return {}
        parsed = json.loads(match.group(0))
    return parsed if isinstance(parsed, dict) else {}


def _attachment_name(attachment) -> str:
    name = str(getattr(attachment, "name", "") or "上传的 PDF")
    return os.path.basename(name) or "上传的 PDF"


def _materialize_attachment(attachment, *, user_id: str) -> tuple[str, str]:
    """Return (temporary path to delete, path to parse)."""
    url = str(getattr(attachment, "url", "") or "")
    object_key = str(getattr(attachment, "object_key", "") or "")
    if settings.OSS_ENABLED:
        object_key = object_key or extract_object_key(url)
        if not _is_allowed_object_key(object_key, user_id):
            raise PermissionError("无法访问该文件")
        fd, temp_path = tempfile.mkstemp(prefix="ai_brief_pdf_", suffix=".pdf")
        os.close(fd)
        from app.services.oss_service import download_object_to_file
        download_object_to_file(object_key, temp_path)
        return temp_path, temp_path

    clean_url = unquote(url.split("?", 1)[0])
    if not clean_url.startswith("/uploads/"):
        raise PermissionError("无法访问该文件")
    relative = clean_url.removeprefix("/uploads/").lstrip("/")
    if not _is_allowed_object_key(relative, user_id):
        raise PermissionError("无法访问该文件")
    upload_root = os.path.abspath(settings.UPLOAD_DIR)
    path = os.path.abspath(os.path.join(upload_root, relative))
    if path == upload_root or not path.startswith(upload_root + os.sep) or not os.path.isfile(path):
        raise FileNotFoundError("文件不存在")
    return "", path


def _is_allowed_object_key(key: str, user_id: str) -> bool:
    if not key or not user_id:
        return False
    return any(key.startswith(prefix.format(user_id=user_id)) for prefix in ALLOWED_OBJECT_PREFIXES)


def _public_failure_message(exc: Exception) -> str:
    if isinstance(exc, ValueError) and "扫描件" in str(exc):
        return "没有可复制的文字，可能是扫描件"
    if isinstance(exc, ValueError) and "过大" in str(exc):
        return "文件过大"
    if isinstance(exc, PermissionError):
        return "无法访问文件"
    if isinstance(exc, FileNotFoundError):
        return "文件不存在"
    if isinstance(exc, RuntimeError) and "PDF" in str(exc):
        return "PDF 解析失败"
    return "解析失败"
