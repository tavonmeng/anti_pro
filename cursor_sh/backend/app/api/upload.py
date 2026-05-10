"""
文件上传 — 通用上传接口
支持现场实拍图、参考文件等上传

OSS_ENABLED=True 时上传到阿里云 OSS（私有 Bucket + 签名 URL），
OSS_ENABLED=False 时回退到本地磁盘存储（开发环境）。
"""

import os
import uuid
from typing import Optional
from datetime import datetime
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, Query
from app.config import settings
from app.utils.security import decode_access_token

router = APIRouter(prefix="/upload", tags=["文件上传"])

UPLOAD_CHUNK_SIZE = 1024 * 1024


def _safe_filename(filename: str | None, fallback: str) -> str:
    """去掉路径片段，避免本地存储时出现路径穿越。"""
    name = os.path.basename(filename or fallback).replace("\x00", "").strip()
    return name or fallback


def _local_safe_name(filename: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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


def _get_user_id_from_request(request: Request) -> str:
    """从请求头中尽量提取用户ID，失败返回 anonymous"""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_access_token(auth_header[7:])
        if payload:
            return payload.get("user_id", "anonymous")
    return "anonymous"


@router.post("/site-photo")
async def upload_site_photo(
    request: Request,
    file: UploadFile = File(...),
):
    """上传现场实拍图或参考文件"""
    # 限制文件类型
    allowed_ext = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
        '.pdf', '.doc', '.docx', '.zip', '.rar',
        '.ppt', '.pptx', '.xls', '.xlsx', '.txt',
        '.mp4', '.mov', '.avi',
    }
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="不支持的文件类型: %s" % ext)

    user_id = _get_user_id_from_request(request)
    filename = _safe_filename(file.filename, "upload%s" % ext)
    tmp_path, size = await _stream_upload_to_temp(file, 20 * 1024 * 1024, "文件大小不能超过20MB")

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
            return {
                "url": result["url"],
                "file_url": result["url"],
                "object_key": result["object_key"],
                "filename": result["filename"],
                "size": result["size"],
                "uploadedAt": datetime.now().isoformat(),
            }
        _safe_name, file_url = _store_local_temp_file(tmp_path, "site_photos", user_id, filename)
        tmp_path = ""
        return {
            "url": file_url,
            "file_url": file_url,
            "filename": filename,
            "size": size,
            "uploadedAt": datetime.now().isoformat(),
        }
    finally:
        _cleanup_temp_file(tmp_path)


@router.post("/file")
async def upload_generic_file(
    request: Request,
    file: UploadFile = File(...),
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
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt',
        # 设计文件
        '.psd', '.ai', '.eps', '.sketch', '.fig',
        # 3D 文件
        '.fbx', '.obj', '.max', '.blend', '.c4d',
        # 压缩包
        '.zip', '.rar', '.7z',
    }
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="不支持的文件类型: %s" % ext)

    user_id = _get_user_id_from_request(request)
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
            return {
                "code": 200,
                "message": "上传成功",
                "data": {
                    "url": result["url"],
                    "object_key": result["object_key"],
                    "filename": result["filename"],
                    "size": result["size"],
                    "mime_type": file.content_type or "",
                    "uploadedAt": datetime.now().isoformat(),
                }
            }
        _safe_name, file_url = _store_local_temp_file(tmp_path, "deliverables", user_id, filename)
        tmp_path = ""
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": file_url,
                "filename": filename,
                "size": size,
                "mime_type": file.content_type or "",
                "uploadedAt": datetime.now().isoformat(),
            }
        }
    finally:
        _cleanup_temp_file(tmp_path)


@router.get("/sign-url")
async def get_signed_url(
    request: Request,
    key: str = Query(..., description="OSS object key"),
):
    """为私有 Bucket 中的文件生成新的签名 URL（1小时有效期）

    前端在签名 URL 过期后调用此接口刷新。
    """
    if not settings.OSS_ENABLED:
        # 本地模式：直接返回原始路径
        return {"url": key}

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(auth_header[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期")

    from app.services.oss_service import get_signed_url as oss_sign
    try:
        url = oss_sign(key, expires=3600)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail="生成签名 URL 失败: %s" % str(e))


@router.post("/showcase-video")
async def upload_showcase_video(
    request: Request,
    file: UploadFile = File(...),
):
    """承包商优秀案例视频上传（最大 200MB）

    仅允许视频格式，上传到 OSS showcase_cases/ 目录。
    """
    # 限制文件类型（仅视频）
    allowed_ext = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="仅支持视频文件格式: %s" % ', '.join(allowed_ext))

    max_size = 200 * 1024 * 1024
    user_id = _get_user_id_from_request(request)
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
            return {
                "code": 200,
                "message": "上传成功",
                "data": {
                    "url": result["url"],
                    "object_key": result["object_key"],
                    "filename": result["filename"],
                    "size": result["size"],
                    "mime_type": file.content_type or "video/mp4",
                    "uploadedAt": datetime.now().isoformat(),
                }
            }
        _safe_name, file_url = _store_local_temp_file(tmp_path, "showcase_cases", user_id, filename)
        tmp_path = ""
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": file_url,
                "filename": filename,
                "size": size,
                "mime_type": file.content_type or "video/mp4",
                "uploadedAt": datetime.now().isoformat(),
            }
        }
    finally:
        _cleanup_temp_file(tmp_path)
