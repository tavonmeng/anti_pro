"""数据库配置

支持 SQLite (开发) 和 MySQL RDS (生产) 双模式。
通过 .env 中的 DB_TYPE 或 DATABASE_URL 进行切换。
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
    async with engine.begin() as conn:
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
