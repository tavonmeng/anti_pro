"""FastAPI 应用主入口"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
import os
from sqlalchemy import text

from app.config import settings
from app.database import init_db, engine
from app.audit_database import init_audit_db
from app.api import auth, orders, staff, notifications, ai, logs, announcements, enterprise, asr
from app.models.human_handoff import HumanHandoff  # noqa: F401 - ensure table is registered before create_all
from app.api import contractor as contractor_api
from app.api import contractor_admin as contractor_admin_api
from app.api import workflow_config as workflow_config_api
from app.api import homepage_bar as homepage_bar_api
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.audit_logger import (
    AuditLoggerMiddleware,
    start_audit_log_workers,
    stop_audit_log_workers,
)
from app.utils.log_setup import get_module_logger, init_loguru
from app.utils.error_handlers import install_exception_handlers

settings.validate_startup_config()

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="VR+AI 裸眼3D内容定制管理系统后端 API",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)
install_exception_handlers(app)

# 配置 CORS
setup_cors(app)

# 配置限流
if settings.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 挂载静态文件目录（仅本地存储模式；OSS 模式下文件通过签名 URL 直接从云端加载）
if not settings.OSS_ENABLED:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 挂载案例视频/封面图静态目录（仅用户端需要，官网 Landing Page 使用）
if settings.deploy_mode in ("all", "external"):
    _cases_static = os.path.join(os.path.dirname(__file__), "data", "cases")
    os.makedirs(_cases_static, exist_ok=True)
    app.mount("/static/cases", StaticFiles(directory=_cases_static), name="cases_static")

# ========== 根据部署模式注册路由 ==========
deploy_mode = settings.deploy_mode  # all / external / internal

# 通用路由（所有模式都需要）
app.include_router(auth.router, prefix="/api")

# 文件上传路由
from app.api import upload
app.include_router(upload.router, prefix="/api")

# ASR 语音识别路由（仅用户端 AI 聊天使用）
if deploy_mode in ("all", "external"):
    app.include_router(asr.router, prefix="/api")

# 订单路由（所有模式都需要，权限由 JWT 控制）
app.include_router(orders.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
# 公告和日志路由（用户端也需要读取公告、发送行为日志）
app.include_router(announcements.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
# 企业认证路由（用户端提交、管理员端审核）
app.include_router(enterprise.router, prefix="/api")
# 官网顶部运营条（官网公开读取，管理员编辑）
app.include_router(homepage_bar_api.router, prefix="/api")

if deploy_mode in ("all", "external"):
    # 用户端专属：AI 聊天（挂载没有 api 前缀）
    app.include_router(ai.router)

# AI 聊天记录持久化（用户端保存、管理端查看，两端都需要）
from app.api import ai_chat_history
app.include_router(ai_chat_history.router, prefix="/api")

if deploy_mode in ("all", "internal"):
    # 内部系统专属路由
    app.include_router(staff.router, prefix="/api")
    # 承包商相关路由
    app.include_router(contractor_api.router, prefix="/api")
    app.include_router(contractor_admin_api.router, prefix="/api")
    from app.api import user_admin as user_admin_api
    app.include_router(user_admin_api.router, prefix="/api")
    app.include_router(workflow_config_api.router, prefix="/api")
    # 用户画像 Memory 管理（管理员端）
    from app.api import admin_memory
    app.include_router(admin_memory.router, prefix="/api")
    # 客户资料导入（管理员端）
    from app.api import admin_documents
    app.include_router(admin_documents.router, prefix="/api")
    from app.api import human_handoffs
    app.include_router(human_handoffs.router, prefix="/api")
    from app.api import creative_agent as creative_agent_api
    app.include_router(creative_agent_api.router, prefix="/api")

# 挂载审计日志中间件（放在路由注册之后，确保能拦截所有请求）
if settings.LOG_ENABLED:
    app.add_middleware(AuditLoggerMiddleware)


@asynccontextmanager
async def _startup_database_lock():
    """MySQL 部署下用 advisory lock 串行化多 worker 启动迁移。"""
    if not settings.is_mysql:
        yield
        return

    lock_name = "%s:%s" % (settings.DB_NAME, "startup_migrations")
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT GET_LOCK(:lock_name, :timeout)"),
            {"lock_name": lock_name, "timeout": settings.STARTUP_DB_LOCK_TIMEOUT},
        )
        acquired = result.scalar()
        if str(acquired) != "1":
            raise RuntimeError("获取启动迁移锁超时: %s" % lock_name)

        try:
            yield
        finally:
            await conn.execute(
                text("SELECT RELEASE_LOCK(:lock_name)"),
                {"lock_name": lock_name},
            )


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 初始化日志系统（在数据库之前，以便记录启动过程）
    init_loguru()
    startup_logger = get_module_logger("system")

    async with _startup_database_lock():
        # 初始化主业务数据库
        await init_db()
        print(f"✅ 主业务数据库初始化完成 (app.db)")

        if settings.is_production and not settings.AUTO_CREATE_TABLES:
            startup_logger.info("生产环境跳过启动时零散数据库迁移，schema 由 Alembic 管理")
        else:
            # 移除 notifications 表的外键约束（支持给 admin/staff/contractor 发通知）
            if deploy_mode in ("all", "internal", "external"):
                try:
                    from migrations.drop_notification_fks import drop_notification_fks
                    await drop_notification_fks()
                except Exception:
                    startup_logger.exception("notifications FK 迁移异常（不影响启动）")

            # 反馈系统字段迁移（feedbacks.deliverable_id + contractor_deliverables.admin_comments）
            try:
                from scripts.migrate_feedback_system import migrate as migrate_feedback
                await migrate_feedback()
            except Exception:
                startup_logger.exception("反馈系统迁移异常（不影响启动）")

            # AI 聊天消息幂等字段迁移（client_message_id + 唯一索引）
            try:
                from scripts.migrate_ai_chat_message_ids import migrate as migrate_ai_chat_message_ids
                await migrate_ai_chat_message_ids()
            except Exception:
                startup_logger.exception("AI 聊天消息幂等迁移异常（不影响启动）")

            # 创意 Agent 字段/反馈表迁移（开发或显式允许自动建表时执行；生产由 Alembic 管理）
            try:
                from scripts.migrate_creative_agent_iterations import migrate as migrate_creative_agent_iterations
                await migrate_creative_agent_iterations()
            except Exception:
                startup_logger.exception("创意 Agent 迭代字段迁移异常（不影响启动）")

            try:
                from scripts.migrate_creative_agent_react import migrate as migrate_creative_agent_react
                await migrate_creative_agent_react()
            except Exception:
                startup_logger.exception("创意 Agent ReAct 字段迁移异常（不影响启动）")

            try:
                from scripts.migrate_creative_designer_feedbacks import migrate as migrate_creative_designer_feedbacks
                await migrate_creative_designer_feedbacks()
            except Exception:
                startup_logger.exception("创意 Agent 设计师反馈表迁移异常（不影响启动）")

        if settings.LOG_DB_ENABLED:
            # 初始化审计日志独立数据库（与主库物理隔离）
            await init_audit_db()
            print("✅ 审计日志数据库初始化完成")
        else:
            startup_logger.info("审计日志数据库写入已关闭，跳过审计库初始化")

        if settings.LOG_ENABLED:
            start_audit_log_workers()

        # 内部系统专属初始化（用户端不需要管理员账户和工作流配置）
        if deploy_mode in ("all", "internal"):
            # 确保管理员账户存在（幂等，从 .env 读取配置）
            from scripts.init_admin import ensure_admin
            try:
                await ensure_admin()
            except Exception:
                startup_logger.exception("管理员初始化异常（不影响启动）")

            # 确保工作流环节配置存在（幂等，仅首次初始化）
            from scripts.init_workflow import ensure_workflow_stages
            from app.database import async_session_maker
            try:
                async with async_session_maker() as session:
                    await ensure_workflow_stages(session)
            except Exception:
                startup_logger.exception("工作流配置初始化异常（不影响启动）")

    # 确保上传目录存在（仅本地存储模式）
    if not settings.OSS_ENABLED:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        print(f"✅ 上传目录已准备: {settings.UPLOAD_DIR}")
    else:
        print(f"✅ 文件存储: 阿里云 OSS ({settings.OSS_BUCKET_NAME} @ {settings.OSS_ENDPOINT})")
    
    mode_label = {"all": "全量", "external": "外部（用户端）", "internal": "内部系统"}
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    print(f"📋 部署模式: {mode_label.get(deploy_mode, deploy_mode)}")
    if settings.docs_enabled:
        print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止后台 worker，尽量刷完审计日志。"""
    if settings.LOG_ENABLED:
        await stop_audit_log_workers()


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "docs": "/docs" if settings.docs_enabled else None,
        "redoc": "/redoc" if settings.docs_enabled else None,
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
