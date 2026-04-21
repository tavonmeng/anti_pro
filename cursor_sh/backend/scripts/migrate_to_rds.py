#!/usr/bin/env python3
"""
SQLite → MySQL (阿里云 RDS) 数据迁移脚本

使用方式:
  1. 先在 .env 中配置好 RDS 连接信息（DB_TYPE=mysql 等）
  2. 确保 RDS 实例已创建且网络可达
  3. 运行: python scripts/migrate_to_rds.py

脚本会自动:
  - 从 SQLite (app.db) 读取所有数据
  - 在 RDS 中创建表结构（通过 SQLAlchemy ORM）
  - 将数据逐表导入 RDS
  - 验证迁移结果

注意: 此脚本不会修改源 SQLite 数据库。
"""

import asyncio
import json
import sqlite3
import sys
import os
from datetime import datetime

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 配置 ====================

# SQLite 源数据库路径
SQLITE_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app.db"
)

# 需要迁移的表（按依赖关系排序，被依赖的表在前）
TABLES_IN_ORDER = [
    "users",
    "orders",
    "order_assignees",
    "files",
    "feedbacks",
    "notifications",
]


# ==================== 辅助函数 ====================

def read_sqlite_data(db_path: str, table: str) -> tuple:
    """读取 SQLite 表数据，返回 (columns, rows)"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    
    if rows:
        columns = rows[0].keys()
        data = [dict(row) for row in rows]
    else:
        # 获取列信息（即使没有数据）
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        data = []
    
    conn.close()
    return columns, data


def check_sqlite_exists(db_path: str) -> bool:
    """检查 SQLite 文件是否存在"""
    return os.path.exists(db_path)


def get_sqlite_tables(db_path: str) -> list:
    """获取 SQLite 中所有表名"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables


# ==================== 核心迁移逻辑 ====================

