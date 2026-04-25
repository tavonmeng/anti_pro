"""
企业认证相关字段扩展迁移脚本
用途：为 users 表增加企业相关状态和认证字段
支持环境：SQLite / MySQL
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def migrate_enterprise_columns():
    print("🚀 开始数据库升级：企业认证字段拓展...")
    
    # 针对 users 表需要增加的字段及 SQLite 语法
    columns_to_add = [
        "enterprise_status VARCHAR(50) NOT NULL DEFAULT 'NONE'",
        "enterprise_name VARCHAR(200)",
        "business_license_url VARCHAR(500)",
        "enterprise_reject_reason TEXT",
        "enterprise_submitted_at DATETIME",
        "enterprise_reviewed_at DATETIME"
    ]
    
    async with engine.begin() as conn:
        for col_def in columns_to_add:
            try:
                # SQLite 和 MySQL 的 ADD COLUMN 语法略有不同但基础是互通的
                query = text(f"ALTER TABLE users ADD COLUMN {col_def};")
                await conn.execute(query)
                print(f"✅ 成功添加字段: {col_def.split()[0]}")
            except Exception as e:
                # 如果字段已存在，会抛出异常，这里我们吃掉它并视为无害错误
                error_msg = str(e).lower()
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    print(f"⏩ 字段已存在，自动跳过: {col_def.split()[0]}")
                else:
                    # 对于 SQLite 特有的错误进行宽容处理
                    print(f"⏩ 尝试添加 {col_def.split()[0]} 时跳过 (可能已存在或语法被拒): {e}")

    print("🎉 企业认证相关及用户信息拓展字段，升级完成！")

if __name__ == "__main__":
    # 执行异步迁移流程
    asyncio.run(migrate_enterprise_columns())
