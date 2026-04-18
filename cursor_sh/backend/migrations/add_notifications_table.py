"""
数据库迁移脚本：添加消息通知表

运行方式：
1. 确保数据库已启动
2. 运行: python -m backend.migrations.add_notifications_table

注意：如果使用 init_db()，此迁移会自动应用
"""

import asyncio
from sqlalchemy import text
from app.database import async_engine


async def add_notifications_table():
    """添加消息通知表"""
    
    # 创建表的 SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS notifications (
        id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        order_id VARCHAR(50),
        type VARCHAR(50) NOT NULL,
        title VARCHAR(200) NOT NULL,
        content TEXT NOT NULL,
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        read_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
    );
    """
    
    # 创建索引
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_notifications_order_id ON notifications(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);"
    ]
    
    async with async_engine.begin() as conn:
        print("开始创建 notifications 表...")
        
        # 创建表
        await conn.execute(text(create_table_sql))
        print("✅ notifications 表创建成功")
        
        # 创建索引
        for index_sql in create_indexes_sql:
            await conn.execute(text(index_sql))
        print("✅ 索引创建成功")
        
        print("✅ 数据库迁移完成")


if __name__ == "__main__":
    print("=" * 50)
    print("数据库迁移：添加消息通知表")
    print("=" * 50)
    asyncio.run(add_notifications_table())