async def migrate():
    """执行迁移"""
    
    print("=" * 60)
    print("  SQLite → MySQL (阿里云 RDS) 数据迁移工具")
    print("=" * 60)
    print()
    
    # Step 1: 检查 SQLite 源数据库
    print("📋 Step 1: 检查源数据库 (SQLite)")
    if not check_sqlite_exists(SQLITE_DB_PATH):
        print(f"  ❌ SQLite 数据库不存在: {SQLITE_DB_PATH}")
        print(f"  请确认 app.db 文件路径正确")
        return False
    
    sqlite_tables = get_sqlite_tables(SQLITE_DB_PATH)
    print(f"  ✅ 找到 SQLite 数据库: {SQLITE_DB_PATH}")
    print(f"  📊 现有表: {', '.join(sqlite_tables)}")
    print()
    
    # Step 2: 读取 SQLite 数据概览
    print("📋 Step 2: 读取源数据概览")
    table_data = {}
    for table in TABLES_IN_ORDER:
        if table not in sqlite_tables:
            print(f"  ⚠️  表 {table} 在 SQLite 中不存在，跳过")
            continue
        columns, data = read_sqlite_data(SQLITE_DB_PATH, table)
        table_data[table] = (columns, data)
        print(f"  📦 {table}: {len(data)} 行")
    print()
    
    # Step 3: 连接 RDS 并创建表
    print("📋 Step 3: 连接 RDS 并创建表结构")
    
    from app.config import settings
    
    if not settings.is_mysql:
        print("  ❌ 当前 .env 配置的不是 MySQL！")
        print(f"  当前 DB_TYPE={settings.DB_TYPE}")
        print(f"  当前连接串: {settings.database_url}")
        print()
        print("  请先修改 .env 中的数据库配置:")
        print("    DB_TYPE=mysql")
        print("    DB_HOST=rm-xxx.mysql.rds.aliyuncs.com")
        print("    DB_PORT=3306")
        print("    DB_NAME=your_db_name")
        print("    DB_USER=your_username")
        print("    DB_PASSWORD=your_password")
        return False
    
    import re
    safe_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', settings.database_url)
    print(f"  🔗 目标 RDS: {safe_url}")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        try:
            from sqlalchemy.ext.asyncio import async_sessionmaker
        except ImportError:
            from sqlalchemy.orm import sessionmaker
            def async_sessionmaker(*args, **kwargs):
                kwargs.setdefault('class_', AsyncSession)
                return sessionmaker(*args, **kwargs)
        from sqlalchemy import text
        
        # 导入所有模型以确保 Base.metadata 包含所有表定义
        from app.database import Base
        from app.models.user import User
        from app.models.order import Order, OrderAssignee
        from app.models.file import File
        from app.models.feedback import Feedback
        from app.models.notification import Notification
        
        rds_engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        
        # 测试连接
        async with rds_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        print("  ✅ RDS 连接成功")
        
        # 创建所有表
        async with rds_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("  ✅ 表结构创建完成")
        print()
        
    except Exception as e:
        print(f"  ❌ RDS 连接失败: {e}")
        print()
        print("  请检查:")
        print("    1. RDS 实例是否已启动")
        print("    2. 网络/安全组/白名单是否允许连接")
        print("    3. 用户名/密码/数据库名是否正确")
        return False
    
    # Step 4: 导入数据
    print("📋 Step 4: 导入数据到 RDS")
    
    rds_session_maker = async_sessionmaker(
        rds_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    total_imported = 0
    
    for table in TABLES_IN_ORDER:
        if table not in table_data:
            continue
        
        columns, rows = table_data[table]
        if not rows:
            print(f"  ⏭️  {table}: 空表，跳过")
            continue
        
        try:
            async with rds_session_maker() as session:
                # 先检查目标表是否已有数据
                count_result = await session.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                existing_count = count_result.scalar()
                
                if existing_count > 0:
                    print(f"  ⚠️  {table}: 目标表已有 {existing_count} 行数据，跳过（避免重复导入）")
                    continue
                
                # 批量插入
                batch_size = 100
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    for row in batch:
                        # 处理 JSON 字段：SQLite 中 JSON 可能存为字符串
                        processed_row = {}
                        for key, value in row.items():
                            if isinstance(value, str) and key in ("order_data",):
                                try:
                                    # 确保 JSON 字段是 dict/list 而非字符串
                                    parsed = json.loads(value)
                                    # 对 MySQL JSON 列，需要存为 JSON 字符串
                                    processed_row[key] = json.dumps(parsed, ensure_ascii=False)
                                except (json.JSONDecodeError, TypeError):
                                    processed_row[key] = value
                            else:
                                processed_row[key] = value
                        
                        # 构建 INSERT 语句
                        cols = ", ".join([f"`{k}`" for k in processed_row.keys()])
                        placeholders = ", ".join([f":{k}" for k in processed_row.keys()])
                        sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
                        await session.execute(text(sql), processed_row)
                    
                    await session.commit()
                
                print(f"  ✅ {table}: {len(rows)} 行导入成功")
                total_imported += len(rows)
                
        except Exception as e:
            print(f"  ❌ {table}: 导入失败 - {e}")
            import traceback
            traceback.print_exc()
    
    print()
    
    # Step 5: 验证
    print("📋 Step 5: 验证迁移结果")
    
    async with rds_session_maker() as session:
        for table in TABLES_IN_ORDER:
            if table not in table_data:
                continue
            
            _, source_rows = table_data[table]
            count_result = await session.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
            rds_count = count_result.scalar()
            
            status = "✅" if rds_count == len(source_rows) else "⚠️"
            print(f"  {status} {table}: SQLite={len(source_rows)} → RDS={rds_count}")
    
    await rds_engine.dispose()
    
    print()
    print("=" * 60)
    print(f"  🎉 迁移完成！共导入 {total_imported} 行数据")
    print()
    print("  下一步操作:")
    print("    1. 验证应用功能（登录/订单/反馈等）")
    print("    2. 确认无误后，保留 app.db 作为备份")
    print("    3. .env 中保持 DB_TYPE=mysql 即可")
    print("=" * 60)
    
    return True


# ==================== 入口 ====================

if __name__ == "__main__":
    print()
    result = asyncio.run(migrate())
    sys.exit(0 if result else 1)
