"""管理员端转人工客户队列 API。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ai_chat import AIChatMessage
from app.models.human_handoff import HANDOFF_STATUSES, HumanHandoff
from app.models.order import Order
from app.models.user import User
from app.schemas.response import ApiResponse
from app.utils.business_log import log_business_event
from app.utils.dependencies import AnyUser, require_admin
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_iso, beijing_now

router = APIRouter(prefix="/human-handoffs", tags=["转人工客户"])
logger = get_module_logger("ai")


class HandoffStatusUpdate(BaseModel):
    status: str


def _handoff_item(handoff: HumanHandoff, user: User | None, order: Order | None) -> dict:
    return {
        "id": handoff.id,
        "userId": handoff.user_id,
        "username": user.username if user else handoff.username,
        "phone": user.phone if user else "",
        "email": user.email if user else "",
        "company": (user.enterprise_name or user.company) if user else "",
        "sessionId": handoff.session_id,
        "draftOrderId": handoff.draft_order_id,
        "draftOrderNumber": order.order_number if order else "",
        "businessType": handoff.business_type,
        "status": handoff.status,
        "triggerMessage": handoff.trigger_message,
        "messageCount": handoff.message_count,
        "extractedData": handoff.extracted_data or {},
        "chatSnapshot": handoff.chat_snapshot or [],
        "createdAt": beijing_iso(handoff.created_at),
        "updatedAt": beijing_iso(handoff.updated_at),
        "followedAt": beijing_iso(handoff.followed_at),
    }


@router.get("")
async def list_handoffs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看转人工客户队列。"""
    query = (
        select(HumanHandoff, User, Order)
        .outerjoin(User, HumanHandoff.user_id == User.id)
        .outerjoin(Order, HumanHandoff.draft_order_id == Order.id)
    )

    if status:
        query = query.where(HumanHandoff.status == status)

    if keyword:
        kw = f"%{keyword}%"
        query = query.where(
            or_(
                HumanHandoff.username.ilike(kw),
                HumanHandoff.trigger_message.ilike(kw),
                User.username.ilike(kw),
                User.phone.ilike(kw),
                User.email.ilike(kw),
                User.company.ilike(kw),
                User.enterprise_name.ilike(kw),
                exists().where(
                    AIChatMessage.session_id == HumanHandoff.session_id,
                    AIChatMessage.content.ilike(kw),
                ),
            )
        )

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(
        query.order_by(desc(HumanHandoff.updated_at))
        .offset((page - 1) * pageSize)
        .limit(pageSize)
    )
    items = [_handoff_item(handoff, user, order) for handoff, user, order in result.all()]
    return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})


@router.get("/{handoff_id}")
async def get_handoff_detail(
    handoff_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看转人工客户详情。"""
    result = await db.execute(
        select(HumanHandoff, User, Order)
        .outerjoin(User, HumanHandoff.user_id == User.id)
        .outerjoin(Order, HumanHandoff.draft_order_id == Order.id)
        .where(HumanHandoff.id == handoff_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="转人工记录不存在")

    handoff, user, order = row
    return ApiResponse(code=200, message="获取成功", data=_handoff_item(handoff, user, order))


@router.put("/{handoff_id}/status")
async def update_handoff_status(
    handoff_id: str,
    payload: HandoffStatusUpdate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员更新跟进状态。"""
    if payload.status not in HANDOFF_STATUSES:
        raise HTTPException(status_code=400, detail="无效状态")

    result = await db.execute(select(HumanHandoff).where(HumanHandoff.id == handoff_id))
    handoff = result.scalar_one_or_none()
    if not handoff:
        raise HTTPException(status_code=404, detail="转人工记录不存在")

    old_status = handoff.status
    handoff.status = payload.status
    handoff.updated_at = beijing_now()
    handoff.followed_at = beijing_now() if payload.status == "followed" else None

    if handoff.draft_order_id:
        order_result = await db.execute(select(Order).where(Order.id == handoff.draft_order_id))
        order = order_result.scalar_one_or_none()
        if order:
            order_data = dict(order.order_data or {})
            order_data["handoff_status"] = payload.status
            order.order_data = order_data
            order.updated_at = beijing_now()

    await db.commit()
    await db.refresh(handoff)
    log_business_event(
        logger,
        "human_handoff_status_updated",
        admin_id=current_user.id,
        handoff_id=handoff.id,
        user_id=handoff.user_id,
        session_id=handoff.session_id,
        draft_order_id=handoff.draft_order_id,
        status_from=old_status,
        status_to=handoff.status,
    )
    return ApiResponse(code=200, message="更新成功", data={"id": handoff.id, "status": handoff.status})
