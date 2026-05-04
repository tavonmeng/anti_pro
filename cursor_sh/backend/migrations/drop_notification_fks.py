"""
数据库迁移脚本：移除 notifications 表的外键约束

通知可能发送给 admins/staff_members/users/contractors 四张表中的任意用户，
因此 user_id 和 order_id 不能有外键约束。

运行方式: python -m migrations.drop_notification_fks
"""

import asyncio
from sqlalchemy import text
from app.database import async_engine


async def drop_notification_fks():
    """移除 notifications 表的 user_id 和 order_id 外键约束"""
    
    async with async_engine.begin() as conn:
        print("检查并移除 notifications 表的外键约束...")
        
        # MySQL: 查询外键名称
        fk_query = text("""
            SELECT CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_NAME = 'notifications'
              AND REFERENCED_TABLE_NAME IS NOT NULL
              AND TABLE_SCHEMA = DATABASE()
        """)
        
        result = await conn.execute(fk_query)
        fk_names = [row[0] for row in result.fetchall()]
        
        if not fk_names:
            print("✅ 没有发现外键约束，无需操作")
            return
        
        for fk_name in fk_names:
            print(f"  移除外键: {fk_name}")
            try:
                await conn.execute(text(f"ALTER TABLE notifications DROP FOREIGN KEY {fk_name}"))
                print(f"  ✅ 已移除: {fk_name}")
            except Exception as e:
                print(f"  ⚠️ 移除失败（可能已不存在）: {e}")
        
        print("✅ notifications 表外键约束移除完成")


if __name__ == "__main__":
    print("=" * 50)
    print("数据库迁移：移除 notifications 外键约束")
    print("=" * 50)
    asyncio.run(drop_notification_fks())
