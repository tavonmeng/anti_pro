"""Services for public website PV/UV analytics."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import hmac
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.website_analytics import (
    WebsiteVisitDailyStat,
    WebsiteVisitEvent,
    WebsiteVisitPathDailyStat,
    WebsiteVisitUnique,
)
from app.utils.timezone import beijing_now
from app.utils.validators import generate_id


SITE_SCOPE_VALUE = "__all__"
MAX_PATH_LENGTH = 255


@dataclass(frozen=True)
class WebsiteVisitInput:
    path: str | None
    ip_address: str
    user_agent: str | None = None
    referrer: str | None = None


@dataclass(frozen=True)
class WebsiteVisitResult:
    counted: bool
    deduped: bool
    path: str


@dataclass(frozen=True)
class WebsiteVisitTotals:
    today_pv: int
    today_uv: int
    yesterday_pv: int
    yesterday_uv: int
    range_pv: int
    range_uv: int
    days: int


@dataclass(frozen=True)
class WebsiteVisitSummary:
    totals: WebsiteVisitTotals
    daily: list[dict[str, Any]]
    paths: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "totals": {
                "today_pv": self.totals.today_pv,
                "today_uv": self.totals.today_uv,
                "yesterday_pv": self.totals.yesterday_pv,
                "yesterday_uv": self.totals.yesterday_uv,
                "range_pv": self.totals.range_pv,
                "range_uv": self.totals.range_uv,
                "days": self.totals.days,
            },
            "daily": [
                {"date": row["date"].isoformat(), "pv": row["pv"], "uv": row["uv"]}
                for row in self.daily
            ],
            "paths": self.paths,
            "recent_events": [
                {
                    "id": row["id"],
                    "visited_at": row["visited_at"].isoformat(),
                    "ip_address": row["ip_address"],
                    "path": row["path"],
                    "referrer": row["referrer"],
                    "user_agent": row["user_agent"],
                    "counted_for_pv": row["counted_for_pv"],
                    "deduped": row["deduped"],
                    "country": row["country"],
                    "province": row["province"],
                    "city": row["city"],
                    "geo_status": row["geo_status"],
                }
                for row in self.recent_events
            ],
        }


class WebsiteVisitDebouncer:
    """Small in-process debounce cache to avoid DB writes for rapid refreshes."""

    def __init__(self, debounce_seconds: int = 10, max_keys: int = 50000):
        self.debounce_seconds = max(1, debounce_seconds)
        self.max_keys = max(100, max_keys)
        self._expires_by_key: dict[str, datetime] = {}

    def should_count(self, key: str, now: datetime) -> bool:
        expires_at = self._expires_by_key.get(key)
        if expires_at and expires_at > now:
            return False

        if len(self._expires_by_key) >= self.max_keys:
            self._prune(now)
            if len(self._expires_by_key) >= self.max_keys:
                self._expires_by_key.clear()

        self._expires_by_key[key] = now + timedelta(seconds=self.debounce_seconds)
        return True

    def _prune(self, now: datetime) -> None:
        expired = [key for key, expires_at in self._expires_by_key.items() if expires_at <= now]
        for key in expired:
            self._expires_by_key.pop(key, None)


def normalize_visit_path(path: str | None) -> str:
    """Normalize frontend-reported path without keeping query strings."""
    raw_path = (path or "").strip()
    if not raw_path:
        return "/"

    parsed = urlsplit(raw_path)
    normalized = parsed.path or raw_path.split("?", 1)[0].split("#", 1)[0]
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized[:MAX_PATH_LENGTH] or "/"


def hash_ip_for_date(ip_address: str, visit_date: date) -> str:
    normalized_ip = normalize_ip_address(ip_address).lower()
    message = f"{visit_date.isoformat()}:{normalized_ip}".encode("utf-8")
    secret = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def normalize_ip_address(ip_address: str | None) -> str:
    return ((ip_address or "unknown").split(",", 1)[0].strip() or "unknown")[:64]


class WebsiteAnalyticsService:
    def __init__(self, debounce_seconds: int = 10, debouncer: WebsiteVisitDebouncer | None = None):
        self.debouncer = debouncer or WebsiteVisitDebouncer(debounce_seconds=debounce_seconds)

    async def track_visit(
        self,
        db: AsyncSession,
        visit: WebsiteVisitInput,
        now: datetime | None = None,
    ) -> WebsiteVisitResult:
        current_time = now or beijing_now()
        visit_date = current_time.date()
        path = normalize_visit_path(visit.path)
        ip_address = normalize_ip_address(visit.ip_address)
        ip_hash = hash_ip_for_date(visit.ip_address, visit_date)
        debounce_key = f"{visit_date.isoformat()}:{path}:{ip_hash}"
        should_count = self.debouncer.should_count(debounce_key, current_time)

        await self._record_event(
            db,
            visit=visit,
            visited_at=current_time,
            visit_date=visit_date,
            ip_address=ip_address,
            ip_hash=ip_hash,
            path=path,
            counted_for_pv=should_count,
            deduped=not should_count,
        )
        await db.commit()

        if not should_count:
            return WebsiteVisitResult(counted=False, deduped=True, path=path)

        global_is_new = await self._insert_unique(db, visit_date, "site", SITE_SCOPE_VALUE, ip_hash, current_time)
        path_is_new = await self._insert_unique(db, visit_date, "path", path, ip_hash, current_time)
        await self._upsert_daily_stat(db, visit_date, pv_increment=1, uv_increment=1 if global_is_new else 0, now=current_time)
        await self._upsert_path_daily_stat(db, visit_date, path, pv_increment=1, uv_increment=1 if path_is_new else 0, now=current_time)
        await db.commit()
        return WebsiteVisitResult(counted=True, deduped=False, path=path)

    async def _record_event(
        self,
        db: AsyncSession,
        visit: WebsiteVisitInput,
        visited_at: datetime,
        visit_date: date,
        ip_address: str,
        ip_hash: str,
        path: str,
        counted_for_pv: bool,
        deduped: bool,
    ) -> None:
        db.add(
            WebsiteVisitEvent(
                id=generate_id("wve"),
                visited_at=visited_at,
                visit_date=visit_date,
                ip_address=ip_address,
                ip_hash=ip_hash,
                path=path,
                referrer=(visit.referrer or "")[:1000] or None,
                user_agent=(visit.user_agent or "")[:500] or None,
                counted_for_pv=counted_for_pv,
                deduped=deduped,
                geo_status="pending",
                created_at=visited_at,
            )
        )

    async def get_summary(
        self,
        db: AsyncSession,
        days: int = 7,
        path_limit: int = 20,
        now: datetime | None = None,
    ) -> WebsiteVisitSummary:
        bounded_days = min(max(days, 1), 90)
        current_date = (now or beijing_now()).date()
        start_date = current_date - timedelta(days=bounded_days - 1)
        yesterday = current_date - timedelta(days=1)

        daily_result = await db.execute(
            select(WebsiteVisitDailyStat)
            .where(WebsiteVisitDailyStat.visit_date >= start_date)
            .where(WebsiteVisitDailyStat.visit_date <= current_date)
            .order_by(WebsiteVisitDailyStat.visit_date.asc())
        )
        daily_stats = daily_result.scalars().all()

        today_stat = next((row for row in daily_stats if row.visit_date == current_date), None)
        yesterday_stat = next((row for row in daily_stats if row.visit_date == yesterday), None)
        daily_rows = [
            {"date": row.visit_date, "pv": int(row.pv or 0), "uv": int(row.uv or 0)}
            for row in daily_stats
        ]
        range_pv = sum(row["pv"] for row in daily_rows)
        range_uv = sum(row["uv"] for row in daily_rows)

        path_pv_sum = func.sum(WebsiteVisitPathDailyStat.pv)
        path_uv_sum = func.sum(WebsiteVisitPathDailyStat.uv)
        path_result = await db.execute(
            select(WebsiteVisitPathDailyStat.path, path_pv_sum, path_uv_sum)
            .where(WebsiteVisitPathDailyStat.visit_date >= start_date)
            .where(WebsiteVisitPathDailyStat.visit_date <= current_date)
            .group_by(WebsiteVisitPathDailyStat.path)
            .order_by(path_pv_sum.desc())
            .limit(path_limit)
        )
        path_rows = [
            {"path": row[0], "pv": int(row[1] or 0), "uv": int(row[2] or 0)}
            for row in path_result.all()
        ]
        events_result = await db.execute(
            select(WebsiteVisitEvent)
            .where(WebsiteVisitEvent.visit_date >= start_date)
            .where(WebsiteVisitEvent.visit_date <= current_date)
            .order_by(WebsiteVisitEvent.visited_at.desc())
            .limit(50)
        )
        recent_events = [
            {
                "id": event.id,
                "visited_at": event.visited_at,
                "ip_address": event.ip_address,
                "path": event.path,
                "referrer": event.referrer,
                "user_agent": event.user_agent,
                "counted_for_pv": bool(event.counted_for_pv),
                "deduped": bool(event.deduped),
                "country": event.country,
                "province": event.province,
                "city": event.city,
                "geo_status": event.geo_status,
            }
            for event in events_result.scalars().all()
        ]

        totals = WebsiteVisitTotals(
            today_pv=int(today_stat.pv if today_stat else 0),
            today_uv=int(today_stat.uv if today_stat else 0),
            yesterday_pv=int(yesterday_stat.pv if yesterday_stat else 0),
            yesterday_uv=int(yesterday_stat.uv if yesterday_stat else 0),
            range_pv=range_pv,
            range_uv=range_uv,
            days=bounded_days,
        )
        return WebsiteVisitSummary(
            totals=totals,
            daily=daily_rows,
            paths=path_rows,
            recent_events=recent_events,
        )

    async def _insert_unique(
        self,
        db: AsyncSession,
        visit_date: date,
        scope: str,
        scope_value: str,
        ip_hash: str,
        now: datetime,
    ) -> bool:
        values = {
            "id": generate_id("wvu"),
            "visit_date": visit_date,
            "scope": scope,
            "scope_value": scope_value[:MAX_PATH_LENGTH],
            "ip_hash": ip_hash,
            "created_at": now,
        }
        dialect = self._dialect_name(db)
        if dialect == "mysql":
            stmt = mysql_insert(WebsiteVisitUnique).values(**values).prefix_with("IGNORE")
        elif dialect == "sqlite":
            stmt = sqlite_insert(WebsiteVisitUnique).values(**values).on_conflict_do_nothing(
                index_elements=["visit_date", "scope", "scope_value", "ip_hash"]
            )
        else:
            stmt = sqlite_insert(WebsiteVisitUnique).values(**values).on_conflict_do_nothing(
                index_elements=["visit_date", "scope", "scope_value", "ip_hash"]
            )

        result = await db.execute(stmt)
        return bool(result.rowcount and result.rowcount > 0)

    async def _upsert_daily_stat(
        self,
        db: AsyncSession,
        visit_date: date,
        pv_increment: int,
        uv_increment: int,
        now: datetime,
    ) -> None:
        values = {
            "id": generate_id("wvd"),
            "visit_date": visit_date,
            "pv": pv_increment,
            "uv": uv_increment,
            "created_at": now,
            "updated_at": now,
        }
        dialect = self._dialect_name(db)
        if dialect == "mysql":
            stmt = mysql_insert(WebsiteVisitDailyStat).values(**values).on_duplicate_key_update(
                pv=WebsiteVisitDailyStat.pv + pv_increment,
                uv=WebsiteVisitDailyStat.uv + uv_increment,
                updated_at=now,
            )
        else:
            stmt = sqlite_insert(WebsiteVisitDailyStat).values(**values).on_conflict_do_update(
                index_elements=["visit_date"],
                set_={
                    "pv": WebsiteVisitDailyStat.pv + pv_increment,
                    "uv": WebsiteVisitDailyStat.uv + uv_increment,
                    "updated_at": now,
                },
            )
        await db.execute(stmt)

    async def _upsert_path_daily_stat(
        self,
        db: AsyncSession,
        visit_date: date,
        path: str,
        pv_increment: int,
        uv_increment: int,
        now: datetime,
    ) -> None:
        values = {
            "id": generate_id("wvp"),
            "visit_date": visit_date,
            "path": path,
            "pv": pv_increment,
            "uv": uv_increment,
            "created_at": now,
            "updated_at": now,
        }
        dialect = self._dialect_name(db)
        if dialect == "mysql":
            stmt = mysql_insert(WebsiteVisitPathDailyStat).values(**values).on_duplicate_key_update(
                pv=WebsiteVisitPathDailyStat.pv + pv_increment,
                uv=WebsiteVisitPathDailyStat.uv + uv_increment,
                updated_at=now,
            )
        else:
            stmt = sqlite_insert(WebsiteVisitPathDailyStat).values(**values).on_conflict_do_update(
                index_elements=["visit_date", "path"],
                set_={
                    "pv": WebsiteVisitPathDailyStat.pv + pv_increment,
                    "uv": WebsiteVisitPathDailyStat.uv + uv_increment,
                    "updated_at": now,
                },
            )
        await db.execute(stmt)

    @staticmethod
    def _dialect_name(db: AsyncSession) -> str:
        bind = db.get_bind()
        return bind.dialect.name if bind is not None else ""
