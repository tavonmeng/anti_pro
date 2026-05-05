"""
数据库迁移脚本：为反馈系统添加新字段

1. feedbacks 表：添加 deliverable_id 列（可选 FK）
2. contractor_deliverables 表：添加 admin_comments JSON 列

可在启动时自动执行（幂等、安全）
"""

import asyncio
import sys
import os

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text


async def migrate():
    from app.database import engine
    
    async with engine.begin() as conn:
        print("🔄 反馈系统迁移：检查字段...")
        
        # 检测数据库类型
        db_url = str(engine.url)
        is_sqlite = "sqlite" in db_url.lower()
        
        # 1. feedbacks 表添加 deliverable_id 列
        try:
            if is_sqlite:
                # SQLite: 检查列是否存在
                result = await conn.execute(text("PRAGMA table_info(feedbacks)"))
                columns = [row[1] for row in result.fetchall()]
                if "deliverable_id" not in columns:
                    await conn.execute(text(
                        "ALTER TABLE feedbacks ADD COLUMN deliverable_id VARCHAR(50)"
                    ))
                    print("  ✅ feedbacks.deliverable_id 列已添加")
                else:
                    print("  ⏭️  feedbacks.deliverable_id 列已存在")
            else:
                # MySQL
                await conn.execute(text(
                    "ALTER TABLE feedbacks ADD COLUMN deliverable_id VARCHAR(50) NULL"
                ))
                print("  ✅ feedbacks.deliverable_id 列已添加")
        except Exception as e:
            err_str = str(e).lower()
            if "duplicate" in err_str or "already exists" in err_str:
                print("  ⏭️  feedbacks.deliverable_id 列已存在")
            else:
                print(f"  ⚠️  feedbacks.deliverable_id: {e}")
        
        # MySQL: 添加索引
        if not is_sqlite:
            try:
                await conn.execute(text(
                    "CREATE INDEX ix_feedbacks_deliverable_id ON feedbacks (deliverable_id)"
                ))
                print("  ✅ feedbacks.deliverable_id 索引已添加")
            except Exception as e:
                err_str = str(e).lower()
                if "duplicate" in err_str or "already exists" in err_str:
                    pass  # 静默
                else:
                    print(f"  ⚠️  索引: {e}")
        
        # 2. contractor_deliverables 表添加 admin_comments 列
        try:
            if is_sqlite:
                result = await conn.execute(text("PRAGMA table_info(contractor_deliverables)"))
                columns = [row[1] for row in result.fetchall()]
                if "admin_comments" not in columns:
                    await conn.execute(text(
                        "ALTER TABLE contractor_deliverables ADD COLUMN admin_comments TEXT"
                    ))
                    print("  ✅ contractor_deliverables.admin_comments 列已添加")
                else:
                    print("  ⏭️  contractor_deliverables.admin_comments 列已存在")
            else:
                await conn.execute(text(
                    "ALTER TABLE contractor_deliverables ADD COLUMN admin_comments JSON NULL"
                ))
                print("  ✅ contractor_deliverables.admin_comments 列已添加")
        except Exception as e:
            err_str = str(e).lower()
            if "duplicate" in err_str or "already exists" in err_str:
                print("  ⏭️  contractor_deliverables.admin_comments 列已存在")
            else:
                print(f"  ⚠️  contractor_deliverables.admin_comments: {e}")
        
        print("✅ 反馈系统迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate())
