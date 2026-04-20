"""审计日志模型（独立存储于 audit.db）"""

from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.audit_database import AuditBase


class AuditLog(AuditBase):
    """操作审计日志"""
    __tablename__ = "operation_logs"

    id = Column(String(50), primary_key=True, index=True)
    trace_id = Column(String(36), index=True, comment="全局追踪 UUID")
    user_id = Column(String(50), index=True, default="anonymous", comment="操作者 ID")
    username = Column(String(50), default="anonymous", comment="操作者用户名")
    type = Column(String(20), nullable=False, index=True, comment="api_call / frontend_action")
    module = Column(String(30), nullable=False, index=True, comment="业务模块: Auth/Order/Workspace/AI 等")
    action = Column(String(200), nullable=False, comment="操作描述")
    ip_address = Column(String(50), comment="客户端 IP")
    user_agent = Column(String(300), comment="浏览器/设备 UA")
    payload = Column(Text, comment="脱敏后的请求参数 JSON")
    response_status = Column(Integer, comment="HTTP 状态码")
    duration_ms = Column(Integer, comment="耗时（毫秒）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, module={self.module}, action={self.action})>"
