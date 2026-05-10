"""Add idempotency key support to AI chat messages."""

import asyncio
import os
import sys

from sqlalchemy import text


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _sqlite_columns(conn, table: str) -> set[str]:
    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in result.fetchall()}


async def migrate():
    from app.database import engine

    async with engine.begin() as conn:
        print("🔄 AI聊天消息幂等迁移：检查字段...")
        db_url = str(engine.url)
        is_sqlite = "sqlite" in db_url.lower()

        try:
            if is_sqlite:
                columns = await _sqlite_columns(conn, "ai_chat_messages")
                if "client_message_id" not in columns:
                    await conn.execute(text(
                        "ALTER TABLE ai_chat_messages ADD COLUMN client_message_id VARCHAR(80)"
                    ))
                    print("  ✅ ai_chat_messages.client_message_id 列已添加")
                else:
                    print("  ⏭️  ai_chat_messages.client_message_id 列已存在")
            else:
                await conn.execute(text(
                    "ALTER TABLE ai_chat_messages ADD COLUMN client_message_id VARCHAR(80) NULL"
                ))
                print("  ✅ ai_chat_messages.client_message_id 列已添加")
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                print("  ⏭️  ai_chat_messages.client_message_id 列已存在")
            else:
                print(f"  ⚠️  client_message_id 列迁移异常: {e}")

        try:
            if is_sqlite:
                await conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_chat_session_client_msg "
                    "ON ai_chat_messages(session_id, client_message_id)"
                ))
            else:
                await conn.execute(text(
                    "CREATE UNIQUE INDEX uq_ai_chat_session_client_msg "
                    "ON ai_chat_messages(session_id, client_message_id)"
                ))
            print("  ✅ ai_chat_messages 幂等唯一索引已添加")
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                print("  ⏭️  ai_chat_messages 幂等唯一索引已存在")
            else:
                print(f"  ⚠️  幂等唯一索引迁移异常: {e}")

        print("✅ AI聊天消息幂等迁移完成")


if __name__ == "__main__":
    asyncio.run(migrate())
