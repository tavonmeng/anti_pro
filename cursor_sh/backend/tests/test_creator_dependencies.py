import pytest
from fastapi import HTTPException

from app.models.user import UserRole
from app.utils.dependencies import require_creator


class _Actor:
    def __init__(self, role):
        self.role = role


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.STAFF, UserRole.CONTRACTOR, "staff", "contractor"])
async def test_require_creator_allows_staff_and_contractor(role):
    actor = _Actor(role)

    assert await require_creator(actor) is actor


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.USER, "admin", "user"])
async def test_require_creator_blocks_non_creator_roles(role):
    with pytest.raises(HTTPException) as exc:
        await require_creator(_Actor(role))

    assert exc.value.status_code == 403
    assert exc.value.detail == "权限不足，仅制作者可执行此操作"
