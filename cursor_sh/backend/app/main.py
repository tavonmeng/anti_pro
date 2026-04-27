"""FastAPI 应用主入口"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
import os

from app.config import settings
from app.database import init_db
from app.audit_database import init_audit_db
from app.api import auth, orders, staff, notifications, ai, logs, announcements, enterprise, asr
from app.api import contractor as contractor_api
from app.api import contractor_admin as contractor_admin_api
from app.api import workflow_config as workflow_config_api
from app.middleware.cors import setup_cors
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.audit_logger import AuditLoggerMiddleware
from app.utils.log_setup import init_loguru

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="VR+AI 裸眼3D内容定制管理系统后端 API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
setup_cors(app)

# 配置限流
if settings.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 挂载静态文件目录（用于访问上传的文件）
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# 挂载案例视频/封面图静态目录（统一放在 app/data/cases/ 下）
_cases_static = os.path.join(os.path.dirname(__file__), "data", "cases")
os.makedirs(_cases_static, exist_ok=True)
app.mount("/static/cases", StaticFiles(directory=_cases_static), name="cases_static")

# ========== 根据部署模式注册路由 ==========
deploy_mode = settings.DEPLOYMENT_MODE  # all / external / internal

# 通用路由（所有模式都需要）
app.include_router(auth.router, prefix="/api")

# 文件上传路由
from app.api import upload
app.include_router(upload.router, prefix="/api")

# ASR 语音识别路由
app.include_router(asr.router, prefix="/api")

# 订单路由（所有模式都需要，权限由 JWT 控制）
app.include_router(orders.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")

if deploy_mode in ("all", "external"):
    # 用户端专属：AI 聊天（挂载没有 api 前缀）
    app.include_router(ai.router)

if deploy_mode in ("all", "internal"):
    # 内部系统专属路由
    app.include_router(staff.router, prefix="/api")
    app.include_router(logs.router, prefix="/api")
    app.include_router(announcements.router, prefix="/api")
    app.include_router(enterprise.router, prefix="/api")
    # 承包商相关路由
    app.include_router(contractor_api.router, prefix="/api")
    app.include_router(contractor_admin_api.router, prefix="/api")
    app.include_router(workflow_config_api.router, prefix="/api")

# 挂载审计日志中间件（放在路由注册之后，确保能拦截所有请求）
if settings.LOG_ENABLED:
    app.add_middleware(AuditLoggerMiddleware)


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 初始化日志系统（在数据库之前，以便记录启动过程）
    init_loguru()
    
    # 初始化主业务数据库
    await init_db()
    print(f"✅ 主业务数据库初始化完成 (app.db)")
    
    # 初始化审计日志独立数据库（与主库物理隔离）
    await init_audit_db()
    print(f"✅ 审计日志数据库初始化完成 (audit.db)")
    
    # 确保管理员账户存在（幂等，从 .env 读取配置）
    from scripts.init_admin import ensure_admin
    try:
        await ensure_admin()
    except Exception as e:
        print(f"⚠️  管理员初始化异常（不影响启动）: {e}")
    
    # 确保工作流环节配置存在（幂等，仅首次初始化）
    from scripts.init_workflow import ensure_workflow_stages
    from app.database import async_session_maker
    try:
        async with async_session_maker() as session:
            await ensure_workflow_stages(session)
    except Exception as e:
        print(f"⚠️  工作流配置初始化异常（不影响启动）: {e}")
    
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"✅ 上传目录已准备: {settings.UPLOAD_DIR}")
    
    mode_label = {"all": "全量", "external": "外部（用户端）", "internal": "内部系统"}
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    print(f"📋 部署模式: {mode_label.get(deploy_mode, deploy_mode)}")
    print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/docs")


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
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

