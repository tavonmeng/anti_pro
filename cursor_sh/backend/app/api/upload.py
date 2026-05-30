"""
文件上传 — 通用上传接口
支持现场实拍图、参考文件等上传

OSS_ENABLED=True 时上传到阿里云 OSS（私有 Bucket + 签名 URL），
OSS_ENABLED=False 时回退到本地磁盘存储（开发环境）。
"""

import os
import uuid
from typing import Optional
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.contractor import Contractor
from app.models.contractor_assignment import ContractorAssignment
from app.models.contractor_deliverable import ContractorDeliverable
from app.models.order import Order, OrderAssignee
from app.models.user import User, UserRole
from app.utils.business_log import log_business_event
from app.utils.dependencies import AnyUser, get_current_user_for_public_deployment, require_internal_deployment
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_now, beijing_now_iso

router = APIRouter(prefix="/upload", tags=["文件上传"])
logger = get_module_logger("order")

UPLOAD_CHUNK_SIZE = 1024 * 1024


def _safe_filename(filename: str | None, fallback: str) -> str:
    """去掉路径片段，避免本地存储时出现路径穿越。"""
    name = os.path.basename(filename or fallback).replace("\x00", "").strip()
    return name or fallback


def _local_safe_name(filename: str) -> str:
    timestamp = beijing_now().strftime("%Y%m%d_%H%M%S_%f")
    return "%s_%s_%s" % (timestamp, uuid.uuid4().hex[:8], filename)


