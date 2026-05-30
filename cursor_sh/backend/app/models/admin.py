"""管理员模型"""

from sqlalchemy import Column, String, Boolean, DateTime
import enum
from app.database import Base
from app.utils.timezone import beijing_now


class Admin(Base):
    """管理员模型（独立存储，与 staff/user 完全隔离）"""
    __tablename__ = "admins"
    
    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), index=True)
    phone = Column(String(20), unique=True, index=True)  # 手机号
    real_name = Column(String(50))
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)
    
    @property
    def role(self):
        """固定返回 admin 角色（兼容现有代码中 user.role 的用法）"""
        from app.models.user import UserRole
        return UserRole.ADMIN
    
    def __repr__(self):
        return f"<Admin(id={self.id}, username={self.username})>"
