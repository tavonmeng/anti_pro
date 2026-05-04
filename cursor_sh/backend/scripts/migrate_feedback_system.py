"""
数据库迁移脚本：为反馈系统添加新字段

1. feedbacks 表：添加 deliverable_id 列（可选 FK）
2. contractor_deliverables 表：添加 admin_comments JSON 列

使用方法：
  python -m scripts.migrate_feedback_system
"""

import asyncio
import sys
import os

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        print("🔄 开始迁移：反馈系统字段...")
        
        # 1. feedbacks 表添加 deliverable_id 列
        try:
            await conn.execute(text(
                "ALTER TABLE feedbacks ADD COLUMN deliverable_id VARCHAR(50) NULL"
            ))
            print("  ✅ feedbacks.deliverable_id 列已添加")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("  ⏭️  feedbacks.deliverable_id 列已存在，跳过")
            else:
                print(f"  ⚠️  feedbacks.deliverable_id 添加失败: {e}")
        
        # 添加索引
        try:
            await conn.execute(text(
                "CREATE INDEX ix_feedbacks_deliverable_id ON feedbacks (deliverable_id)"
            ))
            print("  ✅ feedbacks.deliverable_id 索引已添加")
        except Exception as e:
            if "Duplicate" in str(e) or "already exists" in str(e).lower():
                print("  ⏭️  索引已存在，跳过")
            else:
                print(f"  ⚠️  索引添加失败: {e}")
        
        # 2. contractor_deliverables 表添加 admin_comments 列
        try:
            await conn.execute(text(
                "ALTER TABLE contractor_deliverables ADD COLUMN admin_comments JSON NULL"
            ))
            print("  ✅ contractor_deliverables.admin_comments 列已添加")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print("  ⏭️  contractor_deliverables.admin_comments 列已存在，跳过")
            else:
                print(f"  ⚠️  contractor_deliverables.admin_comments 添加失败: {e}")
        
        print("✅ 迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate())
