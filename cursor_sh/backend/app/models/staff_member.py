"""设计师/负责人模型"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class StaffMember(Base):
    """设计师/负责人模型（独立存储，与 admin/user 完全隔离）"""
    __tablename__ = "staff_members"
    
    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), index=True)
    phone = Column(String(20), unique=True, index=True)  # 手机号
    real_name = Column(String(50))
    company = Column(String(100))
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def role(self):
        """固定返回 staff 角色（兼容现有代码中 user.role 的用法）"""
        from app.models.user import UserRole
        return UserRole.STAFF
    
    def __repr__(self):
        return f"<StaffMember(id={self.id}, username={self.username})>"
