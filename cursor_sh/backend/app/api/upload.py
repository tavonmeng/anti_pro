"""
文件上传 — 通用上传接口
支持现场实拍图、参考文件等上传

OSS_ENABLED=True 时上传到阿里云 OSS（私有 Bucket + 签名 URL），
OSS_ENABLED=False 时回退到本地磁盘存储（开发环境）。
"""

import os
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request, Query
from app.config import settings
from app.utils.security import decode_access_token

router = APIRouter(prefix="/upload", tags=["文件上传"])


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
    # 限制文件大小 20MB
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小不能超过20MB")

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

    if settings.OSS_ENABLED:
        from app.services.oss_service import upload_and_sign
        result = upload_and_sign(
            data=contents,
            prefix="site_photos",
            user_id=user_id,
            filename=file.filename or "upload%s" % ext,
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
    else:
        # 本地存储（开发环境）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "%s_%s" % (timestamp, file.filename)

        upload_dir = os.path.join(settings.UPLOAD_DIR, "site_photos", user_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(contents)

        file_url = "/uploads/site_photos/%s/%s" % (user_id, safe_name)

        return {
            "url": file_url,
            "file_url": file_url,
            "filename": file.filename,
            "size": len(contents),
            "uploadedAt": datetime.now().isoformat(),
        }


@router.post("/file")
async def upload_generic_file(
    request: Request,
    file: UploadFile = File(...),
):
    """通用文件上传（支持图片、视频、文档，最大 50MB）

    用于承包商交付物上传等场景。
    """
    # 限制文件大小 50MB
    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小不能超过50MB")

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

    if settings.OSS_ENABLED:
        from app.services.oss_service import upload_and_sign
        result = upload_and_sign(
            data=contents,
            prefix="deliverables",
            user_id=user_id,
            filename=file.filename or "upload%s" % ext,
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
    else:
        # 本地存储（开发环境）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "%s_%s" % (timestamp, file.filename)

        upload_dir = os.path.join(settings.UPLOAD_DIR, "deliverables", user_id)
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(contents)

        file_url = "/uploads/deliverables/%s/%s" % (user_id, safe_name)

        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": file_url,
                "filename": file.filename,
                "size": len(contents),
                "mime_type": file.content_type or "",
                "uploadedAt": datetime.now().isoformat(),
            }
        }


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

    # 流式读取，限制 200MB
    max_size = 200 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=413, detail="视频文件大小不能超过200MB")

    user_id = _get_user_id_from_request(request)

    if settings.OSS_ENABLED:
        from app.services.oss_service import upload_and_sign
        result = upload_and_sign(
            data=contents,
            prefix="showcase_cases",
            user_id=user_id,
            filename=file.filename or "showcase%s" % ext,
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
    else:
        # 本地存储
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "%s_%s" % (timestamp, file.filename)
        upload_dir = os.path.join(settings.UPLOAD_DIR, "showcase_cases", user_id)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(contents)

        file_url = "/uploads/showcase_cases/%s/%s" % (user_id, safe_name)
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "url": file_url,
                "filename": file.filename,
                "size": len(contents),
                "mime_type": file.content_type or "video/mp4",
                "uploadedAt": datetime.now().isoformat(),
            }
        }
