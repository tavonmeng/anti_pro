"""承包商一次性邀请链接模型"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class ContractorInvitation(Base):
    """承包商邀请链接（管理员生成，一次性使用）"""
    __tablename__ = "contractor_invitations"

    id = Column(String(50), primary_key=True, index=True)
    token = Column(String(100), unique=True, nullable=False, index=True)   # 一次性 token
    created_by = Column(String(50), nullable=False)                         # 生成该链接的管理员 ID
    used_by = Column(String(50), nullable=True)                             # 使用该链接注册的 contractor ID
    is_used = Column(Boolean, default=False)
    note = Column(String(500))                                              # 管理员备注（如：给 XX 公司的邀请）
    expires_at = Column(DateTime(timezone=True), nullable=False)            # 过期时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ContractorInvitation(id={self.id}, used={self.is_used})>"
