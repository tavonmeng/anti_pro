"""普通用户一次性邀请链接模型"""

from sqlalchemy import Column, String, Boolean, DateTime

from app.database import Base
from app.utils.timezone import beijing_now


class UserInvitation(Base):
    """用户邀请链接（管理员生成，一次性使用）"""

    __tablename__ = "user_invitations"

    id = Column(String(50), primary_key=True, index=True)
    token = Column(String(100), unique=True, nullable=False, index=True)
    created_by = Column(String(50), nullable=False)
    used_by = Column(String(50), nullable=True)
    is_used = Column(Boolean, default=False)
    company_name = Column(String(100), nullable=True)
    memory_user_id = Column(String(50), nullable=True)
    note = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=beijing_now)

    def __repr__(self):
        return f"<UserInvitation(id={self.id}, used={self.is_used})>"
