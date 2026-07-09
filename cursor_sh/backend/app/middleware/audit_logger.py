"""
审计日志中间件

职责：
- 为每个请求生成 Trace-ID
- 解析 JWT 提取用户信息（不查库）
- 按 URL 映射业务模块
- 拦截请求/响应，脱敏后写入日志文件
- 对写操作 (POST/PUT/DELETE) 异步入库
"""

import time
import uuid
import json
import asyncio
from contextlib import suppress
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.utils.log_setup import (
    resolve_module,
    sanitize_payload,
    truncate_payload,
    get_module_logger,
)
from app.utils.security import decode_access_token
from app.utils.request_context import reset_request_context, set_request_context


# 预解析配置
_db_methods = set()
_db_enabled = False
_audit_queue: asyncio.Queue | None = None
_audit_workers: list[asyncio.Task] = []
_dropped_audit_logs = 0
_audit_skip_paths = {
    "/api/website-analytics/visit",
}


def should_skip_audit_logging(path: str) -> bool:
    """Return whether a high-frequency endpoint should bypass audit logging."""
    return path in _audit_skip_paths


def _init_config():
    global _db_methods, _db_enabled
    _db_enabled = settings.LOG_DB_ENABLED
    _db_methods = {m.strip().upper() for m in settings.LOG_DB_METHODS.split(",") if m.strip()}


def start_audit_log_workers():
    """启动有界审计日志入库 worker，避免每个请求无限 create_task。"""
    global _audit_queue, _audit_workers

    _init_config()
    if not _db_enabled or _audit_workers:
        return

    queue_size = max(1, int(settings.LOG_DB_QUEUE_SIZE or 1000))
    worker_count = max(1, int(settings.LOG_DB_WORKERS or 1))
    _audit_queue = asyncio.Queue(maxsize=queue_size)
    _audit_workers = [
        asyncio.create_task(_audit_worker_loop(i), name=f"audit-log-worker-{i}")
        for i in range(worker_count)
    ]


async def stop_audit_log_workers():
    """应用关闭时尽量刷完队列，然后取消 worker。"""
    global _audit_queue, _audit_workers

    queue = _audit_queue
    if queue is not None:
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(queue.join(), timeout=5)

    for task in _audit_workers:
        task.cancel()
    if _audit_workers:
        await asyncio.gather(*_audit_workers, return_exceptions=True)

    _audit_workers = []
    _audit_queue = None


async def _audit_worker_loop(worker_id: int):
    while True:
        queue = _audit_queue
        if queue is None:
            await asyncio.sleep(0.1)
            continue

        payload = await queue.get()
        try:
            await _persist_audit_log(**payload)
        except Exception as e:
            get_module_logger("system").error(f"审计日志 worker {worker_id} 异常: {e}")
        finally:
            queue.task_done()


def _enqueue_audit_log(payload: dict, logger):
    global _dropped_audit_logs

    if _audit_queue is None:
        try:
            start_audit_log_workers()
        except RuntimeError as e:
            logger.error(f"审计日志 worker 启动失败: {e}")
            return

    queue = _audit_queue
    if queue is None:
        return

    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        _dropped_audit_logs += 1
        if _dropped_audit_logs == 1 or _dropped_audit_logs % 100 == 0:
            logger.warning(f"审计日志队列已满，累计丢弃 {_dropped_audit_logs} 条")