async def _stream_upload_to_temp(file: UploadFile, max_size: int, limit_message: str) -> tuple[str, int]:
    """将上传文件分块写入临时文件，并在读取过程中做大小限制。"""
    tmp_dir = os.path.join(settings.UPLOAD_DIR, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    tmp_path = os.path.join(tmp_dir, "%s%s.part" % (uuid.uuid4().hex, ext))
    size = 0

    try:
        async with aiofiles.open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(status_code=413, detail=limit_message)
                await out.write(chunk)
        return tmp_path, size
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _store_local_temp_file(tmp_path: str, prefix: str, user_id: str, filename: str) -> tuple[str, str]:
    safe_name = _local_safe_name(filename)
    upload_dir = os.path.join(settings.UPLOAD_DIR, prefix, user_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, safe_name)
    os.replace(tmp_path, file_path)
    file_url = "/uploads/%s/%s/%s" % (prefix, user_id, safe_name)
    return safe_name, file_url


def _cleanup_temp_file(tmp_path: str):
    if not tmp_path:
        return
    try:
        os.remove(tmp_path)
    except OSError:
        pass


def _role_value(user: AnyUser) -> str:
    role = getattr(user, "role", "")
    return role.value if hasattr(role, "value") else str(role)


def _contains_object_key(value, key: str) -> bool:
    """Recursively check JSON-ish metadata for an OSS object key."""
    if isinstance(value, str):
        if value == key:
            return True
        from app.services.oss_service import extract_object_key
        return extract_object_key(value) == key
    if isinstance(value, dict):
        if value.get("object_key") == key or value.get("objectKey") == key:
            return True
        return any(_contains_object_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_object_key(item, key) for item in value)
    return False


def _key_matches_user_prefix(key: str, user_id: str) -> bool:
    allowed_prefixes = (
        f"site_photos/{user_id}/",
        f"deliverables/{user_id}/",
        f"showcase_cases/{user_id}/",
        f"avatars/{user_id}/",
        f"enterprise/{user_id}/",
    )
    return key.startswith(allowed_prefixes)


async def _can_access_order_object_key(db: AsyncSession, key: str, current_user: AnyUser) -> bool:
    role = _role_value(current_user)

    if role == UserRole.USER.value:
        result = await db.execute(select(Order).where(Order.user_id == current_user.id))
    elif role == UserRole.STAFF.value:
        result = await db.execute(
            select(Order)
            .join(OrderAssignee, Order.id == OrderAssignee.order_id)
            .where(OrderAssignee.assignee_id == current_user.id)
        )
    elif role == UserRole.CONTRACTOR.value:
        result = await db.execute(
            select(Order)
            .join(ContractorAssignment, Order.id == ContractorAssignment.order_id)
            .where(ContractorAssignment.contractor_id == current_user.id)
        )
    else:
        return False

    return any(_contains_object_key(order.order_data or {}, key) for order in result.scalars().all())


async def _can_access_deliverable_object_key(db: AsyncSession, key: str, current_user: AnyUser) -> bool:
    role = _role_value(current_user)

    query = select(ContractorDeliverable).join(
        ContractorAssignment,
        ContractorDeliverable.assignment_id == ContractorAssignment.id,
    )

    if role == UserRole.USER.value:
        query = query.join(Order, ContractorAssignment.order_id == Order.id).where(
            Order.user_id == current_user.id,
            ContractorDeliverable.is_published_to_user == True,  # noqa: E712
        )
    elif role == UserRole.STAFF.value:
        query = query.join(Order, ContractorAssignment.order_id == Order.id).join(
            OrderAssignee,
            Order.id == OrderAssignee.order_id,
        ).where(OrderAssignee.assignee_id == current_user.id)
    elif role == UserRole.CONTRACTOR.value:
        query = query.where(ContractorAssignment.contractor_id == current_user.id)
    else:
        return False

    result = await db.execute(query)
    return any(_contains_object_key(deliverable.files or [], key) for deliverable in result.scalars().all())


async def _can_access_object_key(db: AsyncSession, key: str, current_user: AnyUser) -> bool:
    role = _role_value(current_user)
    if role == UserRole.ADMIN.value:
        return True

    if _key_matches_user_prefix(key, current_user.id):
        return True

    if role == UserRole.USER.value:
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        if user and key in {user.avatar, user.business_license_url}:
            return True

    if role == UserRole.CONTRACTOR.value:
        result = await db.execute(select(Contractor).where(Contractor.id == current_user.id))
        contractor = result.scalar_one_or_none()
        if contractor and _contains_object_key(contractor.showcase_cases or [], key):
            return True

    return (
        await _can_access_order_object_key(db, key, current_user)
        or await _can_access_deliverable_object_key(db, key, current_user)
    )


def _log_upload_rejected(endpoint: str, user_id: str, filename: str | None, ext: str, reason: str) -> None:
    log_business_event(
        logger,
        "file_upload_rejected",
        level="warning",
        endpoint=endpoint,
        user_id=user_id,
        filename=filename,
        ext=ext,
        reason=reason,
    )


def _log_upload_success(
    endpoint: str,
    user_id: str,
    prefix: str,
    storage: str,
    filename: str,
    size: int,
    mime_type: str,
    object_key: str | None = None,
    url: str | None = None,
) -> None:
    log_business_event(
        logger,
        "file_uploaded",
        endpoint=endpoint,
        user_id=user_id,
        prefix=prefix,
        storage=storage,
        filename=filename,
        size=size,
        mime_type=mime_type,
        object_key=object_key,
        url=url,
    )


@router.post("/site-photo")
async def upload_site_photo(
    file: UploadFile = File(...),
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """上传现场实拍图或参考文件"""
    # 限制文件类型
    allowed_ext = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
        '.pdf', '.doc', '.docx', '.zip', '.rar', '.7z',
        '.ppt', '.pptx', '.xls', '.xlsx', '.txt',
        '.key', '.mp4', '.mov', '.avi',
    }
    ext = os.path.splitext(file.filename or '')[1].lower()
    user_id = current_user.id
    if ext not in allowed_ext:
        _log_upload_rejected("site_photo", user_id, file.filename, ext, "unsupported_ext")
        raise HTTPException(status_code=400, detail="不支持的文件类型: %s" % ext)

    filename = _safe_filename(file.filename, "upload%s" % ext)
    tmp_path, size = await _stream_upload_to_temp(file, 50 * 1024 * 1024, "文件大小不能超过50MB")

    try:
        if settings.OSS_ENABLED:
            from app.services.oss_service import upload_file_and_sign
            result = upload_file_and_sign(
                file_path=tmp_path,
                prefix="site_photos",
                user_id=user_id,
                filename=filename,
                content_type=file.content_type or "",
            )
            _log_upload_success(
                "site_photo",
                user_id,
                "site_photos",
                "oss",
                result["filename"],
                result["size"],
                file.content_type or "",
                object_key=result["object_key"],
            )
            return {
                "url": result["url"],
                "file_url": result["url"],
                "object_key": result["object_key"],
                "filename": result["filename"],
                "size": result["size"],
                "uploadedAt": beijing_now_iso(),
            }
        _safe_name, file_url = _store_local_temp_file(tmp_path, "site_photos", user_id, filename)
        tmp_path = ""
        _log_upload_success(
            "site_photo",
            user_id,
            "site_photos",
            "local",
            filename,
            size,
            file.content_type or "",
            url=file_url,
        )
        return {
            "url": file_url,
            "file_url": file_url,
            "filename": filename,
            "size": size,
            "uploadedAt": beijing_now_iso(),
        }
    finally:
        _cleanup_temp_file(tmp_path)


@router.post("/file")
async def upload_generic_file(
    file: UploadFile = File(...),
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """通用文件上传（支持图片、视频、文档，最大 50MB）

    用于承包商交付物上传等场景。
    """
    # 允许的文件类型
    allowed_ext = {
        # 图片
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
        # 视频
        '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
        # 文档
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.key', '.txt',
        # 设计文件
        '.psd', '.ai', '.eps', '.sketch', '.fig',
        # 3D 文件
        '.fbx', '.obj', '.max', '.blend', '.c4d',
        # 压缩包
        '.zip', '.rar', '.7z',
    }
    ext = os.path.splitext(file.filename or '')[1].lower()
    user_id = current_user.id
    if ext not in allowed_ext:
        _log_upload_rejected("generic_file", user_id, file.filename, ext, "unsupported_ext")
        raise HTTPException(status_code=400, detail="不支持的文件类型: %s" % ext)

    filename = _safe_filename(file.filename, "upload%s" % ext)
    tmp_path, size = await _stream_upload_to_temp(file, 50 * 1024 * 1024, "文件大小不能超过50MB")

    try:
        if settings.OSS_ENABLED:
            from app.services.oss_service import upload_file_and_sign
            result = upload_file_and_sign(
                file_path=tmp_path,
                prefix="deliverables",
                user_id=user_id,
                filename=filename,
                content_type=file.content_type or "",
            )
            _log_upload_success(
                "generic_file",
                user_id,
                "deliverables",
                "oss",
                result["filename"],
                result["size"],
                file.content_type or "",
                object_key=result["object_key"],
            )
            return {
                "code": 200,
                "message": "上传成功",
                "data": {
                    "url": result["url"],
                    "object_key": result["object_key"],
                    "filename": result["filename"],
                    "size": result["size"],
                    "mime_type": file.content_type or "",
                    "uploadedAt": beijing_now_iso(),
                }
            }
        _safe_name, file_url = _store_local_temp_file(tmp_path, "deliverables", user_id, filename)
        tmp_path = ""
        _log_upload_success(
            "generic_file",
            user_id,
            "deliverables",
            "local",
            filename,
            size,
            file.content_type or "",
            url=file_url,
        )
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": file_url,
                "filename": filename,
                "size": size,
                "mime_type": file.content_type or "",
                "uploadedAt": beijing_now_iso(),
            }
        }
    finally:
        _cleanup_temp_file(tmp_path)


