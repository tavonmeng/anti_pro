"""用户模型（仅存储普通客户）"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    """用户角色枚举（用于 JWT 和权限判断，所有角色共用）"""
    ADMIN = "admin"
    USER = "user"
    STAFF = "staff"


class EnterpriseStatus(str, enum.Enum):
    """企业认证状态枚举"""
    NONE = "none"            # 未提交
    PENDING = "pending"      # 审核中
    APPROVED = "approved"    # 已通过
    REJECTED = "rejected"    # 已拒绝


class User(Base):
    """普通客户模型（独立存储，与 admin/staff 完全隔离）"""
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), index=True)
    phone = Column(String(20), unique=True, index=True)  # 手机号
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    real_name = Column(String(50))
    company = Column(String(100))
    address = Column(String(255))
    avatar = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    # 企业认证相关字段
    enterprise_status = Column(Enum(EnterpriseStatus), nullable=False, default=EnterpriseStatus.NONE, server_default='NONE')
    enterprise_name = Column(String(200))              # 企业名称
    business_license_url = Column(String(500))         # 营业执照图片URL
    enterprise_reject_reason = Column(Text)            # 拒绝原因
    enterprise_submitted_at = Column(DateTime(timezone=True))   # 提交认证时间
    enterprise_reviewed_at = Column(DateTime(timezone=True))    # 审核时间
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role}, enterprise={self.enterprise_status})>"
