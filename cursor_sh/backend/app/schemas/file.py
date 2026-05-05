"""文件相关 Schema"""

from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from app.models.file import FileType


class FileUpload(BaseModel):
    """文件上传模型"""
    id: str
    name: str
    size: int
    type: str  # MIME type
    uploadTime: str


class FileResponse(BaseModel):
    """文件响应模型"""
    id: str
    name: str
    size: int
    type: str  # MIME type
    uploadTime: str
    url: str
    object_key: Optional[str] = None  # OSS 对象路径（用于签名 URL 刷新）
    
    class Config:
        from_attributes = True

