"""AI 聊天记录 API — 保存 & 加载

前端每次对话完成后自动同步到后端数据库。
客户端加载历史时从后端拉取（最近 N 条会话）。
管理员可查看所有用户的完整聊天记录。
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, exists, delete
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models.ai_chat import AIChatSession, AIChatMessage
from app.models.user import User
from app.schemas.response import ApiResponse
from app.services.ai_brief_state import load_agent_state
from app.utils.dependencies import get_current_user_for_public_deployment, require_internal_admin, AnyUser
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.timezone import beijing_iso, beijing_now

router = APIRouter(prefix="/ai/chat-history", tags=["AI 聊天记录"])
logger = get_module_logger("ai")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Schemas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SaveMessageRequest(BaseModel):
    session_id: str
    client_message_id: Optional[str] = None
    role: str                          # user / assistant
    content: str
    business_type: str = "ai_3d_custom"
    session_type: str = "requirement"
    metadata: Optional[dict] = None


class SyncSessionRequest(BaseModel):
    """前端批量同步整个会话（首次保存或恢复）"""
    session_id: str
    business_type: str = "ai_3d_custom"
    session_type: str = "requirement"
    messages: list[dict]               # [{"client_message_id": "...", "role": "user", "content": "..."}]
    replace: bool = False              # True 时以后端消息完全替换为本次列表


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 辅助函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _user_identity(current_user: AnyUser) -> tuple[str, str]:
    return current_user.id, getattr(current_user, "username", "") or ""


def _make_title(content: str) -> str:
    """从第一条用户消息生成会话标题"""
    title = content.strip().replace("\n", " ")
    return title[:80] + "..." if len(title) > 80 else title


def _refresh_session_owner(session: AIChatSession, user_id: str, username: str):
    """会话先被匿名接口创建时，后续同步可补正为真实客户。"""
    if user_id and user_id != "anonymous":
        if not session.user_id or session.user_id == "anonymous":
            session.user_id = user_id
        if username and (not session.username or session.username == "anonymous"):
            session.username = username


def _ensure_session_owner(session: AIChatSession, user_id: str, username: str):
    """Protect client-generated session IDs from cross-user reuse."""
    current_user_id = user_id or "anonymous"
    owner_id = session.user_id or "anonymous"
    if owner_id != "anonymous" and owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="无权修改此会话")
    _refresh_session_owner(session, user_id, username)


def _message_pair(message: dict) -> tuple[str, str]:
    return (message.get("role", "user"), message.get("content", ""))


def _unsynced_messages(existing: list[tuple[str, str]], incoming: list[dict]) -> list[dict]:
    """Return only incoming messages that are not already stored as a prefix.

    The AI endpoint can persist the same turn in the background while the
    browser also syncs the whole conversation. Prefix matching keeps the common
    path idempotent and avoids duplicating the full transcript on retries.
    """
    incoming_pairs = [_message_pair(m) for m in incoming]
    if existing == incoming_pairs[:len(existing)]:
        return incoming[len(existing):]

    # If a previous background save wrote the latest turn first, find the
    # longest suffix of existing that matches the incoming prefix.
    max_overlap = min(len(existing), len(incoming_pairs))
    for overlap in range(max_overlap, 0, -1):
        if existing[-overlap:] == incoming_pairs[:overlap]:
            return incoming[overlap:]
    return incoming


def _message_client_id(message: dict) -> str:
    return message.get("client_message_id") or message.get("clientMessageId") or ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 用户端 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/message")
async def save_message(
    data: SaveMessageRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db),
):
    """保存单条消息（AI 对话完成后前端自动调用）"""
    user_id, username = _user_identity(current_user)

    try:
        # 查找或创建 session
        result = await db.execute(
            select(AIChatSession).where(AIChatSession.id == data.session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            session = AIChatSession(
                id=data.session_id,
                user_id=user_id,
                username=username,
                session_type=data.session_type,
                business_type=data.business_type,
                title=_make_title(data.content) if data.role == "user" else None,
                message_count=0,
            )
            db.add(session)
        else:
            _ensure_session_owner(session, user_id, username)
            session.session_type = data.session_type or session.session_type
            session.business_type = data.business_type or session.business_type

        # 如果 session 还没有标题且这条是 user 消息，设置标题
        if not session.title and data.role == "user":
            session.title = _make_title(data.content)

        if data.client_message_id:
            existing_msg_result = await db.execute(
                select(AIChatMessage).where(
                    AIChatMessage.session_id == data.session_id,
                    AIChatMessage.client_message_id == data.client_message_id,
                )
            )
            existing_msg = existing_msg_result.scalar_one_or_none()
            if existing_msg:
                existing_msg.role = data.role
                existing_msg.content = data.content
                if data.metadata is not None:
                    existing_msg.metadata_json = data.metadata
                session.updated_at = beijing_now()
                await db.commit()
                log_business_event(
                    logger,
                    "ai_chat_message_updated",
                    session_id=data.session_id,
                    user_id=user_id,
                    role=data.role,
                    client_message_id=data.client_message_id,
                    business_type=session.business_type,
                )
                return {"code": 200, "message": "ok"}

        # 保存消息
        msg = AIChatMessage(
            session_id=data.session_id,
            client_message_id=data.client_message_id,
            role=data.role,
            content=data.content,
            metadata_json=data.metadata,
        )
        db.add(msg)

        session.message_count = (session.message_count or 0) + 1
        session.updated_at = beijing_now()

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            log_business_event(
                logger,
                "ai_chat_message_duplicate_skipped",
                level="debug",
                session_id=data.session_id,
                user_id=user_id,
                role=data.role,
                client_message_id=data.client_message_id,
            )
        else:
            log_business_event(
                logger,
                "ai_chat_message_saved",
                session_id=data.session_id,
                user_id=user_id,
                role=data.role,
                client_message_id=data.client_message_id,
                business_type=session.business_type,
                message_count=session.message_count,
            )
        return {"code": 200, "message": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_history_save_failed",
            level="warning",
            session_id=getattr(data, "session_id", None),
            role=getattr(data, "role", None),
            business_type=getattr(data, "business_type", None),
            error=str(e),
        )
        # 不抛异常，不阻断聊天流程
        return {"code": 200, "message": "save skipped"}


@router.post("/sync")
async def sync_session(
    data: SyncSessionRequest,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db),
):
    """批量同步整个会话（前端关闭时或首次保存）"""
    user_id, username = _user_identity(current_user)

    try:
        # 检查是否已有这个 session
        result = await db.execute(
            select(AIChatSession).where(AIChatSession.id == data.session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            _ensure_session_owner(session, user_id, username)

        if data.replace and not data.messages:
            if session:
                await db.execute(
                    delete(AIChatMessage).where(AIChatMessage.session_id == data.session_id)
                )
                await db.execute(
                    delete(AIChatSession).where(AIChatSession.id == data.session_id)
                )
                await db.commit()
            return {"code": 200, "message": "ok", "data": {"synced": 0}}

        if not session:
            first_user_msg = next(
                (m["content"] for m in data.messages if m.get("role") == "user"), ""
            )
            session = AIChatSession(
                id=data.session_id,
                user_id=user_id,
                username=username,
                session_type=data.session_type,
                business_type=data.business_type,
                title=_make_title(first_user_msg) if first_user_msg else None,
                message_count=0,
            )
            db.add(session)
            await db.flush()
        else:
            session.session_type = data.session_type or session.session_type
            session.business_type = data.business_type or session.business_type

        existing_result = await db.execute(
            select(AIChatMessage.role, AIChatMessage.content)
            .where(AIChatMessage.session_id == data.session_id)
            .order_by(AIChatMessage.id.asc())
        )
        existing_pairs = [(role, content) for role, content in existing_result.all()]

        incoming_with_ids = [m for m in data.messages if _message_client_id(m)]
        if incoming_with_ids and len(incoming_with_ids) == len(data.messages):
            message_ids = [_message_client_id(m) for m in data.messages]
            if data.replace:
                await db.execute(
                    delete(AIChatMessage).where(
                        AIChatMessage.session_id == data.session_id,
                        ~AIChatMessage.client_message_id.in_(message_ids),
                    )
                )
            id_result = await db.execute(
                select(AIChatMessage).where(
                    AIChatMessage.session_id == data.session_id,
                    AIChatMessage.client_message_id.in_(message_ids),
                )
            )
            existing_by_id = {m.client_message_id: m for m in id_result.scalars().all()}
            for incoming in data.messages:
                existing_msg = existing_by_id.get(_message_client_id(incoming))
                if existing_msg:
                    incoming_content = incoming.get("content", "")
                    if existing_msg.content != incoming_content:
                        existing_msg.content = incoming_content
                    if incoming.get("metadata") is not None:
                        existing_msg.metadata_json = incoming.get("metadata")
            existing_ids = set(existing_by_id.keys())
            new_messages = [m for m in data.messages if _message_client_id(m) not in existing_ids]
        else:
            # 兼容旧客户端/旧 localStorage 记录：按已有前缀跳过。
            if data.replace:
                await db.execute(
                    delete(AIChatMessage).where(AIChatMessage.session_id == data.session_id)
                )
                existing_pairs = []
            new_messages = _unsynced_messages(existing_pairs, data.messages)

        for m in new_messages:
            msg = AIChatMessage(
                session_id=data.session_id,
                client_message_id=_message_client_id(m) or None,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                metadata_json=m.get("metadata"),
            )
            db.add(msg)

        session.message_count = len(data.messages) if data.replace else len(existing_pairs) + len(new_messages)
        session.updated_at = beijing_now()

        # 补充标题
        if data.replace:
            first_user_msg = next(
                (m["content"] for m in data.messages if m.get("role") == "user"), ""
            )
            session.title = _make_title(first_user_msg) if first_user_msg else None
        elif not session.title:
            first_user_msg = next(
                (m["content"] for m in data.messages if m.get("role") == "user"), ""
            )
            if first_user_msg:
                session.title = _make_title(first_user_msg)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            log_business_event(
                logger,
                "ai_chat_session_sync_duplicate_skipped",
                level="debug",
                session_id=data.session_id,
                user_id=user_id,
                business_type=data.business_type,
            )
        else:
            log_business_event(
                logger,
                "ai_chat_session_synced",
                session_id=data.session_id,
                user_id=user_id,
                business_type=session.business_type,
                replace=data.replace,
                incoming_message_count=len(data.messages),
                synced_message_count=len(new_messages),
                session_message_count=session.message_count,
            )
        return {"code": 200, "message": "ok", "data": {"synced": len(new_messages)}}

    except HTTPException:
        raise
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_history_sync_failed",
            level="warning",
            session_id=getattr(data, "session_id", None),
            business_type=getattr(data, "business_type", None),
            message_count=len(getattr(data, "messages", []) or []),
            error=str(e),
        )
        return {"code": 200, "message": "sync skipped"}


@router.get("/sessions")
async def get_user_sessions(
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的聊天会话列表（客户端默认最近5条）"""
    user_id, _ = _user_identity(current_user)

    try:
        result = await db.execute(
            select(AIChatSession)
            .where(AIChatSession.user_id == user_id)
            .order_by(desc(AIChatSession.updated_at))
            .limit(limit)
        )
        sessions = result.scalars().all()

        items = []
        for s in sessions:
            items.append({
                "id": s.id,
                "title": s.title,
                "sessionType": s.session_type,
                "businessType": s.business_type,
                "messageCount": s.message_count,
                "createdAt": beijing_iso(s.created_at),
                "updatedAt": beijing_iso(s.updated_at),
            })

        return {"code": 200, "data": items}
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_history_sessions_failed",
            level="warning",
            user_id=user_id,
            error=str(e),
        )
        return {"code": 200, "data": []}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db),
):
    """获取某个会话的所有消息"""
    user_id, _ = _user_identity(current_user)

    try:
        # 验证权限：只能查自己的会话
        session_result = await db.execute(
            select(AIChatSession).where(AIChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            return {"code": 404, "data": [], "message": "会话不存在"}
        if session.user_id != user_id:
            return {"code": 403, "data": [], "message": "无权查看"}

        result = await db.execute(
            select(AIChatMessage)
            .where(AIChatMessage.session_id == session_id)
            .order_by(AIChatMessage.id.asc())
        )
        messages = result.scalars().all()

        items = [
            {
                "client_message_id": m.client_message_id,
                "role": m.role,
                "content": m.content,
                "timestamp": beijing_iso(m.created_at),
                "metadata": m.metadata_json,
            }
            for m in messages
        ]

        return {"code": 200, "data": items}
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_history_messages_failed",
            level="warning",
            user_id=user_id,
            session_id=session_id,
            error=str(e),
        )
        return {"code": 200, "data": []}


@router.get("/sessions/{session_id}/state")
async def get_session_state(
    session_id: str,
    current_user: AnyUser = Depends(get_current_user_for_public_deployment),
    db: AsyncSession = Depends(get_db),
):
    """获取某个会话对应的 AI Agent 状态，用于历史会话恢复后继续对话。"""
    user_id, _ = _user_identity(current_user)

    try:
        session_result = await db.execute(
            select(AIChatSession).where(AIChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            return {"code": 404, "data": None, "message": "会话不存在"}
        if session.user_id != user_id:
            return {"code": 403, "data": None, "message": "无权查看"}

        state = load_agent_state(
            session_id=session_id,
            user_id=user_id,
            business_type=session.business_type or "ai_3d_custom",
        )
        return {"code": 200, "data": state}
    except Exception as e:
        log_business_event(
            logger,
            "ai_chat_history_state_failed",
            level="warning",
            user_id=user_id,
            session_id=session_id,
            error=str(e),
        )
        return {"code": 200, "data": None}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 管理员 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/admin/sessions")
async def admin_get_all_sessions(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    current_user: AnyUser = Depends(require_internal_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看所有用户的聊天记录"""
    try:
        query = (
            select(
                AIChatSession,
                User.phone,
                User.email,
                User.company,
                User.enterprise_name,
            )
            .outerjoin(User, AIChatSession.user_id == User.id)
        )

        if user_id:
            query = query.where(AIChatSession.user_id == user_id)
        if keyword:
            from sqlalchemy import or_
            kw = f"%{keyword}%"
            query = query.where(
                or_(
                    AIChatSession.title.ilike(kw),
                    AIChatSession.username.ilike(kw),
                    User.username.ilike(kw),
                    User.phone.ilike(kw),
                    User.email.ilike(kw),
                    User.company.ilike(kw),
                    User.enterprise_name.ilike(kw),
                    exists().where(
                        AIChatMessage.session_id == AIChatSession.id,
                        AIChatMessage.content.ilike(kw),
                    ),
                )
            )

        # 总数
        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        # 分页
        query = query.order_by(desc(AIChatSession.updated_at))
        query = query.offset((page - 1) * pageSize).limit(pageSize)
        result = await db.execute(query)
        rows = result.all()

        items = []
        for s, phone, email, company, enterprise_name in rows:
            items.append({
                "id": s.id,
                "userId": s.user_id,
                "username": s.username,
                "phone": phone,
                "email": email,
                "company": enterprise_name or company or "",
                "title": s.title,
                "sessionType": s.session_type,
                "businessType": s.business_type,
                "messageCount": s.message_count,
                "createdAt": beijing_iso(s.created_at),
                "updatedAt": beijing_iso(s.updated_at),
            })

        return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e


@router.get("/admin/sessions/{session_id}/messages")
async def admin_get_session_messages(
    session_id: str,
    current_user: AnyUser = Depends(require_internal_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看某个会话的完整消息"""
    try:
        result = await db.execute(
            select(AIChatMessage)
            .where(AIChatMessage.session_id == session_id)
            .order_by(AIChatMessage.id.asc())
        )
        messages = result.scalars().all()

        items = [
            {
                "client_message_id": m.client_message_id,
                "role": m.role,
                "content": m.content,
                "timestamp": beijing_iso(m.created_at),
                "metadata": m.metadata_json,
            }
            for m in messages
        ]

        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误，请稍后重试") from e
