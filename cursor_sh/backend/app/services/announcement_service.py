from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate
from typing import List

class AnnouncementService:
    @staticmethod
    async def get_all_announcements(db: AsyncSession, active_only: bool = False) -> List[Announcement]:
        query = select(Announcement)
        if active_only:
            query = query.where(Announcement.is_active == True)
        query = query.order_by(Announcement.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def create_announcement(db: AsyncSession, data: AnnouncementCreate, admin_id: str) -> Announcement:
        announcement = Announcement(
            title=data.title,
            content=data.content,
            is_active=data.is_active,
            created_by=admin_id
        )
        db.add(announcement)
        await db.commit()
        await db.refresh(announcement)
        return announcement
    
    @staticmethod
    async def update_announcement(db: AsyncSession, announcement_id: str, data: AnnouncementUpdate) -> Announcement:
        result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
        announcement = result.scalar_one_or_none()
        if not announcement:
            raise HTTPException(status_code=404, detail="公告不存在")
        
        if data.title is not None:
            announcement.title = data.title
        if data.content is not None:
            announcement.content = data.content
        if data.is_active is not None:
            announcement.is_active = data.is_active
            
        await db.commit()
        await db.refresh(announcement)
        return announcement
        
    @staticmethod
    async def delete_announcement(db: AsyncSession, announcement_id: str):
        result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
        announcement = result.scalar_one_or_none()
        if not announcement:
            raise HTTPException(status_code=404, detail="公告不存在")
            
        await db.delete(announcement)
        await db.commit()
