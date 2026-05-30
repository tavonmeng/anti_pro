"""数据库配置

支持 SQLite (开发) 和 MySQL RDS (生产) 双模式。
通过 .env 中的 DB_TYPE 或 DATABASE_URL 进行切换。
"""

from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

try:
    from sqlalchemy.ext.asyncio import async_sessionmaker
except ImportError:
    from sqlalchemy.orm import sessionmaker
    def async_sessionmaker(*args, **kwargs):
        kwargs.setdefault('class_', AsyncSession)
        return sessionmaker(*args, **kwargs)

from app.config import settings


def _required_alembic_heads() -> set[str]:
    """Return migration heads from the local Alembic script directory."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    script = ScriptDirectory.from_config(alembic_cfg)
    return set(script.get_heads())


def _create_engine():
    """
    根据数据库类型创建合适的异步引擎。
    - SQLite: 轻量配置，适合开发
    - MySQL (RDS): 完整连接池 + 健康检查，适合生产
    """
    db_url = settings.database_url
    
    if settings.is_mysql:
        # ====== MySQL / RDS 模式 ======
        return create_async_engine(
            db_url,
            echo=settings.DEBUG,
            future=True,
            # 连接池配置（对 RDS 至关重要）
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            # pool_pre_ping: 每次从池中取连接前先 ping 一下
            # 防止 RDS 在空闲超时后关闭连接导致 "MySQL server has gone away"
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            connect_args={"init_command": "SET time_zone = '+08:00'"},
        )
    else:
        # ====== SQLite 模式（开发/测试）======
        return create_async_engine(
            db_url,
            echo=settings.DEBUG,
            future=True
        )


# 创建异步数据库引擎
engine = _create_engine()

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 创建基础模型类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    import app.models  # noqa: F401 - ensure all models are registered

    async with engine.begin() as conn:
        if settings.is_production and not settings.AUTO_CREATE_TABLES:
            required_heads = _required_alembic_heads()

            def _schema_state(sync_conn):
                existing = set(inspect(sync_conn).get_table_names())
                expected = set(Base.metadata.tables.keys())
                versions = set()
                if "alembic_version" in existing:
                    rows = sync_conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
                    versions = {row[0] for row in rows}
                return {
                    "missing_tables": sorted(expected - existing),
                    "versions": versions,
                    "has_version_table": "alembic_version" in existing,
                }

            schema_state = await conn.run_sync(_schema_state)
            missing_tables = schema_state["missing_tables"]
            if missing_tables:
                preview = ", ".join(missing_tables[:10])
                more = "..." if len(missing_tables) > 10 else ""
                raise RuntimeError(
                    "数据库 schema 未完成迁移，请先运行 `alembic upgrade head`；缺失表: %s%s"
                    % (preview, more)
                )
            if not schema_state["has_version_table"]:
                raise RuntimeError("数据库缺少 alembic_version 表，请先运行 `alembic upgrade head` 或在确认结构一致后执行 `alembic stamp head`")
            missing_heads = sorted(required_heads - schema_state["versions"])
            if missing_heads:
                raise RuntimeError(
                    "数据库 Alembic 版本不是最新，请先运行 `alembic upgrade head`；缺失版本: %s"
                    % ", ".join(missing_heads)
                )
        else:
            await conn.run_sync(Base.metadata.create_all)
    
    # 打印当前数据库模式
    db_type = "MySQL (RDS)" if settings.is_mysql else "SQLite"
    # 脱敏打印连接信息
    db_url = settings.database_url
    if settings.is_mysql:
        # 隐藏密码
        import re
        safe_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', db_url)
        print(f"  📦 数据库类型: {db_type}")
        print(f"  🔗 连接地址: {safe_url}")
        print(f"  🏊 连接池: size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW}")
    else:
        print(f"  📦 数据库类型: {db_type}")
        print(f"  🔗 数据库文件: {db_url}")
