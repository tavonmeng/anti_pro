"""公司资料库服务。

用于管理员在客户注册前上传 PDF/PPTX 资料，按自动识别出的公司名归档；
客户注册/填写公司名后，再同步到该客户的 UserMemory。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.company_profile import CompanyLibraryDocument, CompanyProfile, CompanyProfileIngestJob
from app.models.user import User


def normalize_company_name(name: str) -> str:
    value = (name or "").strip().lower()
    value = re.sub(r"[\s（）()【】\[\]·,，.。\-_/]+", "", value)
    suffixes = [
        "有限责任公司", "股份有限公司", "集团有限公司", "有限公司",
        "集团", "公司", "传媒", "广告", "文化", "科技",
    ]
    for suffix in suffixes:
        suffix = suffix.lower()
        if value.endswith(suffix) and len(value) > len(suffix):
            value = value[: -len(suffix)]
    return value or "unknown"


async def sync_company_profile_ingest(document_info: dict[str, Any]) -> CompanyProfile:
    """将一次文档 ingest 结果归档到公司资料库。"""
    company_info = document_info.get("company_info") or {}
    extracted_name = company_info.get("company_name") or ""
    company_name = extracted_name or document_info.get("company_name") or "未知公司"
    company_key = normalize_company_name(company_name)
    now = datetime.now().isoformat()

    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfile).where(CompanyProfile.company_key == company_key)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            profile = CompanyProfile(
                id=str(uuid.uuid4()),
                company_key=company_key,
                company_name=company_name,
                profile_data={},
                screen_resources=[],
                documents=[],
            )
            session.add(profile)

        profile.company_name = company_name if company_name != "未知公司" else profile.company_name
        profile.profile_data = _merge_profile_data(profile.profile_data or {}, document_info)
        profile.screen_resources = _merge_screen_resources(
            profile.screen_resources or [],
            document_info.get("media_assets") or [],
            company_key=company_key,
            company_name=profile.company_name,
            source_filename=document_info.get("filename", ""),
        )

        docs = profile.documents or []
        docs.append({
            "document_id": document_info.get("document_id", ""),
            "filename": document_info.get("filename", ""),
            "title": document_info.get("document_title", ""),
            "brief": document_info.get("brief", ""),
            "assets": document_info.get("assets") or {},
            "page_count": document_info.get("page_count", ""),
            "text_chars": document_info.get("text_chars", ""),
            "ingested_at": now,
        })
        profile.documents = docs[-20:]

        await session.commit()
        await session.refresh(profile)
        return profile


async def link_profile_to_matching_users(company_name: str) -> int:
    """将公司资料同步给已存在且公司名匹配的用户。"""
    company_key = normalize_company_name(company_name)
    if not company_key or company_key == "unknown":
        return 0

    async with async_session_maker() as session:
        profile = await find_company_profile(company_name, session=session)
        if not profile:
            return 0

        result = await session.execute(
            select(User).where(
                or_(
                    User.company.isnot(None),
                    User.enterprise_name.isnot(None),
                )
            )
        )
        users = result.scalars().all()

    matched = 0
    for user in users:
        user_company = user.enterprise_name or user.company or ""
        if normalize_company_name(user_company) == company_key:
            await attach_company_profile_to_user(user.id, profile)
            matched += 1
    return matched


async def attach_matching_profile_to_user(user_id: str, company_name: str) -> bool:
    """用户注册/更新资料后，按公司名查找并接入已有公司资料。"""
    if not user_id or not company_name:
        return False
    async with async_session_maker() as session:
        profile = await find_company_profile(company_name, session=session)
    if not profile:
        return False
    await attach_company_profile_to_user(user_id, profile)
    return True


async def find_company_profile(company_name: str, session: AsyncSession | None = None) -> CompanyProfile | None:
    company_key = normalize_company_name(company_name)
    if not company_key or company_key == "unknown":
        return None

    async def _inner(db: AsyncSession):
        result = await db.execute(
            select(CompanyProfile).where(CompanyProfile.company_key == company_key)
        )
        return result.scalar_one_or_none()

    if session:
        return await _inner(session)
    async with async_session_maker() as db:
        return await _inner(db)


async def list_company_profiles(limit: int = 50) -> list[CompanyProfile]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfile).order_by(CompanyProfile.updated_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


async def get_company_profile_by_key(company_key: str) -> CompanyProfile | None:
    if not company_key:
        return None
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfile).where(CompanyProfile.company_key == company_key)
        )
        return result.scalar_one_or_none()


async def update_company_profile(
    company_key: str,
    updates: dict[str, Any],
) -> CompanyProfile | None:
    """管理员编辑已解析的公司资料。"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfile).where(CompanyProfile.company_key == company_key)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return None

        if "company_name" in updates and updates["company_name"]:
            profile.company_name = str(updates["company_name"]).strip()
        if "profile_data" in updates and isinstance(updates["profile_data"], dict):
            existing = dict(profile.profile_data or {})
            incoming = dict(updates["profile_data"])
            if existing.get("manual_links") and "manual_links" not in incoming:
                incoming["manual_links"] = existing["manual_links"]
            incoming["updated_at"] = datetime.now().isoformat()
            profile.profile_data = incoming
        if "screen_resources" in updates and isinstance(updates["screen_resources"], list):
            profile.screen_resources = updates["screen_resources"]
        if "notes" in updates:
            profile.notes = str(updates["notes"] or "")

        await session.commit()
        await session.refresh(profile)
        return profile


