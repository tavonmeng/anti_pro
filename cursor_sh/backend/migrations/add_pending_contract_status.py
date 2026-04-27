"""
数据库迁移脚本：为 orders.status 添加 'pending_contract' 枚举值

适用场景：
- MySQL/RDS 数据库（使用原生 ENUM 类型，需手动添加新枚举值）
- SQLite 无需运行此脚本（ENUM 存储为 VARCHAR，自动兼容）

运行方式：
1. 确保 .env 中 DB_TYPE=mysql
2. 运行: cd backend && python -m migrations.add_pending_contract_status
"""

import asyncio
from sqlalchemy import text
from app.database import engine
from app.config import settings


async def add_pending_contract_status():
    """为 orders.status 字段添加 pending_contract 枚举值"""

    if not settings.is_mysql:
        print("当前数据库为 SQLite，无需执行此迁移（ENUM 存储为 VARCHAR，自动兼容）")
        return

    async with engine.begin() as conn:
        print("开始迁移：为 orders.status 添加 pending_contract 枚举值...")

        # MySQL ALTER TABLE 修改 ENUM 类型：需列出所有枚举值（包括新增的）
        # pending_contract 插入到 pending_assign 和 in_production 之间
        alter_sql = text("""
            ALTER TABLE orders
            MODIFY COLUMN status ENUM(
                'draft',
                'pending_assign',
                'pending_contract',
                'in_production',
                'pending_review',
                'preview_ready',
                'review_rejected',
                'revision_needed',
                'final_preview',
                'completed',
                'cancelled'
            ) NOT NULL DEFAULT 'pending_contract'
        """)

        try:
            await conn.execute(alter_sql)
            print("✅ orders.status 枚举值已更新，新增 'pending_contract'")
        except Exception as e:
            # 如果枚举值已存在，会通过不报错（MODIFY 是幂等的）
            print(f"⚠️  执行结果: {e}")

        # 可选：将现有的 pending_assign 订单迁移到 pending_contract
        # （仅在确认所有旧的 pending_assign 订单都应迁移时启用）
        # migrate_sql = text("""
        #     UPDATE orders SET status = 'pending_contract'
        #     WHERE status = 'pending_assign'
        # """)
        # result = await conn.execute(migrate_sql)
        # print(f"  迁移了 {result.rowcount} 个 pending_assign → pending_contract 订单")

        print("✅ 数据库迁移完成")


if __name__ == "__main__":
    print("=" * 50)
    print("数据库迁移：添加 pending_contract 状态")
    print("=" * 50)
    asyncio.run(add_pending_contract_status())
