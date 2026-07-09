"""负责人 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

from app.database import get_db
from app.models.admin import Admin
from app.models.contractor import Contractor
from app.models.user import UserRole
from app.models.staff_member import StaffMember
from app.models.order import Order, OrderAssignee
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.response import ApiResponse
from app.services.staff_phone_service import validate_staff_phone_for_active_staff
from app.utils.dependencies import get_current_user, require_admin, AnyUser
from app.utils.security import get_password_hash
from app.utils.validators import generate_id
from app.utils.timezone import beijing_iso

router = APIRouter(prefix="/staff", tags=["负责人"])


async def _ensure_staff_phone_unique(
    db: AsyncSession,
    phone: Optional[str],
    exclude_staff_id: Optional[str] = None
) -> None:
    if not phone:
        return

    staff_query = select(StaffMember).where(StaffMember.phone == phone)
    if exclude_staff_id:
        staff_query = staff_query.where(StaffMember.id != exclude_staff_id)
    staff_result = await db.execute(staff_query)
    if staff_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="手机号已被其他负责人使用")

    admin_result = await db.execute(select(Admin).where(Admin.phone == phone))
    if admin_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="手机号已被管理员使用")

    contractor_result = await db.execute(select(Contractor).where(Contractor.phone == phone))
    if contractor_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="手机号已被承包商使用")


@router.get("")
async def get_staff_list(
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色筛选"),
    isActive: Optional[bool] = Query(None, description="状态筛选"),
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取负责人列表（从 staff_members 表查询）"""
    try:
        # 只查 staff_members 表
        query = select(StaffMember)
        
        # 关键词搜索
        if keyword:
            query = query.where(
                or_(
                    StaffMember.username.ilike(f"%{keyword}%"),
                    StaffMember.real_name.ilike(f"%{keyword}%"),
                    StaffMember.email.ilike(f"%{keyword}%"),
                    StaffMember.phone.ilike(f"%{keyword}%")
                )
            )
        
        # 状态筛选
        if isActive is not None:
            query = query.where(StaffMember.is_active == isActive)
        
        # 查询总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        query = query.offset((page - 1) * pageSize).limit(pageSize)
        result = await db.execute(query)
        staff_list = result.scalars().all()
        
        # 统计每个负责人的订单数
        staff_with_count = []
        for staff in staff_list:
            # 查询该负责人负责的订单数
            order_count_query = select(func.count(Order.id)).select_from(
                Order
            ).join(
                OrderAssignee, Order.id == OrderAssignee.order_id
            ).where(
                OrderAssignee.assignee_id == staff.id,
                Order.status != "completed",
                Order.status != "cancelled"
            )
            order_count_result = await db.execute(order_count_query)
            order_count = order_count_result.scalar()
            
            staff_dict = {
                "id": staff.id,
                "username": staff.username,
                "email": staff.email,
                "phone": staff.phone,
                "realName": staff.real_name,
                "role": "staff",
                "isActive": staff.is_active,
                "orderCount": order_count,
                "createdAt": beijing_iso(staff.created_at),
                "updatedAt": beijing_iso(staff.updated_at)
            }
            staff_with_count.append(staff_dict)
        
        return ApiResponse(
            code=200, 
            message="获取成功", 
            data={
                "data": staff_with_count,
                "total": total
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.post("")
async def add_staff(
    user_data: UserCreate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """添加负责人（创建到 staff_members 表）"""
    try:
        # 检查用户名是否已存在（在 staff_members 表中）
        result = await db.execute(
            select(StaffMember).where(StaffMember.username == user_data.username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=409, detail="用户名已存在")
        
        is_active = user_data.isActive if user_data.isActive is not None else True
        phone = validate_staff_phone_for_active_staff(user_data.phone, is_active=is_active)
        await _ensure_staff_phone_unique(db, phone)

        # 创建负责人账户（到 staff_members 表）
        new_staff = StaffMember(
            id=generate_id("staff"),
            username=user_data.username,
            email=user_data.email,
            phone=phone,
            real_name=user_data.realName,
            password_hash=get_password_hash(user_data.password),
            is_active=is_active
        )
        
        db.add(new_staff)
        await db.commit()
        await db.refresh(new_staff)
        
        staff_response = {
            "id": new_staff.id,
            "username": new_staff.username,
            "email": new_staff.email,
            "phone": new_staff.phone,
            "realName": new_staff.real_name,
            "role": "staff",
            "isActive": new_staff.is_active,
            "orderCount": 0,
            "createdAt": beijing_iso(new_staff.created_at)
        }
        
        return ApiResponse(code=201, message="负责人添加成功", data=staff_response)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.put("/{staff_id}")
async def update_staff(
    staff_id: str,
    user_data: UserUpdate,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新负责人信息"""
    try:
        # 查询负责人（从 staff_members 表）
        result = await db.execute(
            select(StaffMember).where(StaffMember.id == staff_id)
        )
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(status_code=404, detail="负责人不存在")
        
        next_is_active = user_data.isActive if user_data.isActive is not None else staff.is_active
        next_phone = user_data.phone if user_data.phone is not None else staff.phone
        normalized_phone = validate_staff_phone_for_active_staff(next_phone, is_active=next_is_active)
        await _ensure_staff_phone_unique(db, normalized_phone, exclude_staff_id=staff.id)

        # 更新字段
        if user_data.email is not None:
            staff.email = user_data.email
        if user_data.phone is not None:
            staff.phone = normalized_phone
        if user_data.realName is not None:
            staff.real_name = user_data.realName
        if user_data.isActive is not None:
            staff.is_active = user_data.isActive
        
        await db.commit()
        await db.refresh(staff)
        
        # 查询订单数
        order_count_query = select(func.count(Order.id)).select_from(
            Order
        ).join(
            OrderAssignee, Order.id == OrderAssignee.order_id
        ).where(
            OrderAssignee.assignee_id == staff.id,
            Order.status != "completed",
            Order.status != "cancelled"
        )
        order_count_result = await db.execute(order_count_query)
        order_count = order_count_result.scalar()
        
        staff_response = {
            "id": staff.id,
            "username": staff.username,
            "email": staff.email,
            "phone": staff.phone,
            "realName": staff.real_name,
            "role": "staff",
            "isActive": staff.is_active,
            "orderCount": order_count,
            "createdAt": beijing_iso(staff.created_at),
            "updatedAt": beijing_iso(staff.updated_at)
        }
        
        return ApiResponse(code=200, message="更新成功", data=staff_response)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.delete("/{staff_id}")
async def delete_staff(
    staff_id: str,
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除负责人"""
    try:
        # 查询负责人
        result = await db.execute(
            select(StaffMember).where(StaffMember.id == staff_id)
        )
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(status_code=404, detail="负责人不存在")
        
        # 检查是否有进行中的订单
        order_count_query = select(func.count(Order.id)).select_from(
            Order
        ).join(
            OrderAssignee, Order.id == OrderAssignee.order_id
        ).where(
            OrderAssignee.assignee_id == staff.id,
            Order.status != "completed",
            Order.status != "cancelled"
        )
        order_count_result = await db.execute(order_count_query)
        order_count = order_count_result.scalar()
        
        if order_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"该负责人还有 {order_count} 个进行中的订单，无法删除"
            )
        
        # 删除负责人
        await db.delete(staff)
        await db.commit()
        
        return ApiResponse(code=200, message="删除成功", data=None)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e
