"""AI 聊天记录 API — 保存 & 加载

前端每次对话完成后自动同步到后端数据库。
客户端加载历史时从后端拉取（最近 N 条会话）。
管理员可查看所有用户的完整聊天记录。
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.ai_chat import AIChatSession, AIChatMessage
from app.schemas.response import ApiResponse
from app.utils.security import decode_access_token
from app.utils.dependencies import require_admin, AnyUser

router = APIRouter(prefix="/ai/chat-history", tags=["AI 聊天记录"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Schemas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SaveMessageRequest(BaseModel):
    session_id: str
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
    messages: list[dict]               # [{"role": "user", "content": "...", "timestamp": "..."}]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 辅助函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _extract_user(request: Request) -> tuple[str, str]:
    """从请求头提取 user_id 和 username"""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            return payload.get("user_id", "anonymous"), payload.get("username", "")
    return "anonymous", ""


def _make_title(content: str) -> str:
    """从第一条用户消息生成会话标题"""
    title = content.strip().replace("\n", " ")
    return title[:80] + "..." if len(title) > 80 else title


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 用户端 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/message")
async def save_message(
    data: SaveMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """保存单条消息（AI 对话完成后前端自动调用）"""
    user_id, username = _extract_user(request)

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

        # 如果 session 还没有标题且这条是 user 消息，设置标题
        if not session.title and data.role == "user":
            session.title = _make_title(data.content)

        # 保存消息
        msg = AIChatMessage(
            session_id=data.session_id,
            role=data.role,
            content=data.content,
            metadata_json=data.metadata,
        )
        db.add(msg)

        session.message_count = (session.message_count or 0) + 1
        session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        return {"code": 200, "message": "ok"}

    except Exception as e:
        print(f"[ChatHistory] 保存消息失败: {e}")
        # 不抛异常，不阻断聊天流程
        return {"code": 200, "message": "save skipped"}


@router.post("/sync")
async def sync_session(
    data: SyncSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """批量同步整个会话（前端关闭时或首次保存）"""
    user_id, username = _extract_user(request)

    try:
        # 检查是否已有这个 session
        result = await db.execute(
            select(AIChatSession).where(AIChatSession.id == data.session_id)
        )
        session = result.scalar_one_or_none()

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

        # 查已保存的消息数
        count_result = await db.execute(
            select(func.count(AIChatMessage.id)).where(
                AIChatMessage.session_id == data.session_id
            )
        )
        existing_count = count_result.scalar() or 0

        # 仅保存新消息（跳过已有的）
        new_messages = data.messages[existing_count:]
        for m in new_messages:
            msg = AIChatMessage(
                session_id=data.session_id,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                metadata_json=m.get("metadata"),
            )
            db.add(msg)

        session.message_count = existing_count + len(new_messages)
        session.updated_at = datetime.now(timezone.utc)

        # 补充标题
        if not session.title:
            first_user_msg = next(
                (m["content"] for m in data.messages if m.get("role") == "user"), ""
            )
            if first_user_msg:
                session.title = _make_title(first_user_msg)

        await db.commit()
        return {"code": 200, "message": "ok", "data": {"synced": len(new_messages)}}

    except Exception as e:
        print(f"[ChatHistory] 同步会话失败: {e}")
        return {"code": 200, "message": "sync skipped"}


@router.get("/sessions")
async def get_user_sessions(
    request: Request,
    limit: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的聊天会话列表（客户端默认最近5条）"""
    user_id, _ = _extract_user(request)
    if user_id == "anonymous":
        return {"code": 200, "data": []}

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
                "createdAt": s.created_at.isoformat() if s.created_at else None,
                "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
            })

        return {"code": 200, "data": items}
    except Exception as e:
        print(f"[ChatHistory] 获取会话列表失败: {e}")
        return {"code": 200, "data": []}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取某个会话的所有消息"""
    user_id, _ = _extract_user(request)

    try:
        # 验证权限：只能查自己的会话
        session_result = await db.execute(
            select(AIChatSession).where(AIChatSession.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            return {"code": 404, "data": [], "message": "会话不存在"}
        if session.user_id != user_id and user_id != "admin":
            return {"code": 403, "data": [], "message": "无权查看"}

        result = await db.execute(
            select(AIChatMessage)
            .where(AIChatMessage.session_id == session_id)
            .order_by(AIChatMessage.id.asc())
        )
        messages = result.scalars().all()

        items = [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
                "metadata": m.metadata_json,
            }
            for m in messages
        ]

        return {"code": 200, "data": items}
    except Exception as e:
        print(f"[ChatHistory] 获取消息失败: {e}")
        return {"code": 200, "data": []}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 管理员 API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/admin/sessions")
async def admin_get_all_sessions(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    current_user: AnyUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看所有用户的聊天记录"""
    try:
        query = select(AIChatSession)

        if user_id:
            query = query.where(AIChatSession.user_id == user_id)
        if keyword:
            from sqlalchemy import or_
            query = query.where(
                or_(
                    AIChatSession.title.ilike(f"%{keyword}%"),
                    AIChatSession.username.ilike(f"%{keyword}%"),
                )
            )

        # 总数
        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        # 分页
        query = query.order_by(desc(AIChatSession.updated_at))
        query = query.offset((page - 1) * pageSize).limit(pageSize)
        result = await db.execute(query)
        sessions = result.scalars().all()

        items = []
        for s in sessions:
            items.append({
                "id": s.id,
                "userId": s.user_id,
                "username": s.username,
                "title": s.title,
                "sessionType": s.session_type,
                "businessType": s.business_type,
                "messageCount": s.message_count,
                "createdAt": s.created_at.isoformat() if s.created_at else None,
                "updatedAt": s.updated_at.isoformat() if s.updated_at else None,
            })

        return ApiResponse(code=200, message="获取成功", data={"data": items, "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/sessions/{session_id}/messages")
async def admin_get_session_messages(
    session_id: str,
    current_user: AnyUser = Depends(require_admin),
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
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
                "metadata": m.metadata_json,
            }
            for m in messages
        ]

        return ApiResponse(code=200, message="获取成功", data=items)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
