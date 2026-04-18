"""文件相关 Schema"""

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
    
    class Config:
        from_attributes = True

