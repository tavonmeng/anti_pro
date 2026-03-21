"""负责人 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order, OrderAssignee
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.schemas.response import ApiResponse
from app.utils.dependencies import get_current_user, require_admin
from app.utils.security import get_password_hash
from app.utils.validators import generate_id

router = APIRouter(prefix="/staff", tags=["负责人"])


@router.get("")
async def get_staff_list(
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色筛选"),
    isActive: Optional[bool] = Query(None, description="状态筛选"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取负责人列表（支持分页和筛选）"""
    try:
        # 构建查询条件
        query = select(User).where(
            User.role.in_([UserRole.STAFF, UserRole.ADMIN])
        )
        
        # 关键词搜索
        if keyword:
            query = query.where(
                or_(
                    User.username.ilike(f"%{keyword}%"),
                    User.real_name.ilike(f"%{keyword}%"),
                    User.email.ilike(f"%{keyword}%")
                )
            )
        
        # 角色筛选
        if role:
            try:
                role_enum = UserRole(role)
                query = query.where(User.role == role_enum)
            except ValueError:
                pass
        
        # 状态筛选
        if isActive is not None:
            query = query.where(User.is_active == isActive)
        
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
                "realName": staff.real_name,
                "role": staff.role.value,
                "isActive": staff.is_active,
                "orderCount": order_count,
                "createdAt": staff.created_at.isoformat() if staff.created_at else None,
                "updatedAt": staff.updated_at.isoformat() if staff.updated_at else None
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def add_staff(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """添加负责人"""
    try:
        # 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=409, detail="用户名已存在")
        
        # 验证角色
        if user_data.role not in ["admin", "staff"]:
            raise HTTPException(status_code=400, detail="角色必须是 admin 或 staff")
        
        # 创建负责人账户
        new_staff = User(
            id=generate_id("user"),
            username=user_data.username,
            email=user_data.email,
            real_name=user_data.realName,
            password_hash=get_password_hash(user_data.password),
            role=UserRole(user_data.role),
            is_active=user_data.isActive if user_data.isActive is not None else True
        )
        
        db.add(new_staff)
        await db.commit()
        await db.refresh(new_staff)
        
        staff_response = {
            "id": new_staff.id,
            "username": new_staff.username,
            "email": new_staff.email,
            "realName": new_staff.real_name,
            "role": new_staff.role.value,
            "isActive": new_staff.is_active,
            "orderCount": 0,
            "createdAt": new_staff.created_at.isoformat() if new_staff.created_at else None
        }
        
        return ApiResponse(code=201, message="负责人添加成功", data=staff_response)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{staff_id}")
async def update_staff(
    staff_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """更新负责人信息"""
    try:
        # 查询负责人
        result = await db.execute(
            select(User).where(User.id == staff_id)
        )
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(status_code=404, detail="负责人不存在")
        
        # 更新字段
        if user_data.email is not None:
            staff.email = user_data.email
        if user_data.realName is not None:
            staff.real_name = user_data.realName
        if user_data.role is not None:
            if user_data.role not in ["admin", "staff"]:
                raise HTTPException(status_code=400, detail="角色必须是 admin 或 staff")
            staff.role = UserRole(user_data.role)
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
            "realName": staff.real_name,
            "role": staff.role.value,
            "isActive": staff.is_active,
            "orderCount": order_count,
            "createdAt": staff.created_at.isoformat() if staff.created_at else None,
            "updatedAt": staff.updated_at.isoformat() if staff.updated_at else None
        }
        
        return ApiResponse(code=200, message="更新成功", data=staff_response)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{staff_id}")
async def delete_staff(
    staff_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """删除负责人"""
    try:
        # 查询负责人
        result = await db.execute(
            select(User).where(User.id == staff_id)
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
        raise HTTPException(status_code=500, detail=str(e))

