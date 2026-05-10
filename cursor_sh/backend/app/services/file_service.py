"""文件服务"""

import os
import aiofiles
from typing import List
from fastapi import UploadFile, HTTPException
from datetime import datetime

from app.config import settings
from app.utils.validators import validate_file_size, validate_file_type, generate_id
from app.schemas.file import FileUpload, FileResponse

UPLOAD_CHUNK_SIZE = 1024 * 1024


async def _stream_file_to_temp(file: UploadFile) -> tuple[str, int]:
    tmp_dir = os.path.join(settings.UPLOAD_DIR, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    file_id = generate_id("tmp")
    extension = os.path.splitext(os.path.basename(file.filename or ""))[1]
    tmp_path = os.path.join(tmp_dir, "%s%s.part" % (file_id, extension))
    size = 0

    try:
        async with aiofiles.open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                validate_file_size(size)
                await out.write(chunk)
        return tmp_path, size
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _cleanup_temp_file(tmp_path: str):
    if not tmp_path:
        return
    try:
        os.remove(tmp_path)
    except OSError:
        pass


class FileService:
    """文件服务类"""
    
    @staticmethod
    async def save_file_local(file: UploadFile, order_id: str) -> FileResponse:
        """保存文件到本地"""
        # 验证文件
        validate_file_type(file.content_type)
        
        # 生成文件 ID 和路径
        file_id = generate_id("file")
        upload_dir = os.path.join(settings.UPLOAD_DIR, order_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        file_extension = os.path.splitext(file.filename or "")[1]
        file_name = f"{file_id}{file_extension}"
        file_path = os.path.join(upload_dir, file_name)

        tmp_path, file_size = await _stream_file_to_temp(file)
        try:
            os.replace(tmp_path, file_path)
            tmp_path = ""
        finally:
            _cleanup_temp_file(tmp_path)
        
        # 构造文件 URL（相对路径）
        file_url = f"/uploads/{order_id}/{file_name}"
        
        return FileResponse(
            id=file_id,
            name=file.filename,
            size=file_size,
            type=file.content_type,
            uploadTime=datetime.utcnow().isoformat() + "Z",
            url=file_url
        )
    
    @staticmethod
    async def save_file_oss(file: UploadFile, order_id: str) -> FileResponse:
        """保存文件到阿里云 OSS（私有 Bucket + 签名 URL）"""
        from app.services.oss_service import upload_file_and_sign

        # 验证文件
        validate_file_type(file.content_type)

        file_id = generate_id("file")
        file_extension = os.path.splitext(file.filename or "")[1]
        filename = "%s%s" % (file_id, file_extension)

        tmp_path, file_size = await _stream_file_to_temp(file)
        try:
            result = upload_file_and_sign(
                file_path=tmp_path,
                prefix="orders/%s" % order_id,
                user_id="",  # 订单附件不按用户分目录
                filename=filename,
                content_type=file.content_type or "",
            )
        finally:
            _cleanup_temp_file(tmp_path)

        return FileResponse(
            id=file_id,
            name=file.filename,
            size=file_size,
            type=file.content_type,
            uploadTime=datetime.utcnow().isoformat() + "Z",
            url=result["url"],
            object_key=result.get("object_key", ""),
        )
    
    @staticmethod
    async def save_files(files: List[UploadFile], order_id: str) -> List[FileResponse]:
        """批量保存文件"""
        saved_files = []
        
        for file in files:
            if settings.OSS_ENABLED:
                file_response = await FileService.save_file_oss(file, order_id)
            else:
                file_response = await FileService.save_file_local(file, order_id)
            
            saved_files.append(file_response)
        
        return saved_files
    
    @staticmethod
    def convert_file_upload_to_response(file_upload, order_id: str) -> FileResponse:
        """将 FileUpload 转换为 FileResponse（用于前端已上传的文件）"""
        # 前端模拟上传的文件，这里只是记录元数据
        # 实际文件需要后续通过 API 上传
        # 支持字典和 FileUpload 对象两种输入
        if isinstance(file_upload, dict):
            # 如果是字典，直接使用字典的值
            file_id = file_upload.get('id')
            file_name = file_upload.get('name')
            file_size = file_upload.get('size')
            file_type = file_upload.get('type')
            upload_time = file_upload.get('uploadTime')
            # 优先使用前端传入的 URL（可能是 OSS 签名 URL 或本地路径）
            existing_url = file_upload.get('url') or file_upload.get('file_url')
            object_key = file_upload.get('object_key')
        else:
            # 如果是 FileUpload 对象
            file_id = file_upload.id
            file_name = file_upload.name
            file_size = file_upload.size
            file_type = file_upload.type
            upload_time = file_upload.uploadTime
            existing_url = file_upload.url or file_upload.file_url
            object_key = file_upload.object_key
        
        # 使用已有的 URL（来自之前的上传接口），否则生成本地路径
        file_url = existing_url or "/uploads/%s/%s" % (order_id, file_name)
        
        return FileResponse(
            id=file_id,
            name=file_name,
            size=file_size,
            type=file_type,
            uploadTime=upload_time,
            url=file_url,
            object_key=object_key,
        )
