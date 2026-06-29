"""Vision pre-processing for uploaded images in AI conversations."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from typing import Any
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.services.ai_client import post_chat_completion
from app.utils.log_setup import get_module_logger

logger = get_module_logger("ai")

IMAGE_CONTEXT_MARKER = "[图片理解摘要]"
MAX_INLINE_IMAGE_BYTES = 7 * 1024 * 1024
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
IMAGE_KIND_LABELS = {
    "site_screen_photo": "实拍屏幕/现场图",
    "reference_design": "参考设计/风格图",
    "other": "其他图片",
}


class UploadedAttachment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = ""
    url: str = ""
    type: str = ""
    is_image: bool | None = Field(default=None, alias="isImage")
    object_key: str | None = Field(default=None, alias="objectKey")
    size: int | None = None


def _is_supported_image(attachment: UploadedAttachment) -> bool:
    if attachment.is_image is False:
        return False

    mime = (attachment.type or "").lower()
    ext = os.path.splitext((attachment.name or attachment.url or "").split("?", 1)[0])[1].lower()
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return True
    return mime in {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"}


def image_attachments(attachments: list[UploadedAttachment] | None) -> list[UploadedAttachment]:
    return [
        attachment
        for attachment in (attachments or [])
        if attachment.url and _is_supported_image(attachment)
    ]


def _safe_local_upload_path(url: str) -> str | None:
    clean_url = unquote((url or "").split("?", 1)[0])
    if not clean_url.startswith("/uploads/"):
        return None

    rel_path = clean_url.removeprefix("/uploads/").lstrip("/")
    upload_root = os.path.abspath(settings.UPLOAD_DIR)
    path = os.path.abspath(os.path.join(upload_root, rel_path))
    if path != upload_root and not path.startswith(upload_root + os.sep):
        return None
    if not os.path.isfile(path):
        return None
    return path


def _local_upload_data_url(path: str, fallback_mime: str = "") -> str | None:
    size = os.path.getsize(path)
    if size <= 0 or size > MAX_INLINE_IMAGE_BYTES:
        return None

    mime = fallback_mime or mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def image_url_for_model(attachment: UploadedAttachment) -> str | None:
    url = (attachment.url or "").strip()
    if not url:
        return None
    if url.startswith("data:image/"):
        return url
    if url.startswith("http://") or url.startswith("https://"):
        return url

    local_path = _safe_local_upload_path(url)
    if local_path:
        return _local_upload_data_url(local_path, attachment.type)
    return None


def _build_vision_prompt(message: str, file_names: list[str]) -> str:
    return (
        "你是 Unique Vision AI 的图片理解器，服务于裸眼3D户外媒体项目 Brief。\n"
        "请基于用户上传的图片提取可用于项目沟通的信息。\n\n"
        "严格要求：\n"
        "- 只能描述图片中可见的内容，或用户文字里明确说明的信息。\n"
        "- 不要推断城市、预算、上刊时间或屏幕尺寸；除非图片文字或用户文字明确给出。\n"
        "- 如果图片是参考风格、角色、材质、屏幕现场或空间环境，请说明它能帮助确认哪些方向。\n"
        "- 不要输出营销话术，不要替用户下结论。\n\n"
        "只返回 JSON object，格式："
        '{"image_kind":"site_screen_photo | reference_design | other",'
        '"visible_summary":"...","project_clues":["..."],'
        '"creative_or_style_clues":["..."],"media_or_scene_clues":["..."],'
        '"uncertain_or_missing":["..."]}\n\n'
        "image_kind 判断：实拍大屏、现场点位、屏幕照片、空间环境 => site_screen_photo；"
        "参考设计、角色图、材质/风格参考、效果图 => reference_design；无法归类 => other。\n\n"
        f"用户当前消息：{message or ''}\n"
        f"上传文件名：{'、'.join(file_names)}"
    )


def _list_to_text(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _image_kind_label(value: Any) -> str:
    kind = str(value or "other").strip()
    return IMAGE_KIND_LABELS.get(kind, IMAGE_KIND_LABELS["other"])


def _format_json_summary(raw: str, file_names: list[str]) -> str:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return f"{IMAGE_CONTEXT_MARKER}\n文件：{'、'.join(file_names)}\n视觉摘要：{raw.strip()}"
        parsed = json.loads(match.group(0))

    lines = [IMAGE_CONTEXT_MARKER, f"文件：{'、'.join(file_names)}"]
    lines.append(f"图片类型：{_image_kind_label(parsed.get('image_kind'))}")
    visible_summary = str(parsed.get("visible_summary") or "").strip()
    if visible_summary:
        lines.append(f"视觉摘要：{visible_summary}")

    field_labels = [
        ("project_clues", "可用于 Brief 的线索"),
        ("creative_or_style_clues", "创意/风格线索"),
        ("media_or_scene_clues", "媒体/现场线索"),
        ("uncertain_or_missing", "识别边界"),
    ]
    for key, label in field_labels:
        text = _list_to_text(parsed.get(key))
        if text:
            lines.append(f"{label}：{text}")
    return "\n".join(lines)


async def summarize_uploaded_images(
    *,
    message: str,
    attachments: list[UploadedAttachment] | None,
) -> str:
    images = image_attachments(attachments)
    if not images or not settings.AI_API_KEY:
        return ""

    content: list[dict[str, Any]] = []
    file_names: list[str] = []
    for attachment in images[:3]:
        image_url = image_url_for_model(attachment)
        if not image_url:
            continue
        file_names.append(attachment.name or "上传图片")
        content.append({"type": "image_url", "image_url": {"url": image_url}})

    if not content:
        return ""

    content.append({"type": "text", "text": _build_vision_prompt(message, file_names)})
    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.1,
                "max_tokens": 700,
                "enable_thinking": False,
                "response_format": {"type": "json_object"},
            },
            timeout=min(float(settings.AI_HTTP_TIMEOUT or 30), 45.0),
            attempts=1,
        )
        raw = data["choices"][0]["message"]["content"]
        return _format_json_summary(raw, file_names)
    except Exception as exc:
        logger.warning("ai_image_understanding_failed", extra={"error": str(exc)})
        return ""


def append_image_context_to_message(message: str, image_context: str) -> str:
    if not image_context or IMAGE_CONTEXT_MARKER in (message or ""):
        return message
    base = (message or "").strip()
    if not base:
        return image_context.strip()
    return f"{base}\n\n{image_context.strip()}"


def build_image_feedback_reply_instruction(message: str) -> str:
    if IMAGE_CONTEXT_MARKER not in (message or ""):
        return ""
    return (
        "\n\n【图片上传后的用户可见反馈】\n"
        "- 当前用户消息包含[图片理解摘要]时，回复开头必须先给一段轻量的看图反馈，让用户明确感到你已经理解图片；"
        "不要直接暴露[图片理解摘要]、JSON 字段名或后台处理过程。\n"
        "- 如果图片类型是「实拍屏幕/现场图」，开头可以用「我先看了一下这张现场图，能抓到几个对方案有用的线索：」，"
        "优先反馈屏幕形态、现场观看关系、空间机会，以及这张图能如何帮助空间适配或创意判断；不要推断具体尺寸、城市、预算或上刊时间，"
        "也不要把识别边界写成待补信息清单。\n"
        "- 如果图片类型是「参考设计/风格图」，开头可以用「我先从这张参考图里抓到几个方向：」，"
        "优先反馈视觉主体、风格质感、情绪气质、可转化成裸眼3D的点；不要声称已经形成完整正式方案。\n"
        "- 反馈段保持克制，通常 2-4 条短要点即可；随后再继续创意方向草案、阶段性创意评估或 Brief 追问。"
    )
