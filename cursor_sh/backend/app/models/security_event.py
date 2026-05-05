"""安全事件模型 — 记录注册/登录等关键操作的行为数据，用于反灰产分析"""

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, Enum
from sqlalchemy.sql import func
import enum
from app.database import Base


class SecurityEventType(str, enum.Enum):
    """安全事件类型"""
    REGISTER_SUCCESS = "register_success"       # 注册成功
    REGISTER_FAIL = "register_fail"             # 注册失败
    REGISTER_BOT_BLOCKED = "register_bot_blocked"  # 注册被反机器人拦截
    LOGIN_SUCCESS = "login_success"             # 登录成功
    LOGIN_FAIL = "login_fail"                   # 登录失败
    PASSWORD_RESET = "password_reset"           # 密码重置
    SMS_SENT = "sms_sent"                       # 短信发送


class SecurityEvent(Base):
    """安全事件记录表
    
    每一次注册/登录尝试（无论成败）都会记录一条记录。
    用于：
    - 同 IP 批量注册检测
    - 行为时序异常检测（注册机识别）
    - 登录异地检测
    - 灰产账号聚类分析
    """
    __tablename__ = "security_events"
    
    id = Column(String(50), primary_key=True, index=True)
    event_type = Column(Enum(SecurityEventType), nullable=False, index=True)
    
    # 关联用户（注册失败时可能为空）
    user_id = Column(String(50), index=True)
    phone = Column(String(20), index=True)
    username = Column(String(50))
    
    # 客户端指纹
    client_ip = Column(String(50), index=True)
    user_agent = Column(String(500))
    
    # 行为时序数据（注册事件专用）
    behavior_data = Column(JSON)
    # 存储结构：
    # {
    #   "page_loaded_at": 1714400000000,
    #   "phone_first_input_at": 1714400003000,
    #   "sms_sent_at": 1714400010000,
    #   "sms_input_at": 1714400075000,
    #   "username_first_input_at": 1714400080000,
    #   "email_first_input_at": 1714400090000,
    #   "password_first_input_at": 1714400095000,
    #   "submit_clicked_at": 1714400105000,
    #   "total_duration_sec": 105.0,
    #   "field_focus_count": 12,
    #   "key_press_count": 87,
    # }
    
    # 拦截原因（仅 bot_blocked 事件）
    block_reason = Column(String(200))
    
    # 失败原因（仅 fail 事件）
    fail_reason = Column(String(200))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, type={self.event_type}, ip={self.client_ip}, phone={self.phone})>"
