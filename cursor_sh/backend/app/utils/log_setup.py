"""
日志系统初始化与模块分发器

职责：
- 初始化 Loguru，按业务模块创建独立日志文件夹
- 注册全局错误/崩溃保护 sink
- 接管 uvicorn/gunicorn 标准日志
- 提供 get_module_logger() 工厂方法
"""

import sys
import os
import signal
import atexit
import logging
from loguru import logger
from app.config import settings


# ============================================================
# 1. 模块映射：URL 前缀 → 业务模块名
# ============================================================
MODULE_ROUTE_MAP = {
    "/api/auth": "auth",
    "/api/orders": "order",
    "/api/staff": "staff",
    "/api/notifications": "notification",
    "/api/logs": "workspace",
    "/ai/": "ai",
}


def resolve_module(path: str) -> str:
    """根据请求路径解析所属的业务模块"""
    path_lower = path.lower()
    for prefix, module in MODULE_ROUTE_MAP.items():
        if path_lower.startswith(prefix):
            return module
    return "system"


# ============================================================
# 2. Uvicorn / 标准库日志拦截器
# ============================================================
class InterceptHandler(logging.Handler):
    """将标准 logging（uvicorn/gunicorn）重定向到 loguru"""

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# ============================================================
# 3. 脱敏工具
# ============================================================
_sanitize_fields = set()


def _init_sanitize_fields():
    """从配置中解析需要脱敏的字段列表"""
    global _sanitize_fields
    raw = getattr(settings, "LOG_SANITIZE_FIELDS", "")
    _sanitize_fields = {f.strip().lower() for f in raw.split(",") if f.strip()}


def sanitize_payload(data: dict) -> dict:
    """对字典中的敏感字段进行脱敏处理"""
    if not isinstance(data, dict):
        return data
    sanitized = {}
    for key, value in data.items():
        if key.lower() in _sanitize_fields:
            sanitized[key] = "******"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_payload(value)
        else:
            sanitized[key] = value
    return sanitized


def truncate_payload(text: str, max_size: int = None) -> str:
    """截断超长 payload"""
    if max_size is None:
        max_size = settings.LOG_MAX_PAYLOAD_SIZE
    if len(text) > max_size:
        return text[:max_size] + "...[TRUNCATED]"
    return text


# ============================================================
# 4. Loguru 初始化
# ============================================================
def init_loguru():
    """初始化日志系统"""
    if not settings.LOG_ENABLED:
        print("⚠️  日志系统已关闭 (LOG_ENABLED=False)")
        return

    # 初始化脱敏字段列表
    _init_sanitize_fields()

    # 移除默认 handler
    logger.remove()

    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>[{extra[trace_id]}]</cyan> "
        "<blue>[{extra[module]}]</blue> | "
        "<level>{message}</level>"
    )

    # 默认 extra 绑定
    logger.configure(extra={"trace_id": "-", "module": "system"})

    # ---- 控制台 sink（开发环境） ----
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # 确保日志根目录存在
    log_dir = settings.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    # 解析压缩格式
    compression = settings.LOG_COMPRESSION if settings.LOG_COMPRESSION != "None" else None

    # ---- 按模块注册独立 file sink ----
    modules = [m.strip().lower() for m in settings.LOG_MODULES.split(",") if m.strip()]
    # 确保 error 和 crash 目录也被创建
    all_dirs = modules + ["error", "crash"]

    for mod in all_dirs:
        mod_dir = os.path.join(log_dir, mod)
        os.makedirs(mod_dir, exist_ok=True)

    # 为每个业务模块创建独立 sink
    for mod in modules:
        mod_dir = os.path.join(log_dir, mod)
        logger.add(
            os.path.join(mod_dir, f"{mod}_{{time:YYYY-MM-DD}}.log"),
            format=log_format,
            level=settings.LOG_LEVEL,
            rotation=settings.LOG_ROTATION,
            retention=settings.LOG_RETENTION,
            compression=compression,
            filter=lambda record, m=mod: record["extra"].get("module", "").lower() == m,
            enqueue=True,  # 异步写入，不阻塞主线程
            encoding="utf-8",
        )

    # ---- error/ sink：汇聚所有 ERROR 及以上级别 ----
    error_dir = os.path.join(log_dir, "error")
    logger.add(
        os.path.join(error_dir, "error_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression=compression,
        enqueue=True,
        encoding="utf-8",
    )

    # ---- crash/ sink：仅 CRITICAL 级别 ----
    crash_dir = os.path.join(log_dir, "crash")
    logger.add(
        os.path.join(crash_dir, "crash_{time:YYYY-MM-DD}.log"),
        format=log_format,
        level="CRITICAL",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression=compression,
        enqueue=True,
        encoding="utf-8",
    )

    # ---- 接管 uvicorn / gunicorn / sqlalchemy 日志 ----
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn", "gunicorn.error", "sqlalchemy.engine"]:
        target_logger = logging.getLogger(name)
        target_logger.handlers = [InterceptHandler()]
        target_logger.propagate = False

    # ---- 注册崩溃保护 ----
    _register_crash_handlers()

    logger.bind(module="system").info(
        f"✅ 日志系统初始化完成 | 级别={settings.LOG_LEVEL} | 目录={os.path.abspath(log_dir)} | 模块={modules}"
    )


# ============================================================
# 5. 崩溃保护
# ============================================================
def _register_crash_handlers():
    """注册全局崩溃/异常/信号处理器"""

    # 全局未捕获异常
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.bind(module="system").critical(
            f"💥 未捕获异常 (Uncaught Exception): {exc_type.__name__}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _excepthook

    # 进程退出记录
    def _on_exit():
        logger.bind(module="system").info("🛑 进程正在退出 (atexit)")

    atexit.register(_on_exit)

    # 信号处理（SIGTERM 等）
    def _signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        logger.bind(module="system").critical(f"⚡ 收到终止信号 {sig_name} (signum={signum})，进程即将退出")
        sys.exit(0)

    # 仅在主线程中注册信号
    try:
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
    except (ValueError, OSError):
        # 非主线程或不支持的平台
        pass

    # stderr 重定向到 loguru
    sys.stderr = _StderrRedirector()


class _StderrRedirector:
    """将 stderr 输出重定向到 loguru"""

    def write(self, message):
        if message and message.strip():
            logger.bind(module="system").opt(depth=1).warning(f"[stderr] {message.rstrip()}")

    def flush(self):
        pass

    def fileno(self):
        return sys.__stderr__.fileno()

    def isatty(self):
        return False


# ============================================================
# 6. 工厂方法
# ============================================================
def get_module_logger(module: str):
    """返回绑定了指定模块的 logger 实例"""
    return logger.bind(module=module.lower())
