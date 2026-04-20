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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import FastAPI

from app.config import settings
from app.utils.log_setup import (
    resolve_module,
    sanitize_payload,
    truncate_payload,
    get_module_logger,
)
from app.utils.security import decode_access_token


# 预解析配置
_db_methods = set()
_db_enabled = False


def _init_config():
    global _db_methods, _db_enabled
    _db_enabled = settings.LOG_DB_ENABLED
    _db_methods = {m.strip().upper() for m in settings.LOG_DB_METHODS.split(",") if m.strip()}


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """全链路审计日志中间件"""

    async def dispatch(self, request: Request, call_next):
        if not settings.LOG_ENABLED:
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

        # ---- 5. 读取请求体（仅写操作） ----
        request_body_str = ""
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                body_bytes = await request.body()
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
            import asyncio
            # 真正的 fire-and-forget 异步任务：扔到事件循环后台执行，主线程立即响应前端，完全不拖慢性能
            try:
                asyncio.create_task(_persist_audit_log(
                    trace_id=trace_id,
                    user_id=user_id,
                    username=username,
                    type="api_call",
                    module=module.capitalize(),
                    action=action_str,
                    ip_address=_get_client_ip(request),
                    user_agent=request.headers.get("user-agent", "")[:300],
                    payload=request_body_str,
                    response_status=status_code,
                    duration_ms=duration_ms,
                ))
            except Exception as e:
                mod_logger.bind(trace_id=trace_id).error(f"审计日志入库失败: {e}")

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
