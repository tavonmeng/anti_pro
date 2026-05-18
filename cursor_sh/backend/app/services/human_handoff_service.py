"""转人工客户记录与草稿保存服务。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.admin import Admin
from app.models.human_handoff import HumanHandoff
from app.models.notification import Notification, NotificationType
from app.models.order import Order, OrderStatus, OrderType
from app.models.user import User
from app.services.ai_client import post_chat_completion
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.validators import generate_id, generate_order_number


logger = get_module_logger("ai")


def _messages_snapshot(history: list[dict], user_msg: str, assistant_msg: str = "") -> list[dict]:
    messages: list[dict] = []
    for item in history or []:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content, "timestamp": item.get("timestamp", "")})
    messages.append({"role": "user", "content": user_msg, "timestamp": datetime.now(timezone.utc).isoformat()})
    if assistant_msg:
        messages.append({"role": "assistant", "content": assistant_msg, "timestamp": datetime.now(timezone.utc).isoformat()})
    return messages


def _chat_text(messages: list[dict]) -> str:
    role_map = {"user": "客户", "assistant": "AI"}
    return "\n".join(f"{role_map.get(m.get('role'), m.get('role'))}: {m.get('content', '')}" for m in messages)


def _order_type_from_business_type(business_type: str) -> OrderType:
    mapping = {
        "video_purchase": OrderType.VIDEO_PURCHASE,
        "digital_art": OrderType.DIGITAL_ART,
        "ai_3d_custom": OrderType.AI_3D_CUSTOM,
    }
    return mapping.get(business_type, OrderType.AI_3D_CUSTOM)


def _empty_order_data(business_type: str) -> dict[str, Any]:
    common = {
        "handoff": True,
        "handoff_status": "pending",
        "handoff_notes": "",
        "remarks": "",
    }
    if business_type == "video_purchase":
        return {
            **common,
            "industryType": "",
            "customIndustry": "",
            "visualStyle": "",
            "customStyle": "",
            "duration": 0,
            "priceRange": {"min": 0, "max": 0},
            "resolution": "",
            "size": "",
            "curvature": "",
        }
    if business_type == "digital_art":
        return {
            **common,
            "artDirection": "",
            "customDirection": "",
            "description": "",
            "materials": [],
        }
    return {
        **common,
        "brand": "",
        "background": "",
        "target_group": "",
        "brand_tone": "",
        "content": "",
        "style": "",
        "prohibited_content": "",
        "city": "",
        "media_size": "",
        "time_number": "",
        "technology": "",
        "budget": "",
        "online_time": "",
        "sales_contact": "",
        "scenePhotos": [],
        "project_name": "",
        "resource_background": "",
        "audience_scene": "",
        "media_positioning": "",
        "city_location": "",
        "viewing_path": "",
        "art_direction": "",
        "theme_concept": "",
        "media_specs": "",
        "timing_number": "",
        "tech_delivery": "",
        "content_review": "",
        "special_requirements": "",
    }


async def _extract_requirement_data(messages: list[dict], business_type: str) -> dict[str, Any]:
    if not settings.AI_API_KEY:
        return {}

    fields = (
        "project_name, resource_background, audience_scene, media_positioning, city_location, "
        "viewing_path, art_direction, theme_concept, media_specs, timing_number, tech_delivery, "
        "content_review, budget, online_time, special_requirements, site_photos, remarks"
        if settings.AGENT_MODE == "media" and business_type == "ai_3d_custom"
        else "brand, background, target_group, brand_tone, content, style, prohibited_content, "
        "city, media_size, time_number, technology, budget, online_time, site_photos, remarks, "
        "industryType, visualStyle, resolution, size, artDirection, description"
    )
    system_prompt = (
        "你是需求信息整理助手。请从对话中提取客户已经提供的项目信息，"
        "输出严格 JSON，不要解释。没有的信息用空字符串。"
        f"可用字段：{fields}。"
    )
    try:
        data = await post_chat_completion(
            {
                "model": settings.AI_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "对话记录：\n" + _chat_text(messages)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=30.0,
        )
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"):
            content = content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif content.startswith("```"):
            content = content.split("```", 1)[1].split("```", 1)[0].strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        log_business_event(
            logger,
            "human_handoff_extract_failed",
            level="warning",
            business_type=business_type,
            message_count=len(messages),
            error=str(e),
        )
        return {}


def _merge_order_data(
    base: dict[str, Any],
    extracted: dict[str, Any],
    messages: list[dict],
    session_id: str,
    handoff_id: str,
    handoff_status: str,
) -> dict[str, Any]:
    merged = dict(base or {})
    for key, value in (extracted or {}).items():
        if value not in (None, "", [], {}):
            merged[key] = value

    handoff_note = f"转人工会话：{session_id}\n触发后聊天记录已同步到管理员端转人工客户队列。"
    existing_notes = (merged.get("handoff_notes") or "").strip()
    if handoff_note not in existing_notes:
        merged["handoff_notes"] = (existing_notes + "\n" + handoff_note).strip()

    merged["handoff"] = True
    merged["handoff_id"] = handoff_id
    merged["handoff_status"] = handoff_status
    merged["chat_snapshot"] = messages
    return merged


async def record_handoff(
    *,
    user_id: str,
    username: str,
    session_id: str,
    business_type: str,
    history: list[dict],
    user_msg: str,
    assistant_msg: str,
) -> dict[str, Any]:
    messages = _messages_snapshot(history, user_msg, assistant_msg)
    extracted = await _extract_requirement_data(messages, business_type)
    draft_order_created = False
    admin_count = 0

    async with async_session_maker() as db:
        user = None
        if user_id and user_id != "anonymous":
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()

        result = await db.execute(select(HumanHandoff).where(HumanHandoff.session_id == session_id))
        handoff = result.scalar_one_or_none()
        is_new = handoff is None

        if is_new:
            handoff = HumanHandoff(
                id=generate_id("handoff"),
                user_id=user_id or "anonymous",
                username=username or (user.username if user else "anonymous"),
                session_id=session_id,
                business_type=business_type,
                status="pending",
                trigger_message=user_msg,
            )
            db.add(handoff)

        handoff.username = username or handoff.username or (user.username if user else "")
        handoff.business_type = business_type or handoff.business_type
        handoff.trigger_message = handoff.trigger_message or user_msg
        handoff.chat_snapshot = messages
        handoff.extracted_data = extracted
        handoff.message_count = len(messages)
        handoff.updated_at = datetime.now(timezone.utc)

        if user:
            order_type = _order_type_from_business_type(business_type)
            draft_order = None
            if handoff.draft_order_id:
                draft_result = await db.execute(select(Order).where(Order.id == handoff.draft_order_id))
                draft_order = draft_result.scalar_one_or_none()

            if not draft_order:
                draft_order = Order(
                    id=generate_id("order"),
                    order_number=generate_order_number(),
                    order_type=order_type,
                    status=OrderStatus.DRAFT,
                    user_id=user.id,
                    revision_count=0,
                    order_data={},
                )
                db.add(draft_order)
                handoff.draft_order_id = draft_order.id
                draft_order_created = True

            base_data = draft_order.order_data or _empty_order_data(business_type)
            if not base_data:
                base_data = _empty_order_data(business_type)
            draft_order.order_data = _merge_order_data(base_data, extracted, messages, session_id, handoff.id, handoff.status)
            draft_order.updated_at = datetime.now(timezone.utc)

        if is_new:
            admin_result = await db.execute(select(Admin).where(Admin.is_active == True))
            admins = admin_result.scalars().all()
            admin_count = len(admins)
            customer_label = (user.enterprise_name or user.company or user.username) if user else (username or user_id or "匿名用户")
            for admin in admins:
                db.add(Notification(
                    user_id=admin.id,
                    type=NotificationType.SYSTEM_NOTICE,
                    title="新转人工客户",
                    content=f"{customer_label} 触发了转人工，请在“转人工客户”中跟进。",
                    is_read=False,
                ))

        await db.commit()
        await db.refresh(handoff)

        log_business_event(
            logger,
            "human_handoff_recorded",
            user_id=user_id,
            username=username,
            session_id=session_id,
            business_type=business_type,
            handoff_id=handoff.id,
            draft_order_id=handoff.draft_order_id,
            draft_order_created=draft_order_created,
            is_new=is_new,
            status=handoff.status,
            message_count=len(messages),
            extracted_field_count=len(extracted or {}),
            admin_count=admin_count,
        )

        return {
            "handoff_id": handoff.id,
            "draft_order_id": handoff.draft_order_id,
            "is_new": is_new,
        }


async def append_handoff_message(
    *,
    user_id: str,
    username: str,
    session_id: str,
    business_type: str,
    history: list[dict],
    user_msg: str,
    assistant_msg: str,
) -> dict[str, Any] | None:
    async with async_session_maker() as db:
        result = await db.execute(select(HumanHandoff).where(HumanHandoff.session_id == session_id))
        handoff = result.scalar_one_or_none()
        if not handoff:
            log_business_event(
                logger,
                "human_handoff_append_skipped",
                level="debug",
                user_id=user_id,
                session_id=session_id,
                business_type=business_type,
                reason="not_found",
            )
            return None

    return await record_handoff(
        user_id=user_id,
        username=username,
        session_id=session_id,
        business_type=business_type,
        history=history,
        user_msg=user_msg,
        assistant_msg=assistant_msg,
    )
