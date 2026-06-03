"""阿里云号码认证服务 (Dypnsapi) - 短信验证码

使用 SendSmsVerifyCode 发送验证码（阿里云自动生成验证码，##code## 占位符）
使用 CheckSmsVerifyCode 校验验证码（阿里云端校验）
"""

import time
import random
import string
import json
from typing import Dict, Tuple

from fastapi import HTTPException, status

from app.config import settings
from app.utils.business_log import log_business_event
from app.utils.log_setup import get_module_logger
from app.utils.retry import retry_sync


logger = get_module_logger("auth")


# ============ 内存验证码缓存（仅本地测试模式使用） ============
_sms_code_cache: Dict[str, Tuple[str, float]] = {}
# 发送频率限制
_sms_rate_limit: Dict[str, float] = {}
SMS_SEND_INTERVAL = 60


def _generate_code(length: int = 6) -> str:
    """生成数字验证码（仅本地测试用）"""
    return ''.join(random.choices(string.digits, k=length))


def _check_rate_limit(phone: str) -> None:
    """检查发送频率"""
    last_send = _sms_rate_limit.get(phone, 0)
    elapsed = time.time() - last_send
    if elapsed < SMS_SEND_INTERVAL:
        remaining = int(SMS_SEND_INTERVAL - elapsed)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请 {remaining} 秒后重试"
        )


def _can_use_cloud() -> bool:
    """判断是否可以调用阿里云接口"""
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
        "check frequency" in text
        or "too frequent" in text
        or ("frequency" in text and ("fail" in text or "limit" in text))
        or ("频繁" in text)
    )


async def send_sms_verify_code(phone: str) -> dict:
    """发送短信验证码"""
    _check_rate_limit(phone)

    if not phone or len(phone) != 11 or not phone.startswith('1'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入有效的11位手机号"
        )

    if _can_use_cloud():
        return await _send_via_dypnsapi(phone)
    else:
        return _send_local(phone)


async def _send_via_dypnsapi(phone: str) -> dict:
    """
    通过阿里云 Dypnsapi SendSmsVerifyCode 发送验证码。
    
    关键：template_param 中的 ##code## 由阿里云自动替换为生成的验证码，
    我们不需要自己生成验证码。校验也由阿里云 CheckSmsVerifyCode 完成。
    """
    try:
        from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
        from alibabacloud_tea_util import models as util_models

        config = open_api_models.Config(
            access_key_id=settings.SMS_ACCESS_KEY_ID,
            access_key_secret=settings.SMS_ACCESS_KEY_SECRET,
        )
        config.endpoint = 'dypnsapi.aliyuncs.com'
        client = DypnsapiClient(config)

        # 完全对齐用户提供的参考代码
        request = dypnsapi_models.SendSmsVerifyCodeRequest(
            sign_name=settings.SMS_SIGN_NAME,
            template_code=settings.SMS_TEMPLATE_CODE,
            phone_number=phone,
            template_param=json.dumps({
                "code": "##code##",
                "min": str(settings.SMS_VALID_TIME // 60)
            }),
            code_length=settings.SMS_CODE_LENGTH,
            valid_time=settings.SMS_VALID_TIME,
        )

        runtime = util_models.RuntimeOptions()
        resp = retry_sync(
            lambda: client.send_sms_verify_code_with_options(request, runtime),
            logger=logger,
            event="sms_send_provider_call",
            attempts=settings.SMS_RETRY_ATTEMPTS,
            fields={"phone": phone, "provider": "aliyun"},
        )

        body = resp.body
        if body and body.code == "OK":
            _sms_rate_limit[phone] = time.time()
            log_business_event(logger, "sms_sent", phone=phone, provider="aliyun")
            return {"success": True, "message": "验证码已发送"}
        else:
            error_msg = body.message if body else "未知错误"
            error_code = getattr(body, "code", None) if body else None
            is_frequency_limited = _is_frequency_limited_error(error_code, error_msg)
            log_business_event(
                logger,
                "sms_send_failed",
                level="warning" if is_frequency_limited else "error",
                phone=phone,
                provider="aliyun",
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
        is_frequency_limited = _is_frequency_limited_error(e)
        log_business_event(
            logger,
            "sms_send_failed",
            level="warning" if is_frequency_limited else "error",
            phone=phone,
            provider="aliyun",
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


def _send_local(phone: str) -> dict:
    """本地测试模式：生成验证码存内存"""
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
    """
    校验短信验证码。
    
    Args:
        phone: 手机号
        code: 验证码
        consume: 是否消耗验证码（预校验时传 False，正式注册时传 True）
    
    云端模式：调用阿里云 CheckSmsVerifyCode（阿里云端存储和校验）
    本地模式：校验内存缓存
    
    注意：阿里云 CheckSmsVerifyCode 每次调用都会消耗验证码，
    因此预校验（consume=False）时仅做格式检查，不调用云端接口，
    避免验证码在注册前就被消耗掉。
    """
    if _can_use_cloud():
        if not consume:
            # 预校验模式：不调用阿里云（会消耗验证码），只做基本格式检查
            # 真正的校验在 register 时 consume=True 才执行
            return bool(code and len(code) == settings.SMS_CODE_LENGTH and code.isdigit())
        return await _verify_via_dypnsapi(phone, code)
    else:
        return _verify_local(phone, code, consume=consume)


async def _verify_via_dypnsapi(phone: str, code: str) -> bool:
    """通过阿里云 Dypnsapi CheckSmsVerifyCode 校验"""
    try:
        from alibabacloud_dypnsapi20170525.client import Client as DypnsapiClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_dypnsapi20170525 import models as dypnsapi_models
        from alibabacloud_tea_util import models as util_models

        config = open_api_models.Config(
            access_key_id=settings.SMS_ACCESS_KEY_ID,
            access_key_secret=settings.SMS_ACCESS_KEY_SECRET,
        )
        config.endpoint = 'dypnsapi.aliyuncs.com'
        client = DypnsapiClient(config)

        request = dypnsapi_models.CheckSmsVerifyCodeRequest(
            phone_number=phone,
            verify_code=code,
        )

        runtime = util_models.RuntimeOptions()
        resp = retry_sync(
            lambda: client.check_sms_verify_code_with_options(request, runtime),
            logger=logger,
            event="sms_verify_provider_call",
            attempts=settings.SMS_RETRY_ATTEMPTS,
            fields={"phone": phone, "provider": "aliyun"},
        )

        body = resp.body
        if body and body.code == "OK":
            if body.model and body.model.verify_result:
                log_business_event(logger, "sms_verified", phone=phone, provider="aliyun")
                return True
        
        log_business_event(logger, "sms_verify_failed", level="warning", phone=phone, provider="aliyun")
        return False
    except Exception as e:
        error_text = str(e)
        if "ValidateFail" in error_text or "验证失败" in error_text:
            log_business_event(
                logger,
                "sms_verify_failed",
                level="warning",
                phone=phone,
                provider="aliyun",
                reason="validate_fail",
            )
            return False
        log_business_event(
            logger,
            "sms_verify_failed",
            level="error",
            phone=phone,
            provider="aliyun",
            error=error_text,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="短信验证服务暂时不可用，请稍后重试"
        )


def _verify_local(phone: str, code: str, consume: bool = True) -> bool:
    """本地校验"""
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