def _request_body_skip_reason(request: Request) -> str:
    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" in content_type:
        return "[multipart/form-data payload skipped]"

    content_length_raw = request.headers.get("content-length", "")
    try:
        content_length = int(content_length_raw) if content_length_raw else 0
    except ValueError:
        content_length = 0

    max_read_size = max(int(settings.LOG_MAX_PAYLOAD_SIZE or 4096) * 4, 64 * 1024)
    if content_length > max_read_size:
        return "[payload skipped: %d bytes]" % content_length

    return ""


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """全链路审计日志中间件"""

    async def dispatch(self, request: Request, call_next):
        if should_skip_audit_logging(request.url.path) or not settings.LOG_ENABLED:
            return await call_next(request)

        # 初始化配置（仅首次）
        if not _db_methods:
            _init_config()

        # ---- 1. 生成 Trace-ID ----
        trace_id = str(uuid.uuid4())[:8]

        # ---- 2. 计时开始 ----
        start_time = time.perf_counter()

        # ---- 3. 解析用户（从 JWT，不查库） ----
        user_id = "anonymous"
        username = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("user_id", "anonymous")
                username = payload.get("username", "anonymous")

        # ---- 4. 解析模块 ----
        path = request.url.path
        module = resolve_module(path)
        method = request.method.upper()
        context_token = set_request_context(
            trace_id=trace_id,
            actor_id=user_id,
            actor_username=username,
            method=method,
            path=path,
            ip=_get_client_ip(request),
        )

        # ---- 5. 读取请求体（仅写操作） ----
        request_body_str = ""
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                request_body_str = _request_body_skip_reason(request)
                if not request_body_str:
                    body_bytes = await request.body()
                else:
                    body_bytes = b""
                if body_bytes:
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    try:
                        body_dict = json.loads(body_text)
                        body_dict = sanitize_payload(body_dict)
                        request_body_str = json.dumps(body_dict, ensure_ascii=False)
                    except json.JSONDecodeError:
                        request_body_str = body_text
                    request_body_str = truncate_payload(request_body_str)
            except Exception:
                request_body_str = "[读取请求体失败]"

        # ---- 6. 执行业务 Handler ----
        response: Response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            # 记录未捕获异常
            mod_logger = get_module_logger(module)
            mod_logger.bind(trace_id=trace_id).exception(
                f"💥 未捕获异常 | {method} {path} | user={username}"
            )
            raise
        finally:
            reset_request_context(context_token)

        # ---- 7. 计时结束 ----
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # ---- 8. 写模块日志文件 ----
        mod_logger = get_module_logger(module)
        log_level = "WARNING" if status_code >= 400 else "INFO"
        action_str = f"{method} {path}"

        log_msg = (
            f"{action_str} | {status_code} | {duration_ms}ms | "
            f"user={username}({user_id}) | ip={_get_client_ip(request)}"
        )
        if request_body_str and method in ("POST", "PUT", "PATCH", "DELETE"):
            log_msg += f" | payload={request_body_str[:500]}"

        mod_logger.bind(trace_id=trace_id).log(log_level, log_msg)

        # ---- 9. 写操作入库 ----
        if _db_enabled and method in _db_methods:
            _enqueue_audit_log({
                "trace_id": trace_id,
                "user_id": user_id,
                "username": username,
                "type": "api_call",
                "module": module.capitalize(),
                "action": action_str,
                "ip_address": _get_client_ip(request),
                "user_agent": request.headers.get("user-agent", "")[:300],
                "payload": request_body_str,
                "response_status": status_code,
                "duration_ms": duration_ms,
            }, mod_logger.bind(trace_id=trace_id))

        # ---- 10. 注入 Trace-ID 到响应头 ----
        if response:
            response.headers["X-Trace-ID"] = trace_id

        return response


def _get_client_ip(request: Request) -> str:
    """提取客户端 IP（支持反向代理）"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


async def _persist_audit_log(**kwargs):
    """异步将审计日志写入独立的审计数据库 (audit.db)"""
    from app.audit_database import audit_session_maker
    from app.models.audit_log import AuditLog
    from app.utils.validators import generate_id

    try:
        async with audit_session_maker() as session:
            log_entry = AuditLog(
                id=generate_id("log"),
                **kwargs,
            )
            session.add(log_entry)
            await session.commit()
    except Exception as e:
        # 日志入库失败不应导致请求失败，静默记录到文件
        get_module_logger("system").error(f"审计日志持久化异常: {e}")