@router.get("/sign-url")
async def get_signed_url(
    key: str = Query(..., description="OSS object key"),
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db),
):
    """为私有 Bucket 中的文件生成新的签名 URL（1小时有效期）

    前端在签名 URL 过期后调用此接口刷新。
    """
    if not settings.OSS_ENABLED:
        # 本地模式：直接返回原始路径
        return {"code": 200, "message": "获取成功", "data": {"url": key}}

    from app.services.oss_service import extract_object_key, get_signed_url as oss_sign

    object_key = extract_object_key(key)
    if not object_key:
        raise HTTPException(status_code=400, detail="无效的 OSS 文件地址")

    if not await _can_access_object_key(db, object_key, current_user):
        raise HTTPException(status_code=403, detail="无权访问此文件")

    try:
        url = oss_sign(object_key, expires=3600)
        return {"code": 200, "message": "获取成功", "data": {"url": url, "object_key": object_key}}
    except Exception as e:
        raise HTTPException(status_code=500, detail="生成签名 URL 失败，请稍后重试") from e


@router.post("/showcase-video")
async def upload_showcase_video(
    file: UploadFile = File(...),
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
):
    """承包商优秀案例视频上传（最大 200MB）

    仅允许视频格式，上传到 OSS showcase_cases/ 目录。
    """
    # 限制文件类型（仅视频）
    allowed_ext = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
    ext = os.path.splitext(file.filename or '')[1].lower()
    await require_internal_deployment()
    if _role_value(current_user) not in [UserRole.CONTRACTOR.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="仅承包商或管理员可以上传案例视频")

    user_id = current_user.id
    if ext not in allowed_ext:
        _log_upload_rejected("showcase_video", user_id, file.filename, ext, "unsupported_ext")
        raise HTTPException(status_code=400, detail="仅支持视频文件格式: %s" % ', '.join(allowed_ext))

    max_size = 200 * 1024 * 1024
    filename = _safe_filename(file.filename, "showcase%s" % ext)
    tmp_path, size = await _stream_upload_to_temp(file, max_size, "视频文件大小不能超过200MB")

    try:
        if settings.OSS_ENABLED:
            from app.services.oss_service import upload_file_and_sign
            result = upload_file_and_sign(
                file_path=tmp_path,
                prefix="showcase_cases",
                user_id=user_id,
                filename=filename,
                content_type=file.content_type or "video/mp4",
            )
            _log_upload_success(
                "showcase_video",
                user_id,
                "showcase_cases",
                "oss",
                result["filename"],
                result["size"],
                file.content_type or "video/mp4",
                object_key=result["object_key"],
            )
            return {
                "code": 200,
                "message": "上传成功",
                "data": {
                    "url": result["url"],
                    "object_key": result["object_key"],
                    "filename": result["filename"],
                    "size": result["size"],
                    "mime_type": file.content_type or "video/mp4",
                    "uploadedAt": beijing_now_iso(),
                }
            }
        _safe_name, file_url = _store_local_temp_file(tmp_path, "showcase_cases", user_id, filename)
        tmp_path = ""
        _log_upload_success(
            "showcase_video",
            user_id,
            "showcase_cases",
            "local",
            filename,
            size,
            file.content_type or "video/mp4",
            url=file_url,
        )
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": file_url,
                "filename": filename,
                "size": size,
                "mime_type": file.content_type or "video/mp4",
                "uploadedAt": beijing_now_iso(),
            }
        }
    finally:
        _cleanup_temp_file(tmp_path)
