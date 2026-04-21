"""前端交互日志接收 API"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit_database import get_audit_db
from app.models.audit_log import AuditLog
from app.utils.dependencies import get_current_user, AnyUser
from app.utils.log_setup import get_module_logger, sanitize_payload, truncate_payload
from app.utils.validators import generate_id
from app.schemas.response import ApiResponse

import json
import uuid

router = APIRouter(prefix="/logs", tags=["日志"])


class FrontendLogRequest(BaseModel):
    """前端日志请求模型"""
    module: str = Field(..., min_length=1, max_length=30, description="业务模块")
    action: str = Field(..., min_length=1, max_length=200, description="操作标识")
    trace_id: Optional[str] = Field(None, max_length=36, description="前端追踪 ID")
    payload: Optional[dict] = Field(None, description="额外上下文")


class FrontendLogBatchRequest(BaseModel):
    """批量前端日志请求"""
    logs: List[FrontendLogRequest] = Field(..., min_length=1, max_length=50)


@router.post("", response_model=ApiResponse[dict])
async def receive_frontend_log(
    log_data: FrontendLogRequest,
    request: Request,
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_audit_db),
):
    """接收单条前端交互日志"""
    try:
        await _save_frontend_log(log_data, request, current_user, db)
        return ApiResponse(code=200, message="日志已记录", data={"received": 1})
    except Exception as e:
        get_module_logger("system").error(f"前端日志接收失败: {e}")
        return ApiResponse(code=200, message="日志记录异常（不影响业务）", data={"received": 0})


@router.post("/batch", response_model=ApiResponse[dict])
async def receive_frontend_log_batch(
    batch_data: FrontendLogBatchRequest,
    request: Request,
    current_user: AnyUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_audit_db),
):
    """批量接收前端交互日志"""
    count = 0
    for log_data in batch_data.logs:
        try:
            await _save_frontend_log(log_data, request, current_user, db)
            count += 1
        except Exception as e:
            get_module_logger("system").error(f"批量日志写入单条失败: {e}")
    return ApiResponse(code=200, message=f"已记录 {count}/{len(batch_data.logs)} 条日志", data={"received": count})


async def _save_frontend_log(
    log_data: FrontendLogRequest,
    request: Request,
    current_user: AnyUser,
    db: AsyncSession,
):
    """保存单条前端日志到数据库和文件"""
    trace_id = log_data.trace_id or str(uuid.uuid4())[:8]
    module = log_data.module.lower()

    # 脱敏 payload
    payload_str = ""
    if log_data.payload:
        sanitized = sanitize_payload(log_data.payload)
        payload_str = truncate_payload(json.dumps(sanitized, ensure_ascii=False))

    # 提取客户端信息
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.headers.get("x-real-ip") or
        (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "")[:300]

    # 写日志文件
    mod_logger = get_module_logger(module if module != "workspace" else "workspace")
    mod_logger.bind(trace_id=trace_id).info(
        f"[前端] {log_data.action} | user={current_user.username}({current_user.id}) | "
        f"ip={ip} | payload={payload_str[:200]}"
    )

    # 写数据库
    log_entry = AuditLog(
        id=generate_id("log"),
        trace_id=trace_id,
        user_id=current_user.id,
        username=current_user.username,
        type="frontend_action",
        module=log_data.module,
        action=log_data.action,
        ip_address=ip,
        user_agent=user_agent,
        payload=payload_str,
        response_status=None,
        duration_ms=None,
    )
    db.add(log_entry)
    await db.commit()
