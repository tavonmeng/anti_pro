"""负责人手机号校验工具。"""

import re
from typing import Optional

from fastapi import HTTPException


def normalize_staff_phone(phone: Optional[str]) -> Optional[str]:
    """去掉手机号里常见的展示分隔符。"""
    if phone is None:
        return None
    normalized = re.sub(r"[\s-]+", "", phone)
    return normalized or None


def validate_staff_phone_for_active_staff(phone: Optional[str], is_active: bool = True) -> Optional[str]:
    """启用负责人必须有可用于短信登录的中国大陆手机号。"""
    normalized = normalize_staff_phone(phone)
    if not normalized:
        if is_active:
            raise HTTPException(status_code=400, detail="启用负责人必须填写手机号")
        return None

    if len(normalized) != 11 or not normalized.startswith("1") or not normalized.isdigit():
        raise HTTPException(status_code=400, detail="请输入有效的11位手机号")

    return normalized
