"""用户模型"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    USER = "user"
    STAFF = "staff"


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), index=True)
    phone = Column(String(20), unique=True, index=True)  # 手机号
    role = Column(Enum(UserRole), nullable=False)
    real_name = Column(String(50))
    company = Column(String(100))
    address = Column(String(255))
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

