"""Add richer iteration-display columns for creative agent runs."""

import asyncio
import os
import sys

from sqlalchemy import text


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _sqlite_columns(conn, table: str) -> set[str]:
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in result.fetchall()}


async def _add_column(conn, table: str, column: str, column_type: str, *, is_sqlite: bool) -> None:
    if is_sqlite:
        columns = await _sqlite_columns(conn, table)
        if column in columns:
            print(f"  ⏭️  {table}.{column} 列已存在")
            return
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
        print(f"  ✅ {table}.{column} 列已添加")
        return

    try:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type} NULL"))
        print(f"  ✅ {table}.{column} 列已添加")
    except Exception as exc:
        err = str(exc).lower()
        if "duplicate" in err or "already exists" in err:
            print(f"  ⏭️  {table}.{column} 列已存在")
            return
        raise


async def migrate():
    from app.database import engine

    async with engine.begin() as conn:
        print("🔄 创意 Agent 迭代展示字段迁移：检查字段...")
        db_url = str(engine.url)
        is_sqlite = "sqlite" in db_url.lower()
        columns = [
            ("score_delta", "INTEGER"),
            ("agent_explanation", "TEXT"),
            ("dimension_deltas", "JSON"),
            ("key_improvements", "JSON"),
        ]
        for column, column_type in columns:
            try:
                await _add_column(conn, "creative_iterations", column, column_type, is_sqlite=is_sqlite)
            except Exception as exc:
                print(f"  ⚠️  creative_iterations.{column} 迁移异常: {exc}")
        print("✅ 创意 Agent 迭代展示字段迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate())
