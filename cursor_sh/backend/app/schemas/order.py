"""订单相关 Schema"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from app.models.order import OrderType, OrderStatus
from app.schemas.file import FileUpload, FileResponse
from app.schemas.feedback import FeedbackResponse


# ========== 订单创建请求 ==========

class VideoPurchaseOrderCreate(BaseModel):
    """裸眼3D成片购买订单创建"""
    orderType: str = Field(default="video_purchase")
    industryType: str
    customIndustry: Optional[str] = None
    visualStyle: str
    customStyle: Optional[str] = None
    duration: int
    priceRange: Dict[str, float]
    resolution: str
    size: str
    curvature: Optional[str] = None


class AI3DCustomOrderCreate(BaseModel):
    """AI裸眼3D定制订单创建"""
    orderType: str = Field(default="ai_3d_custom")
    brand: Optional[str] = None
    background: Optional[str] = None
    target_group: Optional[str] = None
    brand_tone: Optional[str] = None
    content: Optional[str] = None
    style: Optional[str] = None
    prohibited_content: Optional[str] = None
    city: Optional[str] = None
    media_size: Optional[str] = None
    time_number: Optional[str] = None
    technology: Optional[str] = None
    budget: Optional[str] = None
    online_time: Optional[str] = None
    sales_contact: Optional[str] = None
    scenePhotos: Optional[List[FileUpload]] = []


class DigitalArtOrderCreate(BaseModel):
    """数字艺术订单创建"""
    orderType: str = Field(default="digital_art")
    artDirection: str
    customDirection: Optional[str] = None
    description: str
    materials: List[FileUpload]


# ========== 订单响应 ==========

class BaseOrderResponse(BaseModel):
    """基础订单响应"""
    id: str
    orderNumber: str
    orderType: OrderType
    status: OrderStatus
    userId: str
    userName: Optional[str] = None
    assignees: List[Dict[str, str]] = []  # 格式: [{"id": "...", "name": "..."}]
    createdAt: datetime
    updatedAt: datetime
    feedbacks: List[FeedbackResponse] = []
    revisionCount: int
    pendingReviewPreviewIds: List[str] = []
    
    class Config:
        from_attributes = True


class VideoPurchaseOrderResponse(BaseOrderResponse):
    """裸眼3D成片购买订单响应"""
    industryType: str
    customIndustry: Optional[str] = None
    visualStyle: str
    customStyle: Optional[str] = None
    duration: int
    priceRange: Dict[str, float]
    resolution: str
    size: str
    curvature: Optional[str] = None


class AI3DCustomOrderResponse(BaseOrderResponse):
    """AI裸眼3D定制订单响应"""
    brand: Optional[str] = None
    background: Optional[str] = None
    target_group: Optional[str] = None
    brand_tone: Optional[str] = None
    content: Optional[str] = None
    style: Optional[str] = None
    prohibited_content: Optional[str] = None
    city: Optional[str] = None
    media_size: Optional[str] = None
    time_number: Optional[str] = None
    technology: Optional[str] = None
    budget: Optional[str] = None
    online_time: Optional[str] = None
    sales_contact: Optional[str] = None
    scenePhotos: List[FileResponse] = []
    previewFiles: Optional[List[FileResponse]] = []


class DigitalArtOrderResponse(BaseOrderResponse):
    """数字艺术订单响应"""
    artDirection: str
    customDirection: Optional[str] = None
    description: str
    materials: List[FileResponse] = []
    previewFiles: Optional[List[FileResponse]] = []


# ========== 其他请求 ==========

class OrderStatusUpdate(BaseModel):
    """订单状态更新"""
    status: OrderStatus


class OrderAssign(BaseModel):
    """订单分配"""
    assigneeIds: List[str]
    assigneeNames: List[str]


class PreviewUpload(BaseModel):
    """预览文件上传"""
    files: List[FileUpload]
    note: Optional[str] = None  # 备注说明，会展示给用户
    previewType: Literal["initial", "final"] = "initial"


class PreviewReview(BaseModel):
    """预览审核请求"""
    previewId: str
    action: Literal["approve", "reject"]
    note: Optional[str] = None


class ContractAdvance(BaseModel):
    """合同与付款推进请求（管理员操作）"""
    contractNumber: str  # 合同编号
    paymentAmount: float  # 首付款金额
    note: Optional[str] = None  # 备注


class AdminCancelOrder(BaseModel):
    """管理员取消订单请求（需 SMS 验证）"""
    phone: str
    smsCode: str
    reason: Optional[str] = None  # 取消原因