async def create_company_profile_ingest_job(
    document_id: str,
    filename: str,
    file_size: int,
    mime_type: str,
    source: str = "company_profile_upload",
    result: dict[str, Any] | None = None,
) -> CompanyProfileIngestJob:
    async with async_session_maker() as session:
        job = CompanyProfileIngestJob(
            id=document_id,
            filename=filename,
            source=source,
            status="queued",
            file_size=str(file_size),
            mime_type=mime_type or "",
            result=result or {},
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


async def update_company_profile_ingest_job(document_id: str, updates: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfileIngestJob).where(CompanyProfileIngestJob.id == document_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            return
        for key, value in updates.items():
            if hasattr(job, key):
                if key == "result" and isinstance(value, dict):
                    existing = dict(job.result or {})
                    existing.update(value)
                    setattr(job, key, existing)
                else:
                    setattr(job, key, value)
        await session.commit()


async def list_company_profile_ingest_jobs(limit: int = 20) -> list[CompanyProfileIngestJob]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfileIngestJob)
            .order_by(CompanyProfileIngestJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def create_company_library_document(
    document_id: str,
    filename: str,
    file_size: int,
    mime_type: str,
    raw_file: dict[str, Any],
    source: str = "company_profile_upload",
) -> CompanyLibraryDocument:
    """创建公司资料库文档记录。"""
    async with async_session_maker() as session:
        document = CompanyLibraryDocument(
            id=document_id,
            filename=filename,
            source=source,
            status="queued",
            file_size=str(file_size),
            mime_type=mime_type or "",
            raw_file=raw_file or {},
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


async def update_company_library_document(document_id: str, updates: dict[str, Any]) -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyLibraryDocument).where(CompanyLibraryDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return
        for key, value in updates.items():
            if hasattr(document, key):
                setattr(document, key, value)
        await session.commit()


async def list_company_library_documents(limit: int = 100) -> list[CompanyLibraryDocument]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyLibraryDocument)
            .order_by(CompanyLibraryDocument.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_company_library_document(document_id: str) -> CompanyLibraryDocument | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyLibraryDocument).where(CompanyLibraryDocument.id == document_id)
        )
        return result.scalar_one_or_none()


async def attach_company_profile_to_user(user_id: str, profile: CompanyProfile):
    """把公司资料库中的画像同步进某个用户的 Memory。"""
    from app.services.memory_service import sync_document_ingest

    await sync_document_ingest(user_id, {
        "source": "company_profile_library",
        "company_name": profile.company_name,
        "filename": (profile.documents or [{}])[-1].get("filename", ""),
        "document_title": (profile.documents or [{}])[-1].get("title", ""),
        "brief": (profile.profile_data or {}).get("brief", ""),
        "company_info": (profile.profile_data or {}).get("company_info", {}),
        "media_assets": _screen_resources_to_media_assets(profile.screen_resources or []),
    })


async def attach_company_profile_to_user_by_key(company_key: str, user_id: str) -> tuple[bool, str]:
    """管理员手动把公司资料关联到已注册用户。"""
    async with async_session_maker() as session:
        profile_result = await session.execute(
            select(CompanyProfile).where(CompanyProfile.company_key == company_key)
        )
        profile = profile_result.scalar_one_or_none()
        if not profile:
            return False, "公司资料不存在"

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            return False, "用户不存在"

    await attach_company_profile_to_user(user_id, profile)

    async with async_session_maker() as session:
        result = await session.execute(
            select(CompanyProfile).where(CompanyProfile.company_key == company_key)
        )
        profile = result.scalar_one_or_none()
        if profile:
            data = dict(profile.profile_data or {})
            links = [dict(item) for item in (data.get("manual_links") or []) if isinstance(item, dict)]
            link = {
                "user_id": user.id,
                "username": user.username or "",
                "phone": user.phone or "",
                "company": user.enterprise_name or user.company or "",
                "linked_at": datetime.now().isoformat(),
            }
            links = [item for item in links if item.get("user_id") != user.id]
            links.append(link)
            data["manual_links"] = links[-50:]
            profile.profile_data = data
            await session.commit()
    return True, "已关联并同步到用户画像"


def _merge_profile_data(existing: dict, document_info: dict) -> dict:
    merged = dict(existing or {})
    for key in [
        "document_title", "brief", "company_info", "project_requirements",
        "creative_direction", "deliverables", "timeline_budget", "risks",
        "questions", "page_summaries",
    ]:
        value = document_info.get(key)
        if value:
            merged[key] = value
    merged["updated_at"] = datetime.now().isoformat()
    return merged


def _merge_screen_resources(existing: list, media_assets: list, company_key: str, company_name: str, source_filename: str) -> list:
    merged = [dict(item) for item in existing if isinstance(item, dict)]

    def key_of(item: dict) -> tuple[str, str]:
        return (str(item.get("city") or ""), str(item.get("location") or item.get("screen_location") or ""))

    index = {key_of(item): idx for idx, item in enumerate(merged)}
    for asset in media_assets:
        if not isinstance(asset, dict):
            continue
        specs = asset.get("screen_specs") or {}
        daily_media_contacts = asset.get("daily_media_contacts") or _extract_daily_media_contacts(
            asset.get("audience_or_traffic") or []
        )
        item = {
            "company_key": company_key,
            "company_name": company_name,
            "city": asset.get("city", ""),
            "location": asset.get("screen_location", ""),
            "type": "、".join(asset.get("screen_features") or []),
            "size": specs.get("size", ""),
            "resolution": specs.get("resolution", ""),
            "daily_media_contacts": daily_media_contacts,
            "daily_traffic": "、".join(asset.get("audience_or_traffic") or []),
            "city_value": asset.get("city_value") or [],
            "location_features": asset.get("location_features") or [],
            "screen_features": asset.get("screen_features") or [],
            "screen_specs": specs,
            "audience_or_traffic": asset.get("audience_or_traffic") or [],
            "source": "company_profile_library",
            "source_filename": source_filename,
            "source_pages": asset.get("source_pages") or [],
        }
        item_key = key_of(item)
        if item_key in index:
            merged[index[item_key]].update({k: v for k, v in item.items() if v})
        else:
            merged.append(item)
    return merged[-100:]


def _screen_resources_to_media_assets(resources: list) -> list:
    assets = []
    for item in resources:
        if not isinstance(item, dict):
            continue
        assets.append({
            "city": item.get("city", ""),
            "city_value": item.get("city_value") or [],
            "screen_location": item.get("location", ""),
            "location_features": item.get("location_features") or [],
            "screen_features": item.get("screen_features") or [],
            "screen_specs": item.get("screen_specs") or {
                "size": item.get("size", ""),
                "resolution": item.get("resolution", ""),
            },
            "daily_media_contacts": item.get("daily_media_contacts") or _extract_daily_media_contacts(
                item.get("audience_or_traffic") or [item.get("daily_traffic", "")]
            ),
            "audience_or_traffic": item.get("audience_or_traffic") or [],
            "source_pages": item.get("source_pages") or [],
        })
    return assets


def _extract_daily_media_contacts(values: list) -> str:
    """从旧的客流/曝光字段中兼容提取日媒体接触人次。"""
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        if "日媒体接触" in text or "日均媒体接触" in text:
            return text
        match = re.search(r"(日[^，、；;]*?(?:媒体接触|触达|接触人次)[^，、；;]*)", text)
        if match:
            return match.group(1)
    return ""
