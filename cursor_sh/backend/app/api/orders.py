"""订单 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Union

from app.database import get_db
from app.models.user import User
from app.models.order import OrderType, OrderStatus
from app.schemas.order import *
from app.schemas.feedback import FeedbackCreate
from app.schemas.response import ApiResponse
from app.services.order_service import OrderService
from app.utils.dependencies import get_current_user, require_admin, require_admin_or_staff

router = APIRouter(prefix="/orders", tags=["订单"])


@router.get("", response_model=ApiResponse[List[dict]])
async def get_orders(
    user_id: Optional[str] = Query(None),
    order_type: Optional[OrderType] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    assignee_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取订单列表"""
    try:
        orders = await OrderService.get_orders(
            db, current_user, user_id, order_type, status, assignee_id
        )
        return ApiResponse(code=200, message="获取成功", data=orders)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ApiResponse[dict])
async def create_order(
    order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate, DigitalArtOrderCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建订单"""
    try:
        order = await OrderService.create_order(db, order_data, current_user)
        
        # 根据订单类型返回不同的提示消息
        messages = {
            "video_purchase": "订单创建成功",
            "ai_3d_custom": "订单创建成功，预计5-7个工作日完成制作",
            "digital_art": "订单创建成功，预计3个工作日交付初稿"
        }
        message = messages.get(order_data.orderType, "订单创建成功")
        
        return ApiResponse(code=201, message=message, data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{order_id}", response_model=ApiResponse[dict])
async def get_order_detail(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取订单详情"""
    try:
        order = await OrderService.get_order_detail(db, order_id, current_user)
        return ApiResponse(code=200, message="获取成功", data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{order_id}", response_model=ApiResponse[dict])
async def update_order(
    order_id: str,
    order_data: Union[VideoPurchaseOrderCreate, AI3DCustomOrderCreate, DigitalArtOrderCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改订单（仅待分配状态可修改）"""
    try:
        order = await OrderService.update_order(db, order_id, order_data, current_user)
        return ApiResponse(code=200, message="订单修改成功", data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{order_id}/status", response_model=ApiResponse[dict])
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    current_user: User = Depends(require_admin_or_staff),
    db: AsyncSession = Depends(get_db)
):
    """更新订单状态"""
    try:
        order = await OrderService.update_order_status(
            db, order_id, status_update.status, current_user
        )
        return ApiResponse(code=200, message="状态更新成功", data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{order_id}/assign", response_model=ApiResponse[dict])
async def assign_order(
    order_id: str,
    assign_data: OrderAssign,
    current_user: User = Depends(require_admin_or_staff),
    db: AsyncSession = Depends(get_db)
):
    """分配订单负责人"""
    try:
        order = await OrderService.assign_order(
            db, order_id, assign_data.assigneeIds, assign_data.assigneeNames, current_user
        )
        return ApiResponse(code=200, message="负责人分配成功", data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{order_id}/preview", response_model=ApiResponse[dict])
async def upload_preview(
    order_id: str,
    preview_data: PreviewUpload,
    current_user: User = Depends(require_admin_or_staff),
    db: AsyncSession = Depends(get_db)
):
    """上传预览文件"""
    try:
        order = await OrderService.upload_preview(
            db, order_id, preview_data.files, preview_data.note, preview_data.previewType, current_user
        )
        return ApiResponse(code=200, message="预览文件上传成功", data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{order_id}/preview/review", response_model=ApiResponse[dict])
async def review_preview(
    order_id: str,
    review_data: PreviewReview,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """审核预览文件"""
    try:
        order = await OrderService.review_preview(db, order_id, review_data, current_user)
        return ApiResponse(code=200, message="预览审核完成", data=order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{order_id}/feedback", response_model=ApiResponse[dict])
async def submit_feedback(
    order_id: str,
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """提交订单反馈"""
    try:
        feedback = await OrderService.submit_feedback(
            db, order_id, feedback_data, current_user
        )
        return ApiResponse(code=200, message="反馈提交成功", data=feedback)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

