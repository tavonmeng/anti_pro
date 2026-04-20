from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean
from app.database import Base
from app.utils.validators import generate_id

class Announcement(Base):
    """公告模型"""
    __tablename__ = "announcements"

    id = Column(String(50), primary_key=True, default=lambda: generate_id("anno"))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # 是否展示（或者发布状态）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(50), nullable=False)  # 创建人的 ADMIN_ID

    def __repr__(self):
        return f"<Announcement {self.id} '{self.title}'>"
