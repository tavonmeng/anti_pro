"""审计日志专用数据库配置

独立于主业务数据库 (app.db)，实现物理隔离。
所有审计日志写入 audit.db，避免锁竞争和容量污染。
"""

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


def _audit_connect_args() -> dict:
    return {"init_command": "SET time_zone = '+08:00'"} if settings.is_audit_mysql else {}


def _create_audit_engine():
    kwargs = {
        "echo": False,  # 审计库不打印 SQL，避免日志风暴
        "future": True,
    }
    if settings.is_audit_mysql:
        kwargs.update({
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            # Keep this aligned with app.database: aiomysql 0.2.0 requires a
            # reconnect argument for ping(), which SQLAlchemy pre-ping omits.
            "pool_pre_ping": False,
            "connect_args": _audit_connect_args(),
        })
    return create_async_engine(settings.audit_database_url, **kwargs)

# 审计日志专用引擎（与主业务库完全隔离）
audit_engine = _create_audit_engine()

# 审计日志专用会话工厂
audit_session_maker = async_sessionmaker(
    audit_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 审计日志专用 Base（与主业务 Base 完全隔离）
AuditBase = declarative_base()


async def get_audit_db() -> AsyncSession:
    """获取审计数据库会话（用于 Depends 注入）"""
    async with audit_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_audit_db():
    """初始化审计数据库（创建所有审计表）"""
    # 必须先导入模型，让 AuditBase.metadata 注册表结构
    from app.models.audit_log import AuditLog  # noqa: F401
    async with audit_engine.begin() as conn:
        await conn.run_sync(AuditBase.metadata.create_all)
