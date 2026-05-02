"""用户画像 Memory — 管理员 API 端点

管理员可以：查看用户 Memory、手动触发爬取、编辑备忘录
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.utils.dependencies import require_admin
from app.services import memory_service

router = APIRouter(prefix="/admin/memory", tags=["管理员 — 用户画像"])


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


@router.get("/{user_id}", response_model=MemoryResponse)
async def get_user_memory(
    user_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取指定用户的 Memory 画像"""
    memory = await memory_service.get_memory(user_id, db=db)
    user_company = await _get_user_company(user_id, db)

    if not memory:
        return MemoryResponse(
            user_id=user_id,
            user_company=user_company,
            company_info={},
            screen_resources=[],
            project_preferences={},
            past_projects=[],
            interaction_stats={},
            agent_notes="",
        )

    return MemoryResponse(
        user_id=memory.user_id,
        user_company=user_company,
        company_info=memory.company_info or {},
        screen_resources=memory.screen_resources or [],
        project_preferences=memory.project_preferences or {},
        past_projects=memory.past_projects or [],
        interaction_stats=memory.interaction_stats or {},
        agent_notes=memory.agent_notes or "",
        created_at=memory.created_at.isoformat() if memory.created_at else None,
        updated_at=memory.updated_at.isoformat() if memory.updated_at else None,
    )


@router.put("/{user_id}/notes")
async def update_agent_notes(
    user_id: str,
    request: UpdateNotesRequest,
    current_admin=Depends(require_admin),
):
    """管理员编辑 Agent 备忘录"""
    await memory_service.update_memory(user_id, {"agent_notes": request.agent_notes})
    return {"message": "备忘录已更新"}


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

    return {"message": f"已触发爬取: {company_name}，结果将在数秒后更新"}


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
    return {"message": "爬取缓存已清除"}

