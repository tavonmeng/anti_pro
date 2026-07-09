from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.website_analytics import WebsiteVisitEvent
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
    assert normalize_visit_path("https://uniquevisionx.com/cases?utm_source=a#intro") == "/cases"
    assert normalize_visit_path("/workspace?invite=secret") == "/workspace"
    assert normalize_visit_path("") == "/"
