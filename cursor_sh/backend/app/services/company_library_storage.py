"""公司资料库资产存储。

生产环境写入阿里云 OSS；本地未开启 OSS 时回退到 uploads 目录，方便开发调试。
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from app.config import settings


def store_company_library_asset(
    document_id: str,
    stage: str,
    filename: str,
    data: bytes,
    content_type: str = "",
) -> dict:
    """保存公司资料库资产，并返回可存入数据库的元数据。"""
    safe_filename = _safe_filename(filename)
    if settings.OSS_ENABLED:
        from app.services.oss_service import get_signed_url, upload_bytes

        object_key = f"company_library/{document_id}/{stage}/{safe_filename}"
        upload_bytes(data, object_key, content_type)
        url = get_signed_url(object_key, settings.OSS_SIGNED_URL_EXPIRES)
        storage = "oss"
    else:
        relative_path = os.path.join("company_library", document_id, stage, safe_filename)
        full_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, relative_path))
        upload_root = os.path.abspath(settings.UPLOAD_DIR)
        if full_path != upload_root and not full_path.startswith(upload_root + os.sep):
            raise ValueError("非法的资料库存储路径")
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as fh:
            fh.write(data)
        object_key = f"/uploads/{relative_path.replace(os.sep, '/')}"
        url = object_key
        storage = "local"

    return {
        "storage": storage,
        "object_key": object_key,
        "url": url,
        "filename": safe_filename,
        "content_type": content_type,
        "size": len(data),
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }


def sign_company_library_asset(asset: dict | None) -> dict:
    """为返回前端的资料库资产补签名 URL。"""
    if not isinstance(asset, dict) or not asset:
        return {}
    signed = dict(asset)
    object_key = str(signed.get("object_key") or "")
    if settings.OSS_ENABLED and object_key and not object_key.startswith("/"):
        from app.services.oss_service import get_signed_url

        signed["url"] = get_signed_url(object_key, settings.OSS_SIGNED_URL_EXPIRES)
    return signed


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "asset")
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()
    return name or "asset"
