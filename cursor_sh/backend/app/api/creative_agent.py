"""管理员创意 Agent 工作台 API。"""

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.creative_agent import (
    CreativeAutoRunRequest,
    CreativeContinueRunRequest,
    CreativeDesignerFeedbackCreate,
    CreativeIdeaCreate,
    CreativeIdeaRunRequest,
    CreativeMemoryCreate,
    CreativeMemoryUpdate,
    CreativeSessionCreate,
    CreativeSessionUpdate,
    CreativeSkillUpdate,
)
from app.services import creative_agent_service
from app.utils.dependencies import require_admin

router = APIRouter(prefix="/admin/creative-agent", tags=["管理员 — 创意 Agent"])


@router.get("/hermes/status")
async def get_hermes_status(current_admin=Depends(require_admin)):
    """检查 Hermes Agent API Server 是否可用。"""
    return {"code": 200, "data": await creative_agent_service.get_hermes_status()}


@router.get("/orders/{order_id}/brief")
async def get_order_brief(
    order_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """从订单只读构造创意 brief。不会修改订单。"""
    brief = await creative_agent_service.build_order_brief(db, order_id)
    return {"code": 200, "data": brief}


@router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.list_sessions(
        db,
        admin_id=getattr(current_admin, "id", ""),
        page=page,
        page_size=pageSize,
        keyword=keyword,
    )
    return {"code": 200, "data": data}


@router.post("/sessions")
async def create_session(
    request: CreativeSessionCreate,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_name = getattr(current_admin, "username", "") or getattr(current_admin, "phone", "") or ""
    data = await creative_agent_service.create_session(
        db,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
        admin_name=admin_name,
    )
    return {"code": 200, "data": data, "message": "创意会话已创建"}


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.get_session_detail(
        db,
        session_id,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data}


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    request: CreativeSessionUpdate,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.update_session(
        db,
        session_id=session_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data, "message": "创意会话已更新"}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.delete_session(
        db,
        session_id=session_id,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data, "message": "创意会话已删除"}


@router.post("/sessions/{session_id}/auto-run")
async def start_auto_run(
    session_id: str,
    request: CreativeAutoRunRequest,
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    run = await creative_agent_service.start_auto_run(
        db,
        session_id=session_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
    )
    if request.wait_for_completion:
        run = await creative_agent_service.wait_for_run_completion(db, run["id"])
    else:
        background_tasks.add_task(creative_agent_service.watch_hermes_run, run["id"])
    return {"code": 200, "data": run, "message": "创意 Agent 已启动"}


@router.post("/sessions/{session_id}/ideas")
async def create_idea(
    session_id: str,
    request: CreativeIdeaCreate,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.create_idea(
        db,
        session_id=session_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data, "message": "创意方案已保存"}


@router.get("/sessions/{session_id}/feedbacks")
async def list_designer_feedbacks(
    session_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.list_designer_feedbacks(
        db,
        session_id=session_id,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data}


@router.post("/sessions/{session_id}/feedbacks")
async def create_designer_feedback(
    session_id: str,
    request: CreativeDesignerFeedbackCreate,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_name = getattr(current_admin, "username", "") or getattr(current_admin, "phone", "") or ""
    data = await creative_agent_service.create_designer_feedback(
        db,
        session_id=session_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
        admin_name=admin_name,
    )
    return {"code": 200, "data": data, "message": "设计师反馈已保存"}


@router.post("/sessions/{session_id}/continue-run")
async def continue_with_feedback(
    session_id: str,
    request: CreativeContinueRunRequest,
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    admin_name = getattr(current_admin, "username", "") or getattr(current_admin, "phone", "") or ""
    run = await creative_agent_service.start_continue_run(
        db,
        session_id=session_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
        admin_name=admin_name,
    )
    if request.wait_for_completion:
        run = await creative_agent_service.wait_for_run_completion(db, run["id"])
    else:
        background_tasks.add_task(creative_agent_service.watch_hermes_run, run["id"])
    return {"code": 200, "data": run, "message": "创意 Agent 已根据设计师反馈继续迭代"}


@router.post("/ideas/{idea_id}/evaluate")
async def evaluate_idea(
    idea_id: str,
    request: CreativeIdeaRunRequest,
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    run = await creative_agent_service.start_idea_run(
        db,
        idea_id=idea_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
        run_type="evaluate",
    )
    if request.wait_for_completion:
        run = await creative_agent_service.wait_for_run_completion(db, run["id"])
    else:
        background_tasks.add_task(creative_agent_service.watch_hermes_run, run["id"])
    return {"code": 200, "data": run, "message": "创意质检已启动"}


@router.post("/ideas/{idea_id}/iterate")
async def iterate_idea(
    idea_id: str,
    request: CreativeIdeaRunRequest,
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    run = await creative_agent_service.start_idea_run(
        db,
        idea_id=idea_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
        run_type="iterate",
    )
    if request.wait_for_completion:
        run = await creative_agent_service.wait_for_run_completion(db, run["id"])
    else:
        background_tasks.add_task(creative_agent_service.watch_hermes_run, run["id"])
    return {"code": 200, "data": run, "message": "创意迭代已启动"}


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    refresh: bool = Query(True),
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if refresh:
        data = await creative_agent_service.refresh_run_from_hermes(db, run_id)
    else:
        data = await creative_agent_service.get_run_detail(db, run_id)
    return {"code": 200, "data": data}


@router.post("/runs/{run_id}/refresh")
async def refresh_run(
    run_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.refresh_run_from_hermes(db, run_id)
    return {"code": 200, "data": data}


@router.get("/runs/{run_id}/events")
async def list_run_events(
    run_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.list_run_events(db, run_id)
    return {"code": 200, "data": data}


@router.get("/runs/{run_id}/steps")
async def list_run_steps(
    run_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.list_run_steps(db, run_id)
    return {"code": 200, "data": data}


@router.post("/runs/{run_id}/stop")
async def stop_run(
    run_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.stop_run(db, run_id)
    return {"code": 200, "data": data, "message": "已请求停止 Hermes 创意 Agent"}


@router.get("/memory")
async def list_memory(
    scope: str | None = Query(None),
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.list_memory_entries(
        db,
        admin_id=getattr(current_admin, "id", ""),
        scope=scope,
    )
    return {"code": 200, "data": data}


@router.post("/memory")
async def create_memory(
    request: CreativeMemoryCreate,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.create_memory_entry(
        db,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data, "message": "创意 Memory 已保存"}


@router.patch("/memory/{entry_id}")
async def update_memory(
    entry_id: str,
    request: CreativeMemoryUpdate,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    data = await creative_agent_service.update_memory_entry(
        db,
        entry_id=entry_id,
        request=request,
        admin_id=getattr(current_admin, "id", ""),
    )
    return {"code": 200, "data": data, "message": "创意 Memory 已更新"}


@router.get("/skills")
async def list_skills(current_admin=Depends(require_admin)):
    data = await creative_agent_service.list_skill_entries()
    return {"code": 200, "data": data}


@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str, current_admin=Depends(require_admin)):
    data = await creative_agent_service.get_skill_entry(skill_name)
    return {"code": 200, "data": data}


@router.patch("/skills/{skill_name}")
async def update_skill(
    skill_name: str,
    request: CreativeSkillUpdate,
    current_admin=Depends(require_admin),
):
    data = await creative_agent_service.update_skill_entry(skill_name, request)
    return {"code": 200, "data": data, "message": "Skill 已更新"}
