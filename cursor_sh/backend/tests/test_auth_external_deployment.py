import pytest
from fastapi import HTTPException

from app.models.admin import Admin
from app.models.contractor import Contractor
from app.models.staff_member import StaffMember
from app.models.user import User, UserRole
from app.services import auth_service


def test_external_deployment_allows_user_auth(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "DEPLOYMENT_MODE", "external")

    auth_service._ensure_role_allowed_for_deployment(UserRole.USER)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.STAFF, UserRole.CONTRACTOR])
def test_external_deployment_blocks_internal_role_auth(monkeypatch, role):
    monkeypatch.setattr(auth_service.settings, "DEPLOYMENT_MODE", "external")
    monkeypatch.setattr(auth_service, "log_business_event", lambda *_, **__: None)

    with pytest.raises(HTTPException) as exc:
        auth_service._ensure_role_allowed_for_deployment(role)

    assert exc.value.status_code == 404


def test_internal_deployment_allows_internal_role_auth(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "DEPLOYMENT_MODE", "internal")

    auth_service._ensure_role_allowed_for_deployment(UserRole.ADMIN)


def test_external_password_reset_searches_only_users(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "DEPLOYMENT_MODE", "external")

    assert auth_service._password_reset_models() == [User]


def test_internal_password_reset_searches_all_actor_tables(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "DEPLOYMENT_MODE", "internal")

    assert auth_service._password_reset_models() == [User, Admin, StaffMember, Contractor]
