from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from app.api import website_analytics as api
from app.database import get_db
from app.services.website_analytics_service import WebsiteIpGeoResolveResult
from app.utils.dependencies import require_internal_admin


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected_days", [("", 7), ("?days=30", 30), ("?days=0", None), ("?days=91", None)])
async def test_resolve_geo_passes_validated_date_range(monkeypatch, query, expected_days):
    app = FastAPI()
    app.include_router(api.router)
    db = object()

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_internal_admin] = lambda: SimpleNamespace(id="admin-test")
    resolve = AsyncMock(return_value=WebsiteIpGeoResolveResult(1, 1, 0, 1, 0, 0, 2, 0))
    monkeypatch.setattr(api.analytics_service, "resolve_unresolved_geos", resolve)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/website-analytics/admin/website-visits/resolve-geo" + query)

    if expected_days is None:
        assert response.status_code == 422
        resolve.assert_not_awaited()
    else:
        assert response.status_code == 200
        assert response.json()["data"]["updated_events"] == 2
        resolve.assert_awaited_once_with(db, days=expected_days)
