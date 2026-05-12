"""用户画像 Memory — 管理员 API 端点

管理员可以：查看用户 Memory、手动触发爬取、编辑备忘录、查看客户列表
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timezone
import asyncio
import os
import uuid

from app.database import get_db
from app.models.user import User, UserRole
from app.models.order import Order
from app.models.user_memory import UserMemory
from app.utils.dependencies import require_admin
from app.services import memory_service
from app.services.company_profile_service import (
    attach_company_profile_to_user_by_key,
    create_company_library_document,
    create_company_profile_ingest_job,
    get_company_library_document,
    get_company_profile_by_key,
    list_company_library_documents,
    list_company_profile_ingest_jobs,
    list_company_profiles,
    update_company_profile,
)
from app.services.company_library_storage import sign_company_library_asset, store_company_library_asset

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
        docs = ci.get("customer_documents") or []
        has_document_profile = any(d.get("ingest_status") == "success" for d in docs)
        memory_map[m[0]] = {
            "hasCrawl": ci.get("crawl_status") == "success" or has_document_profile,
            "crawlStatus": ci.get("crawl_status", ""),
            "updatedAt": m[2].isoformat() if m[2] else None,
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
            "createdAt": r[6].isoformat() if r[6] else None,
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


class UpdateCompanyProfileRequest(BaseModel):
    company_name: Optional[str] = None
    profile_data: Optional[dict] = None
    screen_resources: Optional[list] = None
    notes: Optional[str] = None


class AttachCompanyProfileRequest(BaseModel):
    user_id: str


@router.get("/company-profiles")
async def get_company_profiles(
    current_admin=Depends(require_admin),
):
    """获取已 ingest 的公司资料库列表。"""
    profiles = await list_company_profiles(limit=100)
    items = []
    for p in profiles:
        items.append({
            "id": p.id,
            "company_key": p.company_key,
            "company_name": p.company_name,
            "brief": (p.profile_data or {}).get("brief", ""),
            "document_count": len(p.documents or []),
            "screen_count": len(p.screen_resources or []),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })
    return {"code": 200, "data": items}


def _serialize_company_profile(profile):
    documents = []
    for doc in profile.documents or []:
        item = dict(doc or {})
        assets = item.get("assets") or {}
        item["assets"] = {
            "raw_file": sign_company_library_asset(assets.get("raw_file")),
            "extracted_text": sign_company_library_asset(assets.get("extracted_text")),
            "structured_memory": sign_company_library_asset(assets.get("structured_memory")),
        }
        documents.append(item)
    return {
        "id": profile.id,
        "company_key": profile.company_key,
        "company_name": profile.company_name,
        "profile_data": profile.profile_data or {},
        "screen_resources": profile.screen_resources or [],
        "documents": documents,
        "notes": profile.notes or "",
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _serialize_company_library_document(document):
    return {
        "id": document.id,
        "filename": document.filename,
        "source": document.source,
        "status": document.status,
        "error": document.error or "",
        "company_key": document.company_key or "",
        "company_name": document.company_name or "",
        "file_size": document.file_size or "",
        "mime_type": document.mime_type or "",
        "page_count": document.page_count or "",
        "text_chars": document.text_chars or "",
        "raw_file": sign_company_library_asset(document.raw_file or {}),
        "extracted_text": sign_company_library_asset(document.extracted_text or {}),
        "structured_memory": sign_company_library_asset(document.structured_memory or {}),
        "text_preview": document.text_preview or "",
        "notes": document.notes or "",
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }


@router.get("/company-library/documents")
async def get_company_library_documents(
    current_admin=Depends(require_admin),
):
    """获取公司资料库中的原始资料、解析文本、结构化 memory 资产。"""
    documents = await list_company_library_documents(limit=100)
    return {"code": 200, "data": [_serialize_company_library_document(item) for item in documents]}


@router.get("/company-library/documents/{document_id}")
async def get_company_library_document_detail(
    document_id: str,
    current_admin=Depends(require_admin),
):
    document = await get_company_library_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="公司资料不存在")
    return {"code": 200, "data": _serialize_company_library_document(document)}


@router.get("/company-profiles/ingest-jobs")
async def get_company_profile_ingest_jobs(
    current_admin=Depends(require_admin),
):
    """获取最近的公司资料 ingest 任务。"""
    jobs = await list_company_profile_ingest_jobs(limit=20)
    items = []
    for job in jobs:
        items.append({
            "id": job.id,
            "filename": job.filename,
            "status": job.status,
            "error": job.error or "",
            "company_key": job.company_key or "",
            "company_name": job.company_name or "",
            "file_size": job.file_size or "",
            "mime_type": job.mime_type or "",
            "page_count": job.page_count or "",
            "text_chars": job.text_chars or "",
            "result": job.result or {},
            "queued_at": job.queued_at.isoformat() if job.queued_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        })
    return {"code": 200, "data": items}


@router.get("/company-profiles/{company_key}")
async def get_company_profile_detail(
    company_key: str,
    current_admin=Depends(require_admin),
):
    """获取某个公司资料库画像详情。"""
    profile = await get_company_profile_by_key(company_key)
    if not profile:
        raise HTTPException(status_code=404, detail="公司资料不存在")

    return {"code": 200, "data": _serialize_company_profile(profile)}


@router.put("/company-profiles/{company_key}")
async def update_company_profile_detail(
    company_key: str,
    request: UpdateCompanyProfileRequest,
    current_admin=Depends(require_admin),
):
    """管理员编辑已解析的公司资料和备注。"""
    updates = request.model_dump(exclude_unset=True)
    profile = await update_company_profile(company_key, updates)
    if not profile:
        raise HTTPException(status_code=404, detail="公司资料不存在")
    return {"code": 200, "data": _serialize_company_profile(profile), "message": "公司资料已更新"}


@router.post("/company-profiles/{company_key}/attach-user")
async def attach_company_profile_to_registered_user(
    company_key: str,
    request: AttachCompanyProfileRequest,
    current_admin=Depends(require_admin),
):
    """管理员手动把公司资料关联到某个已注册用户。"""
    ok, message = await attach_company_profile_to_user_by_key(company_key, request.user_id)
    if not ok:
        raise HTTPException(status_code=404, detail=message)
    profile = await get_company_profile_by_key(company_key)
    return {"code": 200, "data": _serialize_company_profile(profile), "message": message}


@router.post("/company-profiles/ingest")
async def upload_company_profile_document(
    file: UploadFile = File(...),
    current_admin=Depends(require_admin),
):
    """管理员全局上传公司资料，自动识别公司名并归档。

    不要求客户已注册。客户注册/填写公司名后会按公司名匹配到 Agent Memory。
    """
    filename = file.filename or "company_document"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".pdf", ".pptx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="仅支持 PDF/PPTX/TXT/MD 公司资料")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小不能超过50MB")

    document_id = str(uuid.uuid4())
    raw_file = store_company_library_asset(
        document_id=document_id,
        stage="raw",
        filename=filename,
        data=contents,
        content_type=file.content_type or "application/octet-stream",
    )
    await create_company_library_document(
        document_id=document_id,
        filename=filename,
        file_size=len(contents),
        mime_type=file.content_type or "",
        raw_file=raw_file,
    )
    await create_company_profile_ingest_job(
        document_id=document_id,
        filename=filename,
        file_size=len(contents),
        mime_type=file.content_type or "",
        result={"stage": "queued", "raw_file": raw_file},
    )

    from app.services.document_ingest_service import ingest_company_document_job

    asyncio.create_task(
        ingest_company_document_job(
            document_id=document_id,
            filename=filename,
            contents=contents,
            raw_file=raw_file,
        )
    )

    return {
        "code": 200,
        "data": {
            "document_id": document_id,
            "filename": filename,
            "ingest_status": "queued",
            "raw_file": sign_company_library_asset(raw_file),
        },
        "message": "已上传公司资料并触发后台解析",
    }


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
            created_at=memory.created_at.isoformat() if memory.created_at else None,
            updated_at=memory.updated_at.isoformat() if memory.updated_at else None,
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


@router.post("/{user_id}/documents/ingest")
async def upload_customer_document_for_ingest(
    user_id: str,
    file: UploadFile = File(...),
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员上传客户维度 PDF/PPTX 资料，并触发客户画像 ingest。"""
    user_result = await db.execute(select(User.id).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="客户不存在")

    filename = file.filename or "customer_document"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".pdf", ".pptx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="仅支持 PDF/PPTX/TXT/MD 客户资料")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件大小不能超过50MB")

    document_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await memory_service.get_or_create_memory(user_id, db=db)
    await memory_service.upsert_customer_document_ingest(user_id, document_id, {
        "filename": filename,
        "source": "customer_profile_upload",
        "size": len(contents),
        "mime_type": file.content_type or "",
        "ingest_status": "queued",
        "ingest_error": "",
        "ingest_queued_at": now,
    })

    from app.services.document_ingest_service import ingest_customer_document_bytes
    asyncio.create_task(ingest_customer_document_bytes(
        user_id=user_id,
        document_id=document_id,
        filename=filename,
        contents=contents,
    ))

    return {
        "code": 200,
        "data": {"document_id": document_id, "filename": filename, "ingest_status": "queued"},
        "message": "已上传客户资料并触发解析",
    }


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
