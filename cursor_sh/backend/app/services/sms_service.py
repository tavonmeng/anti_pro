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


async def send_sms_verify_code(phone: str) -> dict:
    """发送短信验证码"""
    _check_rate_limit(phone)

    if not phone or len(phone) != 11 or not phone.startswith('1'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入有效的11位手机号"
        )

    _sms_rate_limit[phone] = time.time()

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
        resp = client.send_sms_verify_code_with_options(request, runtime)

        body = resp.body
        if body and body.code == "OK":
            print(f"✅ 短信验证码已通过阿里云发送至 {phone[:3]}****{phone[7:]}")
            return {"success": True, "message": "验证码已发送"}
        else:
            error_msg = body.message if body else "未知错误"
            print(f"❌ 阿里云短信发送失败: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"短信发送失败: {error_msg}"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 阿里云短信服务异常: {str(e)}")
        # 回退到本地模式
        print("⚠️ 回退到本地验证码模式")
        return _send_local(phone)


def _send_local(phone: str) -> dict:
    """本地测试模式：生成验证码存内存"""
    code = _generate_code(settings.SMS_CODE_LENGTH)
    expire_at = time.time() + settings.SMS_VALID_TIME
    _sms_code_cache[phone] = (code, expire_at)
    print(f"📱 [本地测试] 手机号 {phone} 的验证码是: {code} (有效期 {settings.SMS_VALID_TIME}秒)")
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
    """
    if _can_use_cloud():
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
        resp = client.check_sms_verify_code_with_options(request, runtime)

        body = resp.body
        if body and body.code == "OK":
            if body.model and body.model.verify_result:
                print(f"✅ 验证码校验通过: {phone[:3]}****{phone[7:]}")
                return True
        
        print(f"❌ 验证码校验失败: {phone}")
        return False
    except Exception as e:
        print(f"❌ 阿里云验证码校验异常: {str(e)}")
        # 回退到本地校验
        return _verify_local(phone, code)


def _verify_local(phone: str, code: str, consume: bool = True) -> bool:
    """本地校验"""
    cached = _sms_code_cache.get(phone)
    if not cached:
        return False
    stored_code, expire_at = cached
    if time.time() > expire_at:
        del _sms_code_cache[phone]
        return False
    if stored_code == code:
        if consume:
            del _sms_code_cache[phone]
        return True
    return False
