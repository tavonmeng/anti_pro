"""Create designer feedback table for creative agent human-in-the-loop iteration."""

import asyncio
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def migrate():
    from app.database import Base, engine
    from app.models.creative_agent import CreativeDesignerFeedback

    async with engine.begin() as conn:
        print("🔄 创意 Agent 设计师反馈表迁移：检查表...")
        await conn.run_sync(CreativeDesignerFeedback.__table__.create, checkfirst=True)
        print("✅ 创意 Agent 设计师反馈表已准备")


if __name__ == "__main__":
    asyncio.run(migrate())
