"""
文件上传 — 通用上传接口
支持现场实拍图、参考文件等上传
"""

import os
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
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
    allowed_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.pdf', '.doc', '.docx', '.zip'}
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # 构建存储路径
    user_id = _get_user_id_from_request(request)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{file.filename}"

    upload_dir = os.path.join(settings.UPLOAD_DIR, "site_photos", user_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/site_photos/{user_id}/{safe_name}"

    return {
        "url": file_url,
        "file_url": file_url,
        "filename": file.filename,
        "size": len(contents),
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
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    # 构建存储路径
    user_id = _get_user_id_from_request(request)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{file.filename}"

    upload_dir = os.path.join(settings.UPLOAD_DIR, "deliverables", user_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/deliverables/{user_id}/{safe_name}"

    return {
        "code": 200,
        "message": "上传成功",
        "data": {
            "url": file_url,
            "filename": file.filename,
            "size": len(contents),
            "mime_type": file.content_type or "",
        }
    }
