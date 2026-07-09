"""Website visit analytics tables."""

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, UniqueConstraint, Index

from app.database import Base
from app.utils.timezone import beijing_now


class WebsiteVisitEvent(Base):
    """Raw public website visit event."""

    __tablename__ = "website_visit_events"
    __table_args__ = (
        Index("ix_website_visit_events_date_time", "visit_date", "visited_at"),
        Index("ix_website_visit_events_ip_date", "ip_address", "visit_date"),
    )

    id = Column(String(50), primary_key=True, index=True)
    visited_at = Column(DateTime(timezone=True), nullable=False, index=True)
    visit_date = Column(Date, nullable=False, index=True)
    ip_address = Column(String(64), nullable=False, index=True)
    ip_hash = Column(String(64), nullable=False, index=True)
    path = Column(String(255), nullable=False)
    referrer = Column(String(1000), nullable=True)
    user_agent = Column(String(500), nullable=True)
    counted_for_pv = Column(Boolean, nullable=False, default=True)
    deduped = Column(Boolean, nullable=False, default=False)
    country = Column(String(80), nullable=True)
    province = Column(String(120), nullable=True)
    city = Column(String(120), nullable=True)
    geo_status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=beijing_now)


class WebsiteVisitDailyStat(Base):
    """Daily homepage PV/UV aggregate."""

    __tablename__ = "website_visit_daily_stats"

    id = Column(String(50), primary_key=True, index=True)
    visit_date = Column(Date, nullable=False, unique=True, index=True)
    pv = Column(Integer, nullable=False, default=0)
    uv = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)


class WebsiteVisitPathDailyStat(Base):
    """Daily PV/UV aggregate grouped by website path."""

    __tablename__ = "website_visit_path_daily_stats"
    __table_args__ = (
        UniqueConstraint("visit_date", "path", name="uq_website_visit_path_daily"),
        Index("ix_website_visit_path_daily_date_pv", "visit_date", "pv"),
    )

    id = Column(String(50), primary_key=True, index=True)
    visit_date = Column(Date, nullable=False, index=True)
    path = Column(String(255), nullable=False)
    pv = Column(Integer, nullable=False, default=0)
    uv = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)


class WebsiteVisitUnique(Base):
    """Per-day unique visitor keys used to increment UV safely."""

    __tablename__ = "website_visit_uniques"
    __table_args__ = (
        UniqueConstraint(
            "visit_date",
            "scope",
            "scope_value",
            "ip_hash",
            name="uq_website_visit_unique_scope",
        ),
        Index("ix_website_visit_uniques_date_scope", "visit_date", "scope"),
    )

    id = Column(String(50), primary_key=True, index=True)
    visit_date = Column(Date, nullable=False, index=True)
    scope = Column(String(20), nullable=False)
    scope_value = Column(String(255), nullable=False)
    ip_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=beijing_now)
