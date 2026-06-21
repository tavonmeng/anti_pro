"""Service for homepage marketing bar configuration."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.homepage_bar import HomepageBar
from app.schemas.homepage_bar import HomepageBarUpdate


DEFAULT_BAR_ID = "homepage_top_bar"
DEFAULT_TITLE = "快速了解我们的服务和案例，点此处下载 PDF"
DEFAULT_BUTTON_TEXT = "下载 PDF"


class HomepageBarService:
    @staticmethod
    def _with_fresh_urls(bar: HomepageBar) -> HomepageBar:
        if settings.OSS_ENABLED:
            from app.services.oss_service import get_signed_url, maybe_sign_url
            if bar.pdf_object_key:
                bar.pdf_url = get_signed_url(bar.pdf_object_key, settings.OSS_SIGNED_URL_EXPIRES)
            elif bar.pdf_url:
                bar.pdf_url = maybe_sign_url(bar.pdf_url, settings.OSS_SIGNED_URL_EXPIRES)
            if bar.image_object_key:
                bar.image_url = get_signed_url(bar.image_object_key, settings.OSS_SIGNED_URL_EXPIRES)
            elif bar.image_url:
                bar.image_url = maybe_sign_url(bar.image_url, settings.OSS_SIGNED_URL_EXPIRES)
        return bar

    @staticmethod
    async def get_or_create(db: AsyncSession, admin_id: str | None = None) -> HomepageBar:
        result = await db.execute(select(HomepageBar).where(HomepageBar.id == DEFAULT_BAR_ID))
        bar = result.scalar_one_or_none()
        if bar:
            return HomepageBarService._with_fresh_urls(bar)

        bar = HomepageBar(
            id=DEFAULT_BAR_ID,
            title=DEFAULT_TITLE,
            button_text=DEFAULT_BUTTON_TEXT,
            is_active=False,
            created_by=admin_id,
        )
        db.add(bar)
        await db.commit()
        await db.refresh(bar)
        return HomepageBarService._with_fresh_urls(bar)

    @staticmethod
    async def get_public(db: AsyncSession) -> HomepageBar | None:
        result = await db.execute(select(HomepageBar).where(HomepageBar.id == DEFAULT_BAR_ID))
        bar = result.scalar_one_or_none()
        if not bar or not bar.is_active or not (bar.pdf_url or bar.pdf_object_key):
            return None
        return HomepageBarService._with_fresh_urls(bar)

    @staticmethod
    async def update(db: AsyncSession, data: HomepageBarUpdate, admin_id: str) -> HomepageBar:
        bar = await HomepageBarService.get_or_create(db, admin_id)
        updates = data.dict(exclude_unset=True)
        for key, value in updates.items():
            setattr(bar, key, value)
        if bar.pdf_object_key:
            bar.pdf_url = bar.pdf_object_key
        if bar.image_object_key:
            bar.image_url = bar.image_object_key
        if not bar.created_by:
            bar.created_by = admin_id

        await db.commit()
        await db.refresh(bar)
        return HomepageBarService._with_fresh_urls(bar)
