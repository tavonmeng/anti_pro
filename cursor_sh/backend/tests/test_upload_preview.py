import pytest

from app.api import upload as upload_api
from app.models.user import UserRole
from app.services import oss_service


class _FakeUser:
    id = "user-1"
    role = UserRole.ADMIN


class _FakeDb:
    pass


@pytest.mark.asyncio
async def test_pdf_preview_response_streams_inline_pdf(monkeypatch):
    monkeypatch.setattr(upload_api.settings, "OSS_ENABLED", True)

    async def can_access(*_):
        return True

    monkeypatch.setattr(upload_api, "_can_access_object_key", can_access)
    monkeypatch.setattr(
        oss_service,
        "iter_object_bytes",
        lambda key: iter([b"%PDF-1.7"]),
        raising=False,
    )

    response = await upload_api.preview_pdf(
        key="site_photos/user-1/demo.pdf",
        filename="演播说明.pdf",
        current_user=_FakeUser(),
        db=_FakeDb(),
    )

    assert response.media_type == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline;")
    assert "filename*=UTF-8''" in response.headers["content-disposition"]
