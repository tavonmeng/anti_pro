"""用户画像 Memory 模型 — 存储 Agent 跨会话记忆"""

from sqlalchemy import Column, String, Text, DateTime, JSON
from app.database import Base
from app.utils.timezone import beijing_now


class UserMemory(Base):
    """用户画像 Memory

    每个用户一条记录，存储 Agent 需要的跨会话上下文信息。
    包括：公司信息（爬取）、屏幕资源（爬取）、项目偏好（LLM 总结）、
    历史项目（orders 同步）、交互统计、Agent 备忘。
    """
    __tablename__ = "user_memories"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)

    # 公司信息（来自官网爬取 + LLM 提取）
    # {
    #   "name": "XX传媒",
    #   "website": "https://xx-media.com",
    #   "description": "国内领先的...",
    #   "advantages": ["核心商圈资源", "..."],
    #   "crawled_at": "2026-05-01T12:00:00",
    #   "crawl_status": "success" | "failed" | "pending"
    # }
    company_info = Column(JSON, default=dict)

    # 屏幕资源列表（来自官网爬取 + LLM 提取）
    # [
    #   {"city": "成都", "location": "春熙路", "type": "L型LED", "size": "800㎡", "resolution": "3840x2160"},
    #   ...
    # ]
    screen_resources = Column(JSON, default=list)

    # 项目偏好（LLM 从对话中学习总结）
    # {
    #   "common_cities": ["成都", "上海"],
    #   "preferred_styles": ["未来科技", "城市文化"],
    #   "budget_range": "30-60万",
    #   "typical_duration": "30秒"
    # }
    project_preferences = Column(JSON, default=dict)

    # 历史项目摘要（从 orders 表自动同步）
    # [
    #   {"order_number": "ORD-xxx", "project_name": "春熙路项目", "city": "成都", "status": "completed"},
    #   ...
    # ]
    past_projects = Column(JSON, default=list)

    # 交互统计
    # {
    #   "total_sessions": 5,
    #   "first_contact": "2026-04-20",
    #   "last_contact": "2026-05-01"
    # }
    interaction_stats = Column(JSON, default=dict)

    # Agent 自由备忘录
    agent_notes = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)

    def __repr__(self):
        return f"<UserMemory(user_id={self.user_id})>"
