from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.config import settings
from app.models.website_analytics import WebsiteIpGeoCache, WebsiteVisitEvent
from app.services.ip_geolocation_service import IpGeoResult
from app.services.website_analytics_service import (
    WebsiteAnalyticsService,
    WebsiteVisitInput,
    normalize_visit_path,
)


@pytest_asyncio.fixture
async def analytics_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_track_visit_debounces_same_ip_and_path_within_window(analytics_db):
    service = WebsiteAnalyticsService(debounce_seconds=10)
    now = datetime(2026, 7, 9, 10, 0, 0)
    visit = WebsiteVisitInput(
        path="/?utm_source=test",
        ip_address="203.0.113.8",
        user_agent="Mozilla/5.0",
        referrer=None,
    )

    first = await service.track_visit(analytics_db, visit, now=now)
    second = await service.track_visit(analytics_db, visit, now=now + timedelta(seconds=5))
    summary = await service.get_summary(analytics_db, days=1, now=now)

    assert first.counted is True
    assert first.deduped is False
    assert second.counted is False
    assert second.deduped is True
    assert summary.totals.today_pv == 1
    assert summary.totals.today_uv == 1
    assert summary.daily == [{"date": date(2026, 7, 9), "pv": 1, "uv": 1}]
    assert summary.paths == [{"path": "/", "pv": 1, "uv": 1}]
    assert [
        (event["ip_address"], event["path"], event["counted_for_pv"], event["deduped"], event["geo_status"])
        for event in summary.recent_events
    ] == [
        ("203.0.113.8", "/", False, True, "pending"),
        ("203.0.113.8", "/", True, False, "pending"),
    ]

    events_result = await analytics_db.execute(
        select(WebsiteVisitEvent).order_by(WebsiteVisitEvent.visited_at.asc())
    )
    events = events_result.scalars().all()
    assert len(events) == 2
    assert [event.ip_address for event in events] == ["203.0.113.8", "203.0.113.8"]
    assert [event.path for event in events] == ["/", "/"]
    assert [event.counted_for_pv for event in events] == [True, False]
    assert [event.deduped for event in events] == [False, True]
    assert [event.geo_status for event in events] == ["pending", "pending"]


@pytest.mark.asyncio
async def test_track_visit_counts_later_pv_without_repeating_uv(analytics_db):
    service = WebsiteAnalyticsService(debounce_seconds=10)
    now = datetime(2026, 7, 9, 10, 0, 0)
    visit = WebsiteVisitInput(
        path="/cases",
        ip_address="203.0.113.9",
        user_agent="Mozilla/5.0",
        referrer=None,
    )

    await service.track_visit(analytics_db, visit, now=now)
    later = await service.track_visit(analytics_db, visit, now=now + timedelta(seconds=11))
    summary = await service.get_summary(analytics_db, days=1, now=now + timedelta(seconds=11))

    assert later.counted is True
    assert later.deduped is False
    assert summary.totals.today_pv == 2
    assert summary.totals.today_uv == 1
    assert summary.paths == [{"path": "/cases", "pv": 2, "uv": 1}]


def test_normalize_visit_path_strips_host_query_and_hash():
    assert normalize_visit_path("https://www.uniquevisionx.com/cases?utm_source=a#intro") == "/cases"
    assert normalize_visit_path("/workspace?invite=secret") == "/workspace"
    assert normalize_visit_path("") == "/"


class FakeIpGeolocation:
    def __init__(self, result: IpGeoResult):
        self.result = result
        self.calls: list[str] = []

    def lookup(self, ip_address: str) -> IpGeoResult:
        self.calls.append(ip_address)
        return self.result


@pytest.mark.asyncio
async def test_manual_geo_resolution_deduplicates_today_and_reuses_cache(analytics_db):
    service = WebsiteAnalyticsService(debounce_seconds=10)
    now = datetime(2026, 7, 9, 10, 0, 0)
    geo = FakeIpGeolocation(IpGeoResult("中国", "广东省", "深圳市", "done"))

    for path in ("/", "/cases"):
        await service.track_visit(
            analytics_db,
            WebsiteVisitInput(path=path, ip_address="113.118.113.77"),
            now=now,
        )

    first = await service.resolve_today_unresolved_geos(analytics_db, geolocation=geo, now=now)

    assert first.candidate_unique_ips == 1
    assert first.processed_unique_ips == 1
    assert first.cache_hits == 0
    assert first.resolved == 1
    assert first.updated_events == 2
    assert geo.calls == ["113.118.113.77"]

    await service.track_visit(
        analytics_db,
        WebsiteVisitInput(path="/contact", ip_address="113.118.113.77"),
        now=now + timedelta(seconds=11),
    )
    second = await service.resolve_today_unresolved_geos(
        analytics_db,
        geolocation=geo,
        now=now + timedelta(seconds=11),
    )

    assert second.cache_hits == 1
    assert second.resolved == 0
    assert second.updated_events == 1
    assert geo.calls == ["113.118.113.77"]

    cache_result = await analytics_db.execute(select(WebsiteIpGeoCache))
    cache = cache_result.scalars().all()
    assert [(item.ip_address, item.country, item.city, item.status) for item in cache] == [
        ("113.118.113.77", "中国", "深圳市", "done")
    ]

    events_result = await analytics_db.execute(select(WebsiteVisitEvent).order_by(WebsiteVisitEvent.path))
    events = events_result.scalars().all()
    assert all(event.geo_status == "done" for event in events)
    assert all(event.province == "广东省" for event in events)


@pytest.mark.asyncio
async def test_manual_geo_resolution_evicts_least_recent_cache_when_full(analytics_db, monkeypatch):
    monkeypatch.setattr(settings, "IP_GEO_CACHE_LIMIT", 1)
    service = WebsiteAnalyticsService(debounce_seconds=10)
    now = datetime(2026, 7, 9, 10, 0, 0)
    geo = FakeIpGeolocation(IpGeoResult("中国", "广东省", "深圳市", "done"))

    await service.track_visit(
        analytics_db,
        WebsiteVisitInput(path="/", ip_address="113.118.113.77"),
        now=now,
    )
    await service.resolve_today_unresolved_geos(analytics_db, geolocation=geo, now=now)

    await service.track_visit(
        analytics_db,
        WebsiteVisitInput(path="/cases", ip_address="8.8.8.8"),
        now=now + timedelta(seconds=11),
    )
    result = await service.resolve_today_unresolved_geos(
        analytics_db,
        geolocation=geo,
        now=now + timedelta(seconds=11),
    )

    assert result.evicted_cache_entries == 1
    cache_result = await analytics_db.execute(select(WebsiteIpGeoCache))
    cache = cache_result.scalars().all()
    assert [item.ip_address for item in cache] == ["8.8.8.8"]
