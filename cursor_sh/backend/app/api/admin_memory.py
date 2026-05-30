"""用户画像 Memory — 管理员 API 端点

管理员可以：查看用户 Memory、手动触发爬取、编辑备忘录、查看客户列表
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order
from app.models.user_memory import UserMemory
from app.utils.dependencies import require_admin
from app.services import memory_service
from app.utils.timezone import beijing_iso

router = APIRouter(prefix="/admin/memory", tags=["管理员 — 用户画像"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 客户列表（以客户为维度）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@router.get("/customers")
async def get_customer_list(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取客户列表（含订单数和画像状态）"""
    # 子查询：每个用户的订单数
    order_count_sub = (
        select(Order.user_id, func.count(Order.id).label("order_count"))
        .where(Order.user_id.isnot(None))
        .group_by(Order.user_id)
        .subquery()
    )

    # 主查询：只查 role='user' 的用户
    query = (
        select(
            User.id,
            User.username,
            User.phone,
            User.email,
            User.company,
            User.enterprise_name,
            User.created_at,
            func.coalesce(order_count_sub.c.order_count, 0).label("order_count"),
        )
        .outerjoin(order_count_sub, User.id == order_count_sub.c.user_id)
        .where(User.role == UserRole.USER)
    )

    if keyword:
        from sqlalchemy import or_
        query = query.where(
            or_(
                User.username.ilike(f"%{keyword}%"),
                User.phone.ilike(f"%{keyword}%"),
                User.company.ilike(f"%{keyword}%"),
                User.enterprise_name.ilike(f"%{keyword}%"),
            )
        )

    # 总数
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # 分页
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * pageSize).limit(pageSize)
    result = await db.execute(query)
    rows = result.all()

    # 批量查 memory 状态
    user_ids = [r[0] for r in rows]
    memory_result = await db.execute(
        select(UserMemory.user_id, UserMemory.company_info, UserMemory.updated_at)
        .where(UserMemory.user_id.in_(user_ids))
    )
    memory_map = {}
    for m in memory_result.all():
        ci = m[1] or {}
        memory_map[m[0]] = {
            "hasCrawl": ci.get("crawl_status") == "success",
            "crawlStatus": ci.get("crawl_status", ""),
            "updatedAt": beijing_iso(m[2]),
        }

    items = []
    for r in rows:
        user_id = r[0]
        items.append({
            "userId": user_id,
            "username": r[1],
            "phone": r[2],
            "email": r[3],
            "company": r[5] or r[4] or "",  # enterprise_name 优先
            "createdAt": beijing_iso(r[6]),
            "orderCount": r[7],
            "memory": memory_map.get(user_id, {"hasCrawl": False, "crawlStatus": "", "updatedAt": None}),
        })

    return {"code": 200, "data": {"data": items, "total": total}}


class MemoryResponse(BaseModel):
    user_id: str
    user_company: str = ""   # 用户注册的公司名
    company_info: dict = {}
    screen_resources: list = []
    project_preferences: dict = {}
    past_projects: list = []
    interaction_stats: dict = {}
    agent_notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateNotesRequest(BaseModel):
    agent_notes: str


class TriggerCrawlRequest(BaseModel):
    company_name: str = ""   # 可选，为空时自动从用户记录获取


async def _get_user_company(user_id: str, db: AsyncSession) -> str:
    """从用户表获取公司名称"""
    result = await db.execute(
        select(User.enterprise_name, User.company).where(User.id == user_id)
    )
    row = result.first()
    if row:
        return row.enterprise_name or row.company or ""
    return ""


@router.get("/{user_id}")
async def get_user_memory(
    user_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取指定用户的 Memory 画像"""
    memory = await memory_service.get_memory(user_id, db=db)
    user_company = await _get_user_company(user_id, db)

    if not memory:
        data = MemoryResponse(
            user_id=user_id,
            user_company=user_company,
            company_info={},
            screen_resources=[],
            project_preferences={},
            past_projects=[],
            interaction_stats={},
            agent_notes="",
        )
    else:
        data = MemoryResponse(
            user_id=memory.user_id,
            user_company=user_company,
            company_info=memory.company_info or {},
            screen_resources=memory.screen_resources or [],
            project_preferences=memory.project_preferences or {},
            past_projects=memory.past_projects or [],
            interaction_stats=memory.interaction_stats or {},
            agent_notes=memory.agent_notes or "",
            created_at=beijing_iso(memory.created_at),
            updated_at=beijing_iso(memory.updated_at),
        )

    return {"code": 200, "data": data.model_dump()}


@router.put("/{user_id}/notes")
async def update_agent_notes(
    user_id: str,
    request: UpdateNotesRequest,
    current_admin=Depends(require_admin),
):
    """管理员编辑 Agent 备忘录"""
    await memory_service.update_memory(user_id, {"agent_notes": request.agent_notes})
    return {"code": 200, "data": None, "message": "备忘录已更新"}


@router.post("/{user_id}/crawl")
async def trigger_crawl(
    user_id: str,
    request: TriggerCrawlRequest,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员手动触发公司官网爬取"""
    company_name = request.company_name.strip()

    # 如果未提供公司名，自动从用户记录获取
    if not company_name:
        company_name = await _get_user_company(user_id, db)

    if not company_name:
        raise HTTPException(status_code=400, detail="该用户未填写公司名称，请手动输入")

    # 确保 memory 记录存在
    await memory_service.get_or_create_memory(user_id)

    # 触发后台爬取
    await memory_service.trigger_crawl(user_id, company_name)

    return {"code": 200, "data": None, "message": f"已触发爬取: {company_name}，结果将在数秒后更新"}


@router.delete("/{user_id}/crawl-cache")
async def clear_crawl_cache(
    user_id: str,
    current_admin=Depends(require_admin),
):
    """清除用户的爬取缓存，允许重新爬取"""
    await memory_service.update_memory(user_id, {
        "company_info": {},
        "screen_resources": [],
    })
    return {"code": 200, "data": None, "message": "爬取缓存已清除"}
