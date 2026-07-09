import pytest
from fastapi import HTTPException

from app.models.user import UserRole
from app.services.order_service import OrderService


class _ContractorUser:
    id = "contractor-1"
    role = UserRole.CONTRACTOR


class _Order:
    def __init__(self, design_plan=None):
        self.design_plan = design_plan


def test_order_detail_rejects_contractor_role():
    with pytest.raises(HTTPException) as exc:
        OrderService._ensure_order_detail_role_allowed(_ContractorUser())

    assert exc.value.status_code == 403
    assert exc.value.detail == "承包商请通过制作任务查看订单信息"


def test_staff_assignment_requires_completed_design_plan():
    with pytest.raises(HTTPException) as exc:
        OrderService._ensure_assignment_design_plan_completed(_Order(design_plan=None))

    assert exc.value.status_code == 400
    assert exc.value.detail == "请先完成AI方案设计"


def test_staff_assignment_allows_completed_design_plan():
    OrderService._ensure_assignment_design_plan_completed(_Order(design_plan={"status": "completed"}))
