"""短信验证码记录。"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base
from app.utils.timezone import beijing_now


class SmsVerificationCode(Base):
    """Store SMS verification codes across backend workers without plaintext codes."""

    __tablename__ = "sms_verification_codes"

    id = Column(String(50), primary_key=True, index=True)
    phone = Column(String(20), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    provider = Column(String(30), nullable=False, default="aliyun_dysmsapi")
    send_status = Column(String(30), nullable=False, default="sent", index=True)
    consumed = Column(Boolean, nullable=False, default=False, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=beijing_now, index=True)

