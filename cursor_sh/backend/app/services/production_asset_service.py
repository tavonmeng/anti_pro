"""制作端可见素材聚合。"""

import copy
import os
from typing import Any, Iterable, Optional


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
DOCUMENT_EXTENSIONS = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".key"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}


def _file_name(item: dict[str, Any], fallback: str) -> str:
    return (
        item.get("name")
        or item.get("filename")
        or item.get("originalName")
        or item.get("title")
        or fallback
    )


def _file_url(item: dict[str, Any]) -> Optional[str]:
    return (
        item.get("url")
        or item.get("file_url")
        or item.get("fileUrl")
        or item.get("signed_url")
        or item.get("signedUrl")
    )


def _kind_from_file(item: dict[str, Any]) -> str:
    mime = str(item.get("mime_type") or item.get("type") or "").lower()
    name = _file_name(item, "")
    url = _file_url(item) or item.get("object_key") or ""
    ext = os.path.splitext(str(name or url).split("?", 1)[0])[1].lower()

    if mime in {"image", "photo"} or mime.startswith("image/") or ext in IMAGE_EXTENSIONS:
        return "image"
    if mime == "video" or mime.startswith("video/") or ext in VIDEO_EXTENSIONS:
        return "video"
    if mime in {"application/pdf", "application/x-pdf"} or ext == ".pdf":
        return "pdf"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in ARCHIVE_EXTENSIONS:
        return "archive"
    return "other"


def _asset_key(item: dict[str, Any]) -> str:
    return str(
        item.get("object_key")
        or _file_url(item)
        or item.get("id")
        or _file_name(item, "")
    )


def _iter_file_items(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield copy.deepcopy(item)
    elif isinstance(value, dict):
        yield copy.deepcopy(value)


def _append_assets(
    assets: list[dict[str, Any]],
    seen: set[str],
    items: Any,
    source: str,
    label: str,
) -> None:
    for raw_item in _iter_file_items(items):
        key = _asset_key(raw_item)
        if not key or key in seen:
            continue
        seen.add(key)

        name = _file_name(raw_item, label)
        assets.append({
            **raw_item,
            "name": name,
            "kind": _kind_from_file(raw_item),
            "source": source,
            "label": label,
        })


def build_production_assets(
    order_data: dict[str, Any] | None,
    design_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """汇总用户与管理员提供给制作者使用的素材。"""
    order_data = order_data or {}
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()

    for field_name in ("scenePhotos", "site_photos", "scene_photos"):
        _append_assets(assets, seen, order_data.get(field_name), "scene_photos", "现场/参考文件")

    _append_assets(assets, seen, order_data.get("materials"), "materials", "相关材料")

    selected_item = order_data.get("selectedLibraryItem")
    if isinstance(selected_item, dict) and isinstance(selected_item.get("media"), dict):
        media = copy.deepcopy(selected_item["media"])
        media.setdefault("id", selected_item.get("id"))
        media.setdefault("name", selected_item.get("title") or "资源库素材")
        _append_assets(assets, seen, media, "selected_library_item", "资源库素材")

    if isinstance(design_plan, dict):
        _append_assets(assets, seen, design_plan.get("files"), "design_plan", "AI设计方案附件")

    return assets
