"""AI 聊天会话 & 消息 — 数据模型

将客户的 AI 对话完整保存到数据库，管理员可随时查阅。
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.sql import func
from app.database import Base


class AIChatSession(Base):
    """AI 聊天会话"""
    __tablename__ = "ai_chat_sessions"

    id = Column(String(50), primary_key=True)                  # session_id
    user_id = Column(String(50), nullable=False, index=True)   # 用户 ID
    username = Column(String(100), nullable=True)              # 用户名（冗余，方便管理员查看）
    session_type = Column(String(20), default="requirement")   # requirement / order / general
    business_type = Column(String(30), default="ai_3d_custom") # ai_3d_custom / video_purchase / digital_art
    title = Column(String(200), nullable=True)                 # 会话标题（取第一条用户消息摘要）
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIChatMessage(Base):
    """AI 聊天消息"""
    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    role = Column(String(20), nullable=False)                  # user / assistant / system
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)                # 附加数据（上传文件等）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
