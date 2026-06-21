"""阿里云短信服务 (Dysmsapi) - 短信验证码。

使用 SendSms 发送短信模板，验证码由后端生成、保存和校验。
"""

from __future__ import annotations

import hashlib
import json
import random
import string
import time
import uuid
from datetime import timedelta
from typing import Dict, Tuple

from fastapi import HTTPException, status
from sqlalchemy import desc, select

from app.config import settings
from app.database import async_session_maker
from app.models.sms_verification import SmsVerificationCode
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.retry import retry_sync
from app.utils.timezone import beijing_now, ensure_beijing


logger = get_module_logger("auth")


# ============ 内存验证码缓存（仅本地测试模式使用） ============
_sms_code_cache: Dict[str, Tuple[str, float]] = {}
# 发送频率限制（本地测试模式使用；云端模式以数据库记录限制）
_sms_rate_limit: Dict[str, float] = {}
SMS_SEND_INTERVAL = 60


def _generate_code(length: int = 6) -> str:
    """生成数字验证码。"""
    return ''.join(random.choices(string.digits, k=length))


def _hash_code(phone: str, code: str) -> str:
    raw = f"{settings.SECRET_KEY}:{phone}:{code}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _check_rate_limit_local(phone: str) -> None:
    """检查本地测试模式发送频率。"""
    last_send = _sms_rate_limit.get(phone, 0)
    elapsed = time.time() - last_send
    if elapsed < SMS_SEND_INTERVAL:
        remaining = int(SMS_SEND_INTERVAL - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请 {remaining} 秒后重试"
        )


async def _check_rate_limit_cloud(phone: str) -> None:
    cutoff = beijing_now() - timedelta(seconds=SMS_SEND_INTERVAL)
    async with async_session_maker() as db:
        result = await db.execute(
            select(SmsVerificationCode)
            .where(
                SmsVerificationCode.phone == phone,
                SmsVerificationCode.send_status == "sent",
                SmsVerificationCode.created_at >= cutoff,
            )
            .order_by(desc(SmsVerificationCode.created_at))
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if not latest:
            return
        created_at = ensure_beijing(latest.created_at)
        if not created_at:
            return
        remaining = int(SMS_SEND_INTERVAL - (beijing_now() - created_at).total_seconds())
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"发送过于频繁，请 {remaining} 秒后重试"
            )


def _can_use_cloud() -> bool:
    """判断是否可以调用阿里云短信服务。"""
    return bool(
        settings.SMS_ENABLED
        and settings.SMS_ACCESS_KEY_ID
        and settings.SMS_ACCESS_KEY_SECRET
        and settings.SMS_SIGN_NAME
        and settings.SMS_TEMPLATE_CODE
    )


def _is_frequency_limited_error(*values) -> bool:
    """Return True for provider messages that mean the SMS send was rate-limited."""
    text = " ".join(str(value).lower() for value in values if value)
    return (
        "isv.businesslimitcontrol" in text
        or "businesslimitcontrol" in text
        or "check frequency" in text
        or "too frequent" in text
        or ("frequency" in text and ("fail" in text or "limit" in text))
        or "触发天级流控" in text
        or "流控" in text
        or "频繁" in text
    )


async def send_sms_verify_code(phone: str) -> dict:
    """发送短信验证码。"""
    if not phone or len(phone) != 11 or not phone.startswith('1'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入有效的11位手机号"
        )

    if _can_use_cloud():
        await _check_rate_limit_cloud(phone)
        return await _send_via_dysmsapi(phone)

    _check_rate_limit_local(phone)
    return _send_local(phone)


