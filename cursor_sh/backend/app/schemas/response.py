"""通用响应模型"""

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    code: int = 200
    message: str = "操作成功"
    data: Optional[T] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "操作成功",
                "data": None
            }
        }

