import pytest
from fastapi import HTTPException

from app.services.staff_phone_service import (
    normalize_staff_phone,
    validate_staff_phone_for_active_staff,
)


def test_normalize_staff_phone_removes_common_separators():
    assert normalize_staff_phone(" 138 0000-0001 ") == "13800000001"


def test_validate_active_staff_requires_phone():
    with pytest.raises(HTTPException) as exc:
        validate_staff_phone_for_active_staff("", is_active=True)

    assert exc.value.status_code == 400
    assert exc.value.detail == "启用负责人必须填写手机号"


def test_validate_active_staff_rejects_invalid_china_mobile_number():
    with pytest.raises(HTTPException) as exc:
        validate_staff_phone_for_active_staff("12345", is_active=True)

    assert exc.value.status_code == 400
    assert exc.value.detail == "请输入有效的11位手机号"


def test_validate_inactive_staff_allows_missing_phone():
    assert validate_staff_phone_for_active_staff(None, is_active=False) is None