async def _send_via_dysmsapi(phone: str) -> dict:
    """通过阿里云 Dysmsapi SendSms 发送验证码短信。"""
    code = _generate_code(settings.SMS_CODE_LENGTH)
    record = SmsVerificationCode(
        id=f"sms_{uuid.uuid4().hex}",
        phone=phone,
        code_hash=_hash_code(phone, code),
        provider="aliyun_dysmsapi",
        send_status="pending",
        consumed=False,
        attempts=0,
        expires_at=beijing_now() + timedelta(seconds=settings.SMS_VALID_TIME),
        created_at=beijing_now(),
    )

    async with async_session_maker() as db:
        db.add(record)
        await db.commit()

    try:
        from alibabacloud_dysmsapi20170525.client import Client as DysmsapiClient
        from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_tea_util import models as util_models

        config = open_api_models.Config(
            access_key_id=settings.SMS_ACCESS_KEY_ID,
            access_key_secret=settings.SMS_ACCESS_KEY_SECRET,
            region_id=settings.SMS_REGION_ID,
        )
        config.endpoint = "dysmsapi.aliyuncs.com"
        client = DysmsapiClient(config)

        request = dysmsapi_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=settings.SMS_SIGN_NAME,
            template_code=settings.SMS_TEMPLATE_CODE,
            template_param=json.dumps({"code": code}, ensure_ascii=False),
        )

        runtime = util_models.RuntimeOptions()
        resp = retry_sync(
            lambda: client.send_sms_with_options(request, runtime),
            logger=logger,
            event="sms_send_provider_call",
            attempts=settings.SMS_RETRY_ATTEMPTS,
            fields={"phone": phone, "provider": "aliyun_dysmsapi"},
        )

        body = resp.body
        if body and body.code == "OK":
            async with async_session_maker() as db:
                saved = await db.get(SmsVerificationCode, record.id)
                if saved:
                    saved.send_status = "sent"
                    await db.commit()
            _sms_rate_limit[phone] = time.time()
            log_business_event(logger, "sms_sent", phone=phone, provider="aliyun_dysmsapi")
            return {"success": True, "message": "验证码已发送"}

        error_msg = body.message if body else "未知错误"
        error_code = getattr(body, "code", None) if body else None
        await _mark_send_failed(record.id)
        is_frequency_limited = _is_frequency_limited_error(error_code, error_msg)
        log_business_event(
            logger,
            "sms_send_failed",
            level="warning" if is_frequency_limited else "error",
            phone=phone,
            provider="aliyun_dysmsapi",
            provider_result=error_code,
            error=error_msg,
        )
        if is_frequency_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="验证码发送频繁，请稍后重试"
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="短信发送失败，请稍后重试"
        )
    except HTTPException:
        raise
    except Exception as e:
        await _mark_send_failed(record.id)
        is_frequency_limited = _is_frequency_limited_error(e)
        log_business_event(
            logger,
            "sms_send_failed",
            level="warning" if is_frequency_limited else "error",
            phone=phone,
            provider="aliyun_dysmsapi",
            error=str(e),
        )
        if is_frequency_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="验证码发送频繁，请稍后重试"
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="短信服务暂时不可用，请稍后重试"
        )


async def _mark_send_failed(record_id: str) -> None:
    async with async_session_maker() as db:
        saved = await db.get(SmsVerificationCode, record_id)
        if saved:
            saved.send_status = "failed"
            await db.commit()


def _send_local(phone: str) -> dict:
    """本地测试模式：生成验证码存内存。"""
    code = _generate_code(settings.SMS_CODE_LENGTH)
    expire_at = time.time() + settings.SMS_VALID_TIME
    _sms_code_cache[phone] = (code, expire_at)
    _sms_rate_limit[phone] = time.time()
    log_business_event(
        logger,
        "sms_sent",
        phone=phone,
        provider="local",
        valid_seconds=settings.SMS_VALID_TIME,
    )
    return {"success": True, "message": "验证码已发送（测试模式）"}


async def verify_sms_code(phone: str, code: str, consume: bool = True) -> bool:
    """校验短信验证码。"""
    if _can_use_cloud():
        return await _verify_cloud_code(phone, code, consume=consume)
    return _verify_local(phone, code, consume=consume)


async def _verify_cloud_code(phone: str, code: str, consume: bool = True) -> bool:
    if not phone or not code:
        return False

    now = beijing_now()
    async with async_session_maker() as db:
        result = await db.execute(
            select(SmsVerificationCode)
            .where(
                SmsVerificationCode.phone == phone,
                SmsVerificationCode.send_status == "sent",
                SmsVerificationCode.consumed.is_(False),
                SmsVerificationCode.expires_at >= now,
            )
            .order_by(desc(SmsVerificationCode.created_at))
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if not record:
            log_business_event(logger, "sms_verify_failed", level="warning", phone=phone, provider="aliyun_dysmsapi", reason="not_found")
            return False

        record.attempts = int(record.attempts or 0) + 1
        if record.code_hash != _hash_code(phone, code):
            await db.commit()
            log_business_event(logger, "sms_verify_failed", level="warning", phone=phone, provider="aliyun_dysmsapi", reason="mismatch")
            return False

        if consume:
            record.consumed = True
            record.consumed_at = now
        await db.commit()
        log_business_event(logger, "sms_verified", phone=phone, provider="aliyun_dysmsapi", consume=consume)
        return True


def _verify_local(phone: str, code: str, consume: bool = True) -> bool:
    """本地校验。"""
    cached = _sms_code_cache.get(phone)
    if not cached:
        log_business_event(logger, "sms_verify_failed", level="warning", phone=phone, provider="local", reason="not_found")
        return False
    stored_code, expire_at = cached
    if time.time() > expire_at:
        del _sms_code_cache[phone]
        log_business_event(logger, "sms_verify_failed", level="warning", phone=phone, provider="local", reason="expired")
        return False
    if stored_code == code:
        if consume:
            del _sms_code_cache[phone]
        log_business_event(logger, "sms_verified", phone=phone, provider="local", consume=consume)
        return True
    log_business_event(logger, "sms_verify_failed", level="warning", phone=phone, provider="local", reason="mismatch")
    return False

