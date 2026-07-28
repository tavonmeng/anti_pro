"""Schemas for website visit analytics."""

from pydantic import BaseModel, Field


class WebsiteVisitTrackRequest(BaseModel):
    path: str = Field("/", max_length=500)
    referrer: str | None = Field(None, max_length=1000)


class WebsiteVisitTrackResponse(BaseModel):
    counted: bool
    deduped: bool
    path: str


class WebsiteIpGeoResolveResponse(BaseModel):
    candidate_unique_ips: int
    processed_unique_ips: int
    cache_hits: int
    resolved: int
    unavailable: int
    failed: int
    updated_events: int


class WebsiteVisitTotalsResponse(BaseModel):
    today_pv: int
    today_uv: int
    yesterday_pv: int
    yesterday_uv: int
    range_pv: int
    range_uv: int
    days: int


class WebsiteVisitDailyRow(BaseModel):
    date: str
    pv: int
    uv: int


class WebsiteVisitPathRow(BaseModel):
    path: str
    pv: int
    uv: int


class WebsiteVisitEventRow(BaseModel):
    id: str
    visited_at: str
    ip_address: str
    path: str
    referrer: str | None = None
    user_agent: str | None = None
    counted_for_pv: bool
    deduped: bool
    country: str | None = None
    province: str | None = None
    city: str | None = None
    geo_status: str


class WebsiteVisitSummaryResponse(BaseModel):
    totals: WebsiteVisitTotalsResponse
    daily: list[WebsiteVisitDailyRow]
    paths: list[WebsiteVisitPathRow]
    recent_events: list[WebsiteVisitEventRow]
