"""用户画像 Memory — 管理员 API 端点

管理员可以：查看用户 Memory、编辑备忘录、查看客户列表
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order
from app.models.user_memory import UserMemory
from app.utils.dependencies import require_admin
from app.services import memory_service
from app.services.memory_sanitizer import (
    sanitize_agent_notes,
    sanitize_document_memory_data,
    sanitize_screen_resources,
)
from app.utils.timezone import beijing_iso

router = APIRouter(prefix="/admin/memory", tags=["管理员 — 用户画像"])


PROSPECT_PREFIX = "prospect_"


def _is_prospect_user_id(user_id: str) -> bool:
    return str(user_id or "").startswith(PROSPECT_PREFIX)


def _memory_status(memory: UserMemory | None) -> dict:
    if not memory:
        return {"hasCrawl": False, "hasMemory": False, "crawlStatus": "", "updatedAt": None}
    ci = memory.company_info or {}
    has_document_memory = ci.get("memory_source") == "document" or bool(
        ci.get("description") or ci.get("past_cases") or memory.screen_resources or memory.agent_notes
    )
    return {
        "hasCrawl": ci.get("crawl_status") == "success",
        "hasMemory": has_document_memory,
        "crawlStatus": ci.get("crawl_status", ""),
        "updatedAt": beijing_iso(memory.updated_at),
    }


def _prospect_company_info(
    company_name: str,
    contact_name: str = "",
    phone: str = "",
    email: str = "",
) -> dict:
    return {
        "name": company_name,
        "is_prospect": True,
        "memory_source": "prospect",
        "contact_name": contact_name,
        "phone": phone,
        "email": email,
    }


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
    """获取客户列表（含已注册客户和未注册预置客户）"""
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

    query = query.order_by(desc(User.created_at))
    result = await db.execute(query)
    rows = result.all()

    # 批量查 memory 状态
    user_ids = [r[0] for r in rows]
    memory_result = await db.execute(select(UserMemory).where(UserMemory.user_id.in_(user_ids))) if user_ids else None
    memory_map = {}
    if memory_result:
        for memory in memory_result.scalars().all():
            memory_map[memory.user_id] = _memory_status(memory)

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
            "customerType": "registered",
            "isProspect": False,
            "memory": memory_map.get(user_id, {"hasCrawl": False, "hasMemory": False, "crawlStatus": "", "updatedAt": None}),
            "_sortAt": r[6],
        })

    prospect_result = await db.execute(
        select(UserMemory)
        .where(UserMemory.user_id.like(f"{PROSPECT_PREFIX}%"))
        .order_by(desc(UserMemory.created_at))
    )
    prospects = prospect_result.scalars().all()
    for memory in prospects:
        ci = memory.company_info or {}
        company = ci.get("name") or ""
        contact_name = ci.get("contact_name") or ""
        phone = ci.get("phone") or ""
        email = ci.get("email") or ""
        if keyword:
            haystack = " ".join([company, contact_name, phone, email]).lower()
            if keyword.lower() not in haystack:
                continue
        items.append({
            "userId": memory.user_id,
            "username": contact_name or company or "未注册客户",
            "phone": phone,
            "email": email,
            "company": company,
            "createdAt": beijing_iso(memory.created_at),
            "orderCount": 0,
            "customerType": "prospect",
            "isProspect": True,
            "memory": _memory_status(memory),
            "_sortAt": memory.created_at,
        })

    items.sort(key=lambda item: item.get("_sortAt") or "", reverse=True)
    total = len(items)
    start = (page - 1) * pageSize
    page_items = items[start:start + pageSize]
    for item in page_items:
        item.pop("_sortAt", None)

    return {"code": 200, "data": {"data": page_items, "total": total}}


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


class CreateProspectRequest(BaseModel):
    company_name: str = ""
    contact_name: str = ""
    phone: str = ""
    email: str = ""
    agent_notes: str = ""


class UpdateCompanyNameRequest(BaseModel):
    company_name: str


async def _get_user_company(user_id: str, db: AsyncSession) -> str:
    """从用户表获取公司名称"""
    result = await db.execute(
        select(User.enterprise_name, User.company).where(User.id == user_id)
    )
    row = result.first()
    if row:
        return row.enterprise_name or row.company or ""
    if _is_prospect_user_id(user_id):
        memory = await memory_service.get_memory(user_id, db=db)
        if memory:
            return (memory.company_info or {}).get("name") or ""
    return ""


@router.post("/prospects")
async def create_prospect_memory(
    request: CreateProspectRequest,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建未注册客户的预置 Memory 档案。"""
    company_name = request.company_name.strip()
    contact_name = request.contact_name.strip()
    if not company_name and not contact_name:
        raise HTTPException(status_code=400, detail="请至少填写公司名称或联系人")

    prospect_id = f"{PROSPECT_PREFIX}{uuid.uuid4().hex[:16]}"
    memory = UserMemory(
        id=str(uuid.uuid4()),
        user_id=prospect_id,
        company_info=_prospect_company_info(
            company_name=company_name,
            contact_name=contact_name,
            phone=request.phone.strip(),
            email=request.email.strip(),
        ),
        screen_resources=[],
        project_preferences={},
        past_projects=[],
        interaction_stats={
            "total_sessions": 0,
            "first_contact": None,
            "last_contact": None,
        },
        agent_notes=request.agent_notes.strip(),
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)

    return {
        "code": 200,
        "data": {
            "userId": memory.user_id,
            "username": contact_name or company_name or "未注册客户",
            "phone": request.phone.strip(),
            "email": request.email.strip(),
            "company": company_name,
            "createdAt": beijing_iso(memory.created_at),
            "orderCount": 0,
            "customerType": "prospect",
            "isProspect": True,
            "memory": _memory_status(memory),
        },
        "message": "未注册客户 Memory 已创建",
    }


@router.put("/{user_id}/company-name")
async def update_company_name(
    user_id: str,
    request: UpdateCompanyNameRequest,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员手动修正 Memory 公司名称。"""
    company_name = request.company_name.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="公司名称不能为空")

    memory = await memory_service.get_or_create_memory(user_id, db=db)
    company_info = dict(memory.company_info or {})
    company_info["name"] = company_name
    if _is_prospect_user_id(user_id):
        company_info["is_prospect"] = True
        company_info.setdefault("memory_source", "prospect")
    memory.company_info = company_info
    await db.commit()

    return {"code": 200, "data": {"company_name": company_name}, "message": "公司名称已更新"}


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
            user_company=user_company or (memory.company_info or {}).get("name", ""),
            company_info=sanitize_document_memory_data(memory.company_info or {}),
            screen_resources=sanitize_screen_resources(memory.screen_resources or []),
            project_preferences=memory.project_preferences or {},
            past_projects=memory.past_projects or [],
            interaction_stats=memory.interaction_stats or {},
            agent_notes=sanitize_agent_notes(memory.agent_notes),
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
    await memory_service.update_memory(user_id, {"agent_notes": sanitize_agent_notes(request.agent_notes)})
    return {"code": 200, "data": None, "message": "备忘录已更新"}


@router.post("/{user_id}/crawl")
async def trigger_crawl(
    user_id: str,
    request: TriggerCrawlRequest,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """公司官网分析功能已下线。"""
    raise HTTPException(status_code=410, detail="官网分析功能已下线，请通过上传客户资料维护 Memory")


@router.delete("/{user_id}/crawl-cache")
async def clear_crawl_cache(
    user_id: str,
    current_admin=Depends(require_admin),
):
    """公司官网分析功能已下线。"""
    raise HTTPException(status_code=410, detail="官网分析功能已下线，无需清除爬取缓存")
