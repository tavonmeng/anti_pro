"""创意工作台业务服务。

系统只负责持久化 brief、运行记录和结果；Hermes Agent 负责生成、委派评估与迭代。
"""

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.models.creative_agent import (
    CreativeAgentStep,
    CreativeDesignerFeedback,
    CreativeIdea,
    CreativeIteration,
    CreativeMemoryEntry,
    CreativeReview,
    CreativeRun,
    CreativeRunEvent,
    CreativeSession,
)
from app.models.order import Order
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
)
from app.services.hermes_client import HermesClient


TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

RUBRIC = [
    {"key": "goal_fit", "name": "目标匹配度", "max": 10},
    {"key": "visual_impact", "name": "视觉冲击力", "max": 15},
    {"key": "naked_eye_3d_fit", "name": "裸眼3D适配度", "max": 15},
    {"key": "spreadability", "name": "传播性", "max": 15},
    {"key": "brand_asset_fit", "name": "品牌资产关联度", "max": 10},
    {"key": "execution_feasibility", "name": "执行可行性", "max": 10},
    {"key": "cost_benefit", "name": "成本收益比", "max": 10},
    {"key": "originality", "name": "原创性与差异化", "max": 8},
    {"key": "emotional_power", "name": "情绪感染力", "max": 5},
    {"key": "compliance_risk", "name": "合规与风险", "max": 2},
]


async def list_sessions(
    db: AsyncSession,
    *,
    admin_id: str,
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = select(CreativeSession).where(
        or_(CreativeSession.visibility == "team", CreativeSession.created_by_id == admin_id)
    )
    if keyword:
        query = query.where(CreativeSession.title.ilike(f"%{keyword.strip()}%"))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(
        query.order_by(desc(CreativeSession.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    sessions = result.scalars().all()
    return {"data": [_serialize_session(item) for item in sessions], "total": total}


async def create_session(
    db: AsyncSession,
    *,
    request: CreativeSessionCreate,
    admin_id: str,
    admin_name: str,
) -> dict[str, Any]:
    brief = dict(request.brief or {})
    source_type = request.source_type
    source_order_id = request.source_order_id
    customer_user_id = request.customer_user_id

    if source_type == "order":
        if not source_order_id:
            raise HTTPException(status_code=400, detail="source_type=order 时必须提供 source_order_id")
        order = await _get_order_or_404(db, source_order_id)
        customer_user_id = customer_user_id or order.user_id
        if not brief:
            brief = _build_order_brief(order)

    title = (request.title or brief.get("project_name") or brief.get("campaign_name") or "").strip()
    if not title:
        title = "创意会话"

    session = CreativeSession(
        title=title[:200],
        created_by_id=admin_id,
        created_by_name=admin_name,
        visibility=request.visibility,
        source_type=source_type,
        source_order_id=source_order_id,
        customer_user_id=customer_user_id,
        brief_json=brief,
        designer_direction=_text_value(request.designer_direction or brief.get("designer_direction")),
        seed_ideas=request.seed_ideas or [item for item in _as_list(brief.get("seed_ideas")) if isinstance(item, dict)],
        status="draft",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return await get_session_detail(db, session.id)


async def update_session(
    db: AsyncSession,
    *,
    session_id: str,
    request: CreativeSessionUpdate,
    admin_id: str,
) -> dict[str, Any]:
    session = await _get_accessible_session_or_404(db, session_id, admin_id)
    if request.title is not None:
        session.title = request.title.strip()[:200] or session.title
    if request.visibility is not None:
        session.visibility = request.visibility
    if request.brief is not None:
        session.brief_json = request.brief
    if request.designer_direction is not None:
        session.designer_direction = request.designer_direction.strip()
    if request.seed_ideas is not None:
        session.seed_ideas = request.seed_ideas
    if request.selected_idea_id is not None:
        session.selected_idea_id = request.selected_idea_id or None
    await db.commit()
    return await get_session_detail(db, session_id)


async def get_session_detail(
    db: AsyncSession,
    session_id: str,
    admin_id: Optional[str] = None,
) -> dict[str, Any]:
    if admin_id:
        session = await _get_accessible_session_or_404(db, session_id, admin_id)
    else:
        result = await db.execute(select(CreativeSession).where(CreativeSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="创意会话不存在")

    ideas_result = await db.execute(
        select(CreativeIdea)
        .where(CreativeIdea.session_id == session_id)
        .order_by(CreativeIdea.version, CreativeIdea.created_at)
    )
    ideas = ideas_result.scalars().all()

    reviews_by_idea: dict[str, list[CreativeReview]] = {}
    if ideas:
        idea_ids = [idea.id for idea in ideas]
        reviews_result = await db.execute(
            select(CreativeReview)
            .where(CreativeReview.idea_id.in_(idea_ids))
            .order_by(desc(CreativeReview.created_at))
        )
        for review in reviews_result.scalars().all():
            reviews_by_idea.setdefault(review.idea_id, []).append(review)

    runs_result = await db.execute(
        select(CreativeRun)
        .where(CreativeRun.session_id == session_id)
        .order_by(desc(CreativeRun.created_at))
        .limit(20)
    )
    iterations_result = await db.execute(
        select(CreativeIteration)
        .where(CreativeIteration.session_id == session_id)
        .order_by(CreativeIteration.created_at, CreativeIteration.round_index)
    )
    steps_result = await db.execute(
        select(CreativeAgentStep)
        .where(CreativeAgentStep.session_id == session_id)
        .order_by(CreativeAgentStep.created_at, CreativeAgentStep.step_index)
        .limit(200)
    )
    feedbacks_result = await db.execute(
        select(CreativeDesignerFeedback)
        .where(CreativeDesignerFeedback.session_id == session_id)
        .order_by(desc(CreativeDesignerFeedback.created_at))
        .limit(100)
    )
    return {
        **_serialize_session(session),
        "ideas": [_serialize_idea(idea, reviews_by_idea.get(idea.id, [])) for idea in ideas],
        "runs": [_serialize_run(run) for run in runs_result.scalars().all()],
        "iterations": [_serialize_iteration(item) for item in iterations_result.scalars().all()],
        "agent_steps": [_serialize_agent_step(item) for item in steps_result.scalars().all()],
        "designer_feedbacks": [_serialize_feedback(item) for item in feedbacks_result.scalars().all()],
    }


async def build_order_brief(db: AsyncSession, order_id: str) -> dict[str, Any]:
    order = await _get_order_or_404(db, order_id)
    return _build_order_brief(order)


async def create_idea(
    db: AsyncSession,
    *,
    session_id: str,
    request: CreativeIdeaCreate,
    admin_id: str,
) -> dict[str, Any]:
    session = await _get_accessible_session_or_404(db, session_id, admin_id)
    max_version = (
        await db.execute(select(func.max(CreativeIdea.version)).where(CreativeIdea.session_id == session.id))
    ).scalar() or 0
    idea = CreativeIdea(
        session_id=session.id,
        version=max_version + 1,
        title=request.title.strip()[:200],
        core_concept=request.core_concept,
        spatial_mechanism=request.spatial_mechanism,
        story_outline=request.story_outline,
        production_notes=request.production_notes,
        risk_notes=request.risk_notes,
        tags=request.tags,
        created_by_role="user",
    )
    db.add(idea)
    await db.commit()
    await db.refresh(idea)
    return _serialize_idea(idea, [])


async def create_designer_feedback(
    db: AsyncSession,
    *,
    session_id: str,
    request: CreativeDesignerFeedbackCreate,
    admin_id: str,
    admin_name: str,
) -> dict[str, Any]:
    session = await _get_accessible_session_or_404(db, session_id, admin_id)
    if request.target_idea_id:
        idea = await _get_idea_or_404(db, request.target_idea_id)
        if idea.session_id != session.id:
            raise HTTPException(status_code=400, detail="反馈目标方案不属于该创意会话")
    feedback = CreativeDesignerFeedback(
        session_id=session.id,
        run_id=request.run_id,
        target_idea_id=request.target_idea_id,
        feedback_text=request.feedback_text.strip(),
        priority=request.priority,
        constraints=request.constraints,
        liked_parts=request.liked_parts,
        disliked_parts=request.disliked_parts,
        requested_changes=request.requested_changes,
        created_by_id=admin_id,
        created_by_name=admin_name,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return _serialize_feedback(feedback)


async def list_designer_feedbacks(
    db: AsyncSession,
    *,
    session_id: str,
    admin_id: str,
) -> list[dict[str, Any]]:
    await _get_accessible_session_or_404(db, session_id, admin_id)
    result = await db.execute(
        select(CreativeDesignerFeedback)
        .where(CreativeDesignerFeedback.session_id == session_id)
        .order_by(desc(CreativeDesignerFeedback.created_at))
    )
    return [_serialize_feedback(item) for item in result.scalars().all()]


async def start_auto_run(
    db: AsyncSession,
    *,
    session_id: str,
    request: CreativeAutoRunRequest,
    admin_id: str,
) -> dict[str, Any]:
    session = await _get_accessible_session_or_404(db, session_id, admin_id)
    if not session.brief_json:
        raise HTTPException(status_code=400, detail="请先填写 brief，再启动创意 Agent")

    active_result = await db.execute(
        select(CreativeRun)
        .where(CreativeRun.session_id == session_id, CreativeRun.status.in_(["queued", "running", "stopping"]))
        .order_by(desc(CreativeRun.created_at))
        .limit(1)
    )
    active_run = active_result.scalar_one_or_none()
    if active_run:
        raise HTTPException(status_code=409, detail="该创意会话已有运行中的 Agent")

    team_memory, personal_memory = await _load_memory(
        db,
        admin_id=admin_id,
        use_team=request.use_team_memory,
        use_personal=request.use_personal_memory,
    )
    instructions, input_text = _build_hermes_prompt(
        session=session,
        request=request,
        team_memory=team_memory,
        personal_memory=personal_memory,
    )

    run = CreativeRun(
        session_id=session.id,
        run_type="auto_optimize",
        status="queued",
        provider="hermes",
        hermes_session_id=f"creative:{session.id}",
        input_json={
            "request": _model_dump(request),
            "brief": session.brief_json or {},
            "designer_direction": _effective_designer_direction(session, request.designer_direction),
            "seed_ideas": _effective_seed_ideas(session, request.seed_ideas),
            "team_memory_count": len(team_memory),
            "personal_memory_count": len(personal_memory),
            "hermes_profile": settings.HERMES_CREATIVE_PROFILE,
        },
    )
    db.add(run)
    session.status = "running"
    await db.flush()
    await _record_run_event(
        db,
        run,
        "backend.queued",
        "已创建创意自动优化运行，准备提交 Hermes",
        {"run_type": run.run_type, "request": _model_dump(request)},
    )
    await db.commit()
    await db.refresh(run)

    try:
        hermes_run = await HermesClient().create_run(
            input_text=input_text,
            session_id=run.hermes_session_id,
            instructions=instructions,
        )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(db, run, "backend.failed", "提交 Hermes 失败", {"error": str(exc.detail)})
        await db.commit()
        raise

    run.status = _normalize_run_status(hermes_run.get("status") or "running")
    run.hermes_run_id = hermes_run.get("run_id") or hermes_run.get("id")
    run.output_json = {"hermes_create": hermes_run}
    run.started_at = datetime.now()
    await _record_run_event(db, run, "hermes.started", "Hermes 创意 Agent 已启动", hermes_run)
    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def start_idea_run(
    db: AsyncSession,
    *,
    idea_id: str,
    request: CreativeIdeaRunRequest,
    admin_id: str,
    run_type: str,
) -> dict[str, Any]:
    idea = await _get_idea_or_404(db, idea_id)
    session = await _get_accessible_session_or_404(db, idea.session_id, admin_id)

    active_result = await db.execute(
        select(CreativeRun)
        .where(CreativeRun.session_id == session.id, CreativeRun.status.in_(["queued", "running", "stopping"]))
        .order_by(desc(CreativeRun.created_at))
        .limit(1)
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该创意会话已有运行中的 Agent")

    team_memory, personal_memory = await _load_memory(
        db,
        admin_id=admin_id,
        use_team=request.use_team_memory,
        use_personal=request.use_personal_memory,
    )
    instructions, input_text = _build_idea_run_prompt(
        session=session,
        idea=idea,
        request=request,
        run_type=run_type,
        team_memory=team_memory,
        personal_memory=personal_memory,
    )
    run = CreativeRun(
        session_id=session.id,
        run_type=run_type,
        status="queued",
        provider="hermes",
        hermes_session_id=f"creative:{session.id}",
        input_json={
            "request": _model_dump(request),
            "brief": session.brief_json or {},
            "designer_direction": _effective_designer_direction(session, request.designer_direction),
            "seed_ideas": session.seed_ideas or [],
            "target_idea_id": idea.id,
            "target_idea": _serialize_idea(idea, []),
            "team_memory_count": len(team_memory),
            "personal_memory_count": len(personal_memory),
            "hermes_profile": settings.HERMES_CREATIVE_PROFILE,
        },
    )
    db.add(run)
    session.status = "running"
    await db.flush()
    await _record_run_event(
        db,
        run,
        "backend.queued",
        "已创建单方案评估/迭代运行，准备提交 Hermes",
        {"run_type": run.run_type, "idea_id": idea.id, "request": _model_dump(request)},
    )
    await db.commit()
    await db.refresh(run)

    try:
        hermes_run = await HermesClient().create_run(
            input_text=input_text,
            session_id=run.hermes_session_id,
            instructions=instructions,
        )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(db, run, "backend.failed", "提交 Hermes 失败", {"error": str(exc.detail)})
        await db.commit()
        raise

    run.status = _normalize_run_status(hermes_run.get("status") or "running")
    run.hermes_run_id = hermes_run.get("run_id") or hermes_run.get("id")
    run.output_json = {"hermes_create": hermes_run}
    run.started_at = datetime.now()
    await _record_run_event(db, run, "hermes.started", "Hermes 单方案运行已启动", hermes_run)
    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def start_continue_run(
    db: AsyncSession,
    *,
    session_id: str,
    request: CreativeContinueRunRequest,
    admin_id: str,
    admin_name: str,
) -> dict[str, Any]:
    session = await _get_accessible_session_or_404(db, session_id, admin_id)
    active_result = await db.execute(
        select(CreativeRun)
        .where(CreativeRun.session_id == session.id, CreativeRun.status.in_(["queued", "running", "stopping"]))
        .order_by(desc(CreativeRun.created_at))
        .limit(1)
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该创意会话已有运行中的 Agent")

    feedback = await _resolve_or_create_feedback(
        db,
        session=session,
        request=request,
        admin_id=admin_id,
        admin_name=admin_name,
    )
    target_idea = await _resolve_continue_target_idea(db, session=session, request=request, feedback=feedback)
    if not target_idea:
        raise HTTPException(status_code=400, detail="请先选择一个目标方案，或等待 Agent 生成方案后再继续迭代")

    team_memory, personal_memory = await _load_memory(
        db,
        admin_id=admin_id,
        use_team=request.use_team_memory,
        use_personal=request.use_personal_memory,
    )
    history = await _build_continue_history(db, session_id=session.id, target_idea_id=target_idea.id)
    instructions, input_text = _build_continue_prompt(
        session=session,
        target_idea=target_idea,
        feedback=feedback,
        request=request,
        history=history,
        team_memory=team_memory,
        personal_memory=personal_memory,
    )

    run = CreativeRun(
        session_id=session.id,
        run_type="continue_with_feedback",
        status="queued",
        provider="hermes",
        hermes_session_id=f"creative:{session.id}",
        input_json={
            "request": _model_dump(request),
            "brief": session.brief_json or {},
            "designer_direction": session.designer_direction or "",
            "seed_ideas": session.seed_ideas or [],
            "target_idea_id": target_idea.id,
            "target_idea": _serialize_idea(target_idea, []),
            "designer_feedback": _serialize_feedback(feedback),
            "history": history,
            "team_memory_count": len(team_memory),
            "personal_memory_count": len(personal_memory),
            "hermes_profile": settings.HERMES_CREATIVE_PROFILE,
        },
    )
    db.add(run)
    session.status = "running"
    feedback.status = "used"
    await db.flush()
    feedback.run_id = run.id
    await _record_run_event(
        db,
        run,
        "backend.queued",
        "已根据设计师反馈创建继续迭代运行，准备提交 Hermes",
        {"run_type": run.run_type, "feedback_id": feedback.id, "target_idea_id": target_idea.id},
    )
    await db.commit()
    await db.refresh(run)

    try:
        hermes_run = await HermesClient().create_run(
            input_text=input_text,
            session_id=run.hermes_session_id,
            instructions=instructions,
        )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.finished_at = datetime.now()
        session.status = "failed"
        feedback.status = "submitted"
        await _record_run_event(db, run, "backend.failed", "提交 Hermes 失败", {"error": str(exc.detail)})
        await db.commit()
        raise

    run.status = _normalize_run_status(hermes_run.get("status") or "running")
    run.hermes_run_id = hermes_run.get("run_id") or hermes_run.get("id")
    run.output_json = {"hermes_create": hermes_run}
    run.started_at = datetime.now()
    await _record_run_event(db, run, "hermes.started", "Hermes 已根据设计师反馈继续迭代", hermes_run)
    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def refresh_run_from_hermes(db: AsyncSession, run_id: str) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    result = await db.execute(select(CreativeSession).where(CreativeSession.id == run.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="创意会话不存在")

    if run.status in TERMINAL_STATUSES:
        return _serialize_run(run)
    if not run.hermes_run_id:
        return _serialize_run(run)

    previous_status = run.status
    hermes_payload = await HermesClient().get_run(run.hermes_run_id)
    normalized = _normalize_run_status(hermes_payload.get("status") or run.status)
    run.status = normalized
    output_text = _extract_hermes_output_text(hermes_payload)
    output_json = dict(run.output_json or {})
    output_json["hermes_status"] = hermes_payload
    if output_text:
        output_json["raw_output"] = output_text
    run.output_json = output_json
    if previous_status != normalized:
        await _record_run_event(
            db,
            run,
            "hermes.status",
            f"Hermes 状态更新: {previous_status} -> {normalized}",
            {"previous_status": previous_status, "status": normalized},
            source="hermes",
        )

    if normalized == "completed":
        await _persist_creative_output(db, session=session, run=run, output_text=output_text)
        run.finished_at = run.finished_at or datetime.now()
        session.status = "completed"
        await _record_run_event(db, run, "backend.completed", "创意结果已解析并入库", {"run_id": run.id})
    elif normalized in {"failed", "cancelled"}:
        run.finished_at = run.finished_at or datetime.now()
        run.error = run.error or _extract_hermes_error(hermes_payload)
        session.status = normalized
        await _record_run_event(
            db,
            run,
            f"backend.{normalized}",
            "Hermes 创意运行已结束",
            {"status": normalized, "error": run.error},
        )
    else:
        session.status = "running"

    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def get_run_detail(db: AsyncSession, run_id: str) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    return _serialize_run(run)


async def list_run_events(db: AsyncSession, run_id: str) -> list[dict[str, Any]]:
    await _get_run_or_404(db, run_id)
    result = await db.execute(
        select(CreativeRunEvent)
        .where(CreativeRunEvent.run_id == run_id)
        .order_by(CreativeRunEvent.sequence, CreativeRunEvent.created_at)
    )
    return [_serialize_event(event) for event in result.scalars().all()]


async def list_run_steps(db: AsyncSession, run_id: str) -> list[dict[str, Any]]:
    await _get_run_or_404(db, run_id)
    result = await db.execute(
        select(CreativeAgentStep)
        .where(CreativeAgentStep.run_id == run_id)
        .order_by(CreativeAgentStep.step_index, CreativeAgentStep.created_at)
    )
    return [_serialize_agent_step(step) for step in result.scalars().all()]


async def stream_run_events(run_id: str) -> AsyncIterator[str]:
    async with async_session_maker() as db:
        run = await _get_run_or_404(db, run_id)
        hermes_run_id = run.hermes_run_id
        stored_events = await list_run_events(db, run_id)

    for event in stored_events:
        yield _format_sse(event.get("event_type") or "stored", event)

    if not hermes_run_id:
        yield _format_sse("backend.done", {"message": "该运行还没有 Hermes run_id"})
        return

    async for event in HermesClient().stream_run_events(hermes_run_id):
        event_type = _text_value(event.get("event") or "hermes.event")[:60] or "hermes.event"
        data_text = _text_value(event.get("data"))
        payload = _parse_event_data(data_text)
        async with async_session_maker() as db:
            run = await _get_run_or_none(db, run_id)
            if run:
                await _record_run_event(
                    db,
                    run,
                    event_type,
                    _event_message(payload, data_text),
                    payload if isinstance(payload, dict) else {"data": data_text},
                    source="hermes",
                )
                await db.commit()
        yield _format_sse(event_type, payload if payload else {"data": data_text})


async def wait_for_run_completion(db: AsyncSession, run_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + float(settings.HERMES_CREATIVE_BACKGROUND_TIMEOUT or 300.0)
    interval = max(1.0, float(settings.HERMES_CREATIVE_POLL_INTERVAL or 2.0))
    payload = await get_run_detail(db, run_id)
    while time.monotonic() < deadline:
        payload = await refresh_run_from_hermes(db, run_id)
        if payload.get("status") in TERMINAL_STATUSES:
            return payload
        await asyncio.sleep(interval)
    return payload


async def watch_hermes_run(run_id: str) -> None:
    """Background polling best effort.

    前端仍应通过 /runs/{id} 轮询；后台任务只是让结果尽快入库。
    """
    deadline = time.monotonic() + float(settings.HERMES_CREATIVE_BACKGROUND_TIMEOUT or 300.0)
    interval = max(1.0, float(settings.HERMES_CREATIVE_POLL_INTERVAL or 2.0))
    while time.monotonic() < deadline:
        async with async_session_maker() as db:
            try:
                payload = await refresh_run_from_hermes(db, run_id)
                if payload.get("status") in TERMINAL_STATUSES:
                    return
            except Exception:
                return
        await asyncio.sleep(interval)

    async with async_session_maker() as db:
        run = await _get_run_or_none(db, run_id)
        if run and run.status not in TERMINAL_STATUSES:
            run.error = "后台轮询超时，前端可继续手动刷新运行状态"
            await db.commit()


async def stop_run(db: AsyncSession, run_id: str) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    if run.status in TERMINAL_STATUSES:
        return _serialize_run(run)
    if run.hermes_run_id:
        await HermesClient().stop_run(run.hermes_run_id)
    run.status = "stopping"
    await _record_run_event(db, run, "backend.stopping", "已向 Hermes 发送停止请求", {"run_id": run.id})
    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def get_hermes_status() -> dict[str, Any]:
    if not settings.HERMES_AGENT_ENABLED:
        return {
            "enabled": False,
            "healthy": False,
            "message": "Hermes Agent 未启用",
            "creative_profile": settings.HERMES_CREATIVE_PROFILE,
            "skills_dir": settings.HERMES_CREATIVE_SKILLS_DIR,
            "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        }
    client = HermesClient()
    health = await client.health()
    capabilities: dict[str, Any] = {}
    try:
        capabilities = await client.get_capabilities()
    except HTTPException:
        capabilities = {}
    return {
        "enabled": True,
        "healthy": True,
        "health": health,
        "capabilities": capabilities,
        "creative_profile": settings.HERMES_CREATIVE_PROFILE,
        "skills_dir": settings.HERMES_CREATIVE_SKILLS_DIR,
        "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
    }


async def list_memory_entries(
    db: AsyncSession,
    *,
    admin_id: str,
    scope: Optional[str] = None,
) -> list[dict[str, Any]]:
    query = select(CreativeMemoryEntry).where(
        or_(CreativeMemoryEntry.scope == "team", CreativeMemoryEntry.owner_id == admin_id)
    )
    if scope:
        query = query.where(CreativeMemoryEntry.scope == scope)
    result = await db.execute(query.order_by(desc(CreativeMemoryEntry.updated_at)))
    return [_serialize_memory(item) for item in result.scalars().all()]


async def create_memory_entry(
    db: AsyncSession,
    *,
    request: CreativeMemoryCreate,
    admin_id: str,
) -> dict[str, Any]:
    entry = CreativeMemoryEntry(
        scope=request.scope,
        owner_id=admin_id if request.scope == "personal" else None,
        kind=request.kind,
        content=request.content.strip(),
        tags=request.tags,
        status=request.status,
        created_by_id=admin_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _serialize_memory(entry)


async def update_memory_entry(
    db: AsyncSession,
    *,
    entry_id: str,
    request: CreativeMemoryUpdate,
    admin_id: str,
) -> dict[str, Any]:
    result = await db.execute(
        select(CreativeMemoryEntry).where(
            CreativeMemoryEntry.id == entry_id,
            or_(CreativeMemoryEntry.scope == "team", CreativeMemoryEntry.owner_id == admin_id),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="创意 Memory 不存在")
    if request.kind is not None:
        entry.kind = request.kind
    if request.content is not None:
        entry.content = request.content.strip()
    if request.tags is not None:
        entry.tags = request.tags
    if request.status is not None:
        entry.status = request.status
    await db.commit()
    await db.refresh(entry)
    return _serialize_memory(entry)


async def _persist_creative_output(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    output_text: str,
) -> None:
    output_json = dict(run.output_json or {})
    if output_json.get("persisted_idea_ids"):
        return

    parsed = _parse_json_output(output_text)
    if not parsed:
        run.error = "Hermes 输出未包含可解析的 JSON 创意结果"
        await _record_run_event(db, run, "backend.parse_failed", run.error, {"output_preview": output_text[:1000]})
        return

    await _persist_agent_steps(db, session=session, run=run, parsed=parsed)
    output_json = dict(run.output_json or {})

    if run.run_type == "evaluate":
        await _persist_evaluation_output(db, session=session, run=run, parsed=parsed)
        await _persist_iterations(db, session=session, run=run, parsed=parsed)
        await _persist_memory_candidates(db, run=run, parsed=parsed)
        return

    ideas_payload = _as_list(
        parsed.get("ideas")
        or parsed.get("final_ideas")
        or parsed.get("optimized_ideas")
        or parsed.get("idea_versions")
    )
    if not ideas_payload and isinstance(parsed.get("idea"), dict):
        ideas_payload = [parsed["idea"]]
    if not ideas_payload:
        run.error = "Hermes 输出 JSON 中没有 ideas"
        output_json["parsed_output"] = parsed
        run.output_json = output_json
        await _record_run_event(db, run, "backend.parse_failed", run.error, {"parsed_keys": list(parsed.keys())})
        return

    max_version = (
        await db.execute(select(func.max(CreativeIdea.version)).where(CreativeIdea.session_id == session.id))
    ).scalar() or 0

    selected_index = _selected_index(parsed.get("selected_idea_index"), len(ideas_payload))
    created_ids: list[str] = []
    previous_id: Optional[str] = None
    for idx, idea_payload in enumerate(ideas_payload):
        if not isinstance(idea_payload, dict):
            continue
        review_payload = _review_payload_for(parsed, idea_payload, idx)
        total_score = _extract_total_score(review_payload, idea_payload)
        idea = CreativeIdea(
            session_id=session.id,
            parent_id=idea_payload.get("parent_id") or previous_id or (run.input_json or {}).get("target_idea_id"),
            run_id=run.id,
            version=max_version + idx + 1,
            title=_text_value(idea_payload.get("title") or idea_payload.get("name") or f"创意方案 {idx + 1}")[:200],
            core_concept=_text_value(
                idea_payload.get("core_concept")
                or idea_payload.get("concept")
                or idea_payload.get("big_idea")
            ),
            spatial_mechanism=_text_value(
                idea_payload.get("spatial_mechanism")
                or idea_payload.get("naked_eye_3d_mechanism")
                or idea_payload.get("3d_mechanism")
            ),
            story_outline=_text_value(
                idea_payload.get("story_outline")
                or idea_payload.get("story")
                or idea_payload.get("script")
            ),
            production_notes=_text_value(
                idea_payload.get("production_notes")
                or idea_payload.get("execution_notes")
                or idea_payload.get("feasibility_notes")
            ),
            risk_notes=_text_value(idea_payload.get("risk_notes") or idea_payload.get("risks")),
            tags=_as_list(idea_payload.get("tags")),
            status="selected" if idx == selected_index else "proposed",
            score=total_score,
            created_by_role="agent",
        )
        db.add(idea)
        await db.flush()
        created_ids.append(idea.id)
        previous_id = idea.id

        if review_payload:
            review = _build_review(idea_id=idea.id, run_id=run.id, payload=review_payload, fallback_score=total_score)
            db.add(review)

    if created_ids:
        if selected_index is not None and selected_index < len(created_ids):
            session.selected_idea_id = created_ids[selected_index]
        else:
            session.selected_idea_id = created_ids[-1]

    output_json["parsed_output"] = parsed
    output_json["persisted_idea_ids"] = created_ids
    output_json["selected_idea_id"] = session.selected_idea_id
    run.output_json = output_json
    await _persist_iterations(db, session=session, run=run, parsed=parsed)
    await _persist_memory_candidates(db, run=run, parsed=parsed)
    await _record_run_event(
        db,
        run,
        "backend.persisted",
        f"已保存 {len(created_ids)} 个创意方案",
        {"idea_ids": created_ids, "selected_idea_id": session.selected_idea_id},
    )


async def _persist_evaluation_output(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    parsed: dict[str, Any],
) -> None:
    output_json = dict(run.output_json or {})
    if output_json.get("persisted_review_id"):
        return

    target_idea_id = (run.input_json or {}).get("target_idea_id")
    if not target_idea_id:
        run.error = "评估运行缺少 target_idea_id"
        return

    idea = await _get_idea_or_404(db, target_idea_id)
    if idea.session_id != session.id:
        raise HTTPException(status_code=400, detail="评估结果与创意会话不匹配")

    parsed_idea = parsed.get("idea") if isinstance(parsed.get("idea"), dict) else {}
    review_payload = (
        parsed.get("review")
        or parsed.get("evaluation")
        or parsed.get("quality_review")
        or _review_payload_for(parsed, parsed_idea, 0)
    )
    if not isinstance(review_payload, dict):
        ideas = _as_list(parsed.get("ideas"))
        if ideas and isinstance(ideas[0], dict):
            review_payload = _review_payload_for(parsed, ideas[0], 0)
    if not isinstance(review_payload, dict) or not review_payload:
        run.error = "Hermes 输出 JSON 中没有可保存的 review"
        output_json["parsed_output"] = parsed
        run.output_json = output_json
        await _record_run_event(db, run, "backend.parse_failed", run.error, {"parsed_keys": list(parsed.keys())})
        return

    total_score = _extract_total_score(review_payload, {"score": idea.score or 0})
    review = _build_review(idea_id=idea.id, run_id=run.id, payload=review_payload, fallback_score=total_score)
    db.add(review)
    await db.flush()
    idea.score = review.total_score
    output_json["parsed_output"] = parsed
    output_json["persisted_review_id"] = review.id
    run.output_json = output_json
    await _record_run_event(
        db,
        run,
        "backend.persisted",
        "已保存单方案质检结果",
        {"idea_id": idea.id, "review_id": review.id, "total_score": review.total_score},
    )


async def _persist_agent_steps(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    parsed: dict[str, Any],
) -> None:
    output_json = dict(run.output_json or {})
    if output_json.get("persisted_agent_step_ids"):
        return

    items = _as_list(
        parsed.get("react_trace")
        or parsed.get("agent_steps")
        or parsed.get("steps")
        or parsed.get("audit_trace")
    )
    created_ids: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            item = {"output_summary": _text_value(item)}
        dimension_deltas = _build_dimension_deltas(item)
        step = CreativeAgentStep(
            session_id=session.id,
            run_id=run.id,
            step_index=_to_int(item.get("step") or item.get("step_index") or item.get("index")) or index,
            phase=_normalize_phase(item.get("phase") or item.get("type")),
            role=_text_value(item.get("role") or item.get("agent") or item.get("actor"))[:60],
            tool_name=_text_value(item.get("tool_name") or item.get("tool") or item.get("action_tool"))[:100],
            input_summary=_text_value(item.get("input_summary") or item.get("input") or item.get("action_input")),
            output_summary=_text_value(item.get("output_summary") or item.get("output") or item.get("result_summary")),
            observation=_text_value(item.get("observation") or item.get("observed")),
            reflection_summary=_text_value(
                item.get("reflection_summary")
                or item.get("reflection")
                or item.get("reasoning_summary")
            ),
            decision=_text_value(item.get("decision") or item.get("selected_decision")),
            next_action=_text_value(item.get("next_action") or item.get("next")),
            score_snapshot=_as_dict(item.get("score_snapshot") or item.get("scores") or item.get("scorecard")),
            dimension_deltas=dimension_deltas,
            payload_json=item,
        )
        db.add(step)
        await db.flush()
        created_ids.append(step.id)

    output_json["persisted_agent_step_ids"] = created_ids
    run.output_json = output_json
    if created_ids:
        await _record_run_event(
            db,
            run,
            "backend.agent_steps_persisted",
            f"已保存 {len(created_ids)} 条 ReAct-style 审计步骤",
            {"agent_step_ids": created_ids},
        )


async def _resolve_or_create_feedback(
    db: AsyncSession,
    *,
    session: CreativeSession,
    request: CreativeContinueRunRequest,
    admin_id: str,
    admin_name: str,
) -> CreativeDesignerFeedback:
    if request.feedback_id:
        result = await db.execute(
            select(CreativeDesignerFeedback).where(
                CreativeDesignerFeedback.id == request.feedback_id,
                CreativeDesignerFeedback.session_id == session.id,
            )
        )
        feedback = result.scalar_one_or_none()
        if not feedback:
            raise HTTPException(status_code=404, detail="设计师反馈不存在")
        return feedback

    if not request.feedback_text.strip():
        raise HTTPException(status_code=400, detail="继续迭代需要 feedback_id 或 feedback_text")

    feedback = CreativeDesignerFeedback(
        session_id=session.id,
        target_idea_id=request.target_idea_id,
        feedback_text=request.feedback_text.strip(),
        priority=request.priority,
        constraints=request.constraints,
        liked_parts=request.liked_parts,
        disliked_parts=request.disliked_parts,
        requested_changes=request.requested_changes,
        created_by_id=admin_id,
        created_by_name=admin_name,
    )
    db.add(feedback)
    await db.flush()
    return feedback


async def _resolve_continue_target_idea(
    db: AsyncSession,
    *,
    session: CreativeSession,
    request: CreativeContinueRunRequest,
    feedback: CreativeDesignerFeedback,
) -> Optional[CreativeIdea]:
    target_idea_id = request.target_idea_id or feedback.target_idea_id or session.selected_idea_id
    if target_idea_id:
        idea = await _get_idea_or_404(db, target_idea_id)
        if idea.session_id != session.id:
            raise HTTPException(status_code=400, detail="目标方案不属于该创意会话")
        return idea
    result = await db.execute(
        select(CreativeIdea)
        .where(CreativeIdea.session_id == session.id)
        .order_by(desc(CreativeIdea.score), desc(CreativeIdea.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _build_continue_history(
    db: AsyncSession,
    *,
    session_id: str,
    target_idea_id: str,
) -> dict[str, Any]:
    iterations_result = await db.execute(
        select(CreativeIteration)
        .where(CreativeIteration.session_id == session_id)
        .order_by(desc(CreativeIteration.created_at))
        .limit(8)
    )
    steps_result = await db.execute(
        select(CreativeAgentStep)
        .where(CreativeAgentStep.session_id == session_id)
        .order_by(desc(CreativeAgentStep.created_at))
        .limit(20)
    )
    reviews_result = await db.execute(
        select(CreativeReview)
        .where(CreativeReview.idea_id == target_idea_id)
        .order_by(desc(CreativeReview.created_at))
        .limit(3)
    )
    feedbacks_result = await db.execute(
        select(CreativeDesignerFeedback)
        .where(CreativeDesignerFeedback.session_id == session_id)
        .order_by(desc(CreativeDesignerFeedback.created_at))
        .limit(5)
    )
    return {
        "recent_iterations": [_serialize_iteration(item) for item in reversed(iterations_result.scalars().all())],
        "recent_agent_steps": [_serialize_agent_step(item) for item in reversed(steps_result.scalars().all())],
        "target_idea_reviews": [_serialize_review(item) for item in reviews_result.scalars().all()],
        "recent_designer_feedbacks": [_serialize_feedback(item) for item in feedbacks_result.scalars().all()],
    }


async def _persist_iterations(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    parsed: dict[str, Any],
) -> None:
    output_json = dict(run.output_json or {})
    if output_json.get("persisted_iteration_ids"):
        return
    items = _as_list(parsed.get("iteration_summary") or parsed.get("iterations") or parsed.get("rounds"))
    created_ids: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            item = {"summary": _text_value(item)}
        score_before = _to_int(item.get("score_before"))
        score_after = _to_int(item.get("score_after"))
        dimension_deltas = _build_dimension_deltas(item)
        key_improvements = _key_improvements(dimension_deltas)
        iteration = CreativeIteration(
            session_id=session.id,
            run_id=run.id,
            round_index=_to_int(item.get("round") or item.get("round_index")) or index,
            action=_text_value(item.get("action") or item.get("phase"))[:80],
            score_before=score_before,
            score_after=score_after,
            score_delta=_score_delta(score_before, score_after, item.get("score_delta")),
            focus=_text_value(item.get("focus") or item.get("target_problem")),
            summary=_text_value(item.get("summary") or item.get("reason") or item.get("decision")),
            agent_explanation=_text_value(
                item.get("agent_explanation")
                or item.get("why_it_improved")
                or item.get("why")
                or item.get("explanation")
            ),
            dimension_deltas=dimension_deltas,
            key_improvements=key_improvements,
            payload_json=item,
        )
        db.add(iteration)
        await db.flush()
        created_ids.append(iteration.id)
    output_json["persisted_iteration_ids"] = created_ids
    run.output_json = output_json
    if created_ids:
        await _record_run_event(
            db,
            run,
            "backend.iterations_persisted",
            f"已保存 {len(created_ids)} 轮迭代记录",
            {"iteration_ids": created_ids},
        )


async def _persist_memory_candidates(
    db: AsyncSession,
    *,
    run: CreativeRun,
    parsed: dict[str, Any],
) -> None:
    output_json = dict(run.output_json or {})
    if output_json.get("persisted_memory_candidate_ids"):
        return
    request = (run.input_json or {}).get("request") or {}
    if request.get("save_memory_candidates") is False:
        return

    candidates = _as_list(
        parsed.get("team_memory_candidates")
        or parsed.get("memory_candidates")
        or parsed.get("lessons_learned")
    )
    created_ids: list[str] = []
    for candidate in candidates:
        if isinstance(candidate, dict):
            content = _text_value(candidate.get("content") or candidate.get("lesson") or candidate.get("principle"))
            kind = _text_value(candidate.get("kind") or "lesson")[:50] or "lesson"
            tags = _as_str_list(candidate.get("tags"))
        else:
            content = _text_value(candidate)
            kind = "lesson"
            tags = []
        if not content:
            continue
        exists = await db.execute(
            select(CreativeMemoryEntry.id)
            .where(CreativeMemoryEntry.scope == "team", CreativeMemoryEntry.content == content)
            .limit(1)
        )
        if exists.scalar_one_or_none():
            continue
        entry = CreativeMemoryEntry(
            scope="team",
            owner_id=None,
            kind=kind,
            content=content,
            tags=tags,
            status="proposed",
            created_by_id="agent",
        )
        db.add(entry)
        await db.flush()
        created_ids.append(entry.id)

    output_json["persisted_memory_candidate_ids"] = created_ids
    run.output_json = output_json
    if created_ids:
        await _record_run_event(
            db,
            run,
            "backend.memory_candidates_persisted",
            f"已沉淀 {len(created_ids)} 条待审核团队 Memory",
            {"memory_entry_ids": created_ids},
        )


def _build_review(idea_id: str, run_id: str, payload: dict[str, Any], fallback_score: int) -> CreativeReview:
    scores = payload.get("scores") or payload.get("score_table") or payload.get("dimensions") or {}
    total_score = _extract_total_score(payload, {"score": fallback_score})
    return CreativeReview(
        idea_id=idea_id,
        run_id=run_id,
        rubric_version=_text_value(payload.get("rubric_version") or "creative_qc_v1")[:50],
        scores_json=scores if isinstance(scores, dict) else {"items": scores},
        total_score=total_score,
        grade=_text_value(payload.get("grade") or _grade(total_score))[:30],
        core_issues=_as_list(payload.get("core_issues") or payload.get("issues") or payload.get("problems")),
        recommendations=_as_list(
            payload.get("recommendations") or payload.get("optimization_suggestions") or payload.get("suggestions")
        ),
        risk_flags=_as_list(payload.get("risk_flags") or payload.get("risks")),
        summary=_text_value(payload.get("summary") or payload.get("overall_judgement") or payload.get("judgement")),
    )


def _build_hermes_prompt(
    *,
    session: CreativeSession,
    request: CreativeAutoRunRequest,
    team_memory: list[dict[str, Any]],
    personal_memory: list[dict[str, Any]],
) -> tuple[str, str]:
    instructions = """你是 Unique Vision 的 Hermes 创意工作台总编排 Agent，服务裸眼 3D / 户外大屏商业创意团队。

必须遵守：
1. 只读取本轮 brief 与记忆内容，不修改订单、客户资料或业务状态。
2. 创意目标是商业可执行的传播方案，不是纯艺术赏析。
3. 如果 Hermes 工具可用，优先使用 delegate_task 并行委派独立评估子代理；再使用 execute_code 进行分数汇总、停止条件判断和版本选择。
4. 子代理必须拿到完整 brief、评分标准、当前方案和约束，不依赖父上下文。
5. 如果 skills 工具可用，先加载 creative-orchestrator、creative-rubric-evaluator、creative-iteration-loop。
6. 每轮迭代必须说清楚哪些评分维度上升了、每个维度为什么上升、对应改动是什么；不能只写“整体更好”。
7. 使用 ReAct-style 审计轨迹，但只输出面向用户的摘要，不要输出隐藏思考链。每一步用 plan/action/observation/reflection/decision 描述做了什么、看到了什么、决定什么。
8. 如果设计师提供了 designer_direction 或 seed_ideas，必须优先作为创作约束；如需偏离，必须在 react_trace 的 decision 里说明原因。
9. 输出必须是一个严格 JSON object，不要 Markdown、不要代码块、不要解释性前后缀。
"""

    designer_direction = _effective_designer_direction(session, request.designer_direction)
    seed_ideas = _effective_seed_ideas(session, request.seed_ideas)
    workflow = {
        "goal": "生成并自动迭代裸眼3D创意方案",
        "max_rounds": request.max_rounds,
        "target_score": request.target_score,
        "idea_count": request.idea_count,
        "strategy": request.strategy,
        "use_parallel_evaluators": request.use_parallel_evaluators,
        "designer_direction": designer_direction,
        "seed_ideas": seed_ideas,
        "hard_constraints": request.hard_constraints,
        "negative_examples": request.negative_examples,
        "recommended_skills": [
            "creative-orchestrator",
            "creative-rubric-evaluator",
            "creative-iteration-loop",
        ],
        "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        "delegation_hint": [
            {
                "name": "rubric_evaluator",
                "goal": "按10项质检标准逐项评分并给扣分理由",
                "toolsets": ["skills"],
            },
            {
                "name": "production_evaluator",
                "goal": "评估裸眼3D制作、屏体适配、周期、素材和成本风险",
                "toolsets": ["skills"],
            },
            {
                "name": "risk_evaluator",
                "goal": "评估合规、品牌安全、误导性表达和现场传播风险",
                "toolsets": ["skills"],
            },
        ],
        "execute_code_hint": "用 Python 汇总维度得分、计算总分、判断是否达到 target_score，并选择最佳版本。",
    }
    expected_output = {
        "session_summary": "一句话说明本轮创意方向与迭代结果",
        "react_trace": [
            {
                "step": 1,
                "phase": "plan/action/observation/reflection/decision",
                "role": "orchestrator/rubric_evaluator/production_evaluator/risk_evaluator",
                "tool_name": "delegate_task/execute_code/skill name",
                "input_summary": "本步输入摘要",
                "output_summary": "本步输出摘要",
                "observation": "观察到的事实、评分或约束",
                "reflection_summary": "面向用户的反思摘要，不能包含隐藏思考链",
                "decision": "本步决定",
                "next_action": "下一步动作",
                "score_snapshot": {"total_score": 0},
                "dimension_deltas": [],
            }
        ],
        "selected_idea_index": 0,
        "iteration_summary": [
            {
                "round": 1,
                "action": "生成/评估/优化",
                "score_before": 0,
                "score_after": 0,
                "score_delta": 0,
                "focus": "本轮主要优化的问题",
                "summary": "本轮改了什么",
                "agent_explanation": "为什么这些修改会提升评分，必须具体到创意机制/传播机制/执行机制",
                "dimension_deltas": [
                    {
                        "key": "naked_eye_3d_fit",
                        "name": "裸眼3D适配度",
                        "score_before": 8,
                        "score_after": 12,
                        "delta": 4,
                        "change": "从平面物体展示改为利用屏幕边缘穿出与遮挡关系",
                        "why": "新增透视纵深、边缘破框和前后层级，直接增强裸眼3D成立度",
                    }
                ],
                "key_improvements": [
                    {
                        "key": "naked_eye_3d_fit",
                        "delta": 4,
                        "why": "上涨原因",
                    }
                ],
            }
        ],
        "ideas": [
            {
                "title": "方案名",
                "core_concept": "核心创意",
                "spatial_mechanism": "裸眼3D空间机制",
                "story_outline": "画面/分镜/节奏",
                "production_notes": "执行要点、素材需求、周期建议",
                "risk_notes": "风险与规避",
                "tags": ["标签"],
                "review": {
                    "rubric_version": "creative_qc_v1",
                    "scores": {
                        "goal_fit": {"score": 0, "max": 10, "reason": ""},
                        "visual_impact": {"score": 0, "max": 15, "reason": ""},
                        "naked_eye_3d_fit": {"score": 0, "max": 15, "reason": ""},
                        "spreadability": {"score": 0, "max": 15, "reason": ""},
                        "brand_asset_fit": {"score": 0, "max": 10, "reason": ""},
                        "execution_feasibility": {"score": 0, "max": 10, "reason": ""},
                        "cost_benefit": {"score": 0, "max": 10, "reason": ""},
                        "originality": {"score": 0, "max": 8, "reason": ""},
                        "emotional_power": {"score": 0, "max": 5, "reason": ""},
                        "compliance_risk": {"score": 0, "max": 2, "reason": ""},
                    },
                    "total_score": 0,
                    "grade": "A/B/C/D",
                    "core_issues": ["核心问题"],
                    "recommendations": ["优化建议"],
                    "risk_flags": ["风险点"],
                    "summary": "综合判断",
                },
            }
        ],
        "team_memory_candidates": ["值得沉淀为团队方法论的经验"],
    }

    input_payload = {
        "workflow": workflow,
        "rubric": RUBRIC,
        "brief": session.brief_json or {},
        "designer_direction": designer_direction,
        "seed_ideas": seed_ideas,
        "reference_cases": request.reference_cases,
        "team_memory": team_memory,
        "personal_memory": personal_memory,
        "output_schema": expected_output,
    }
    return instructions, json.dumps(input_payload, ensure_ascii=False, indent=2)


def _build_idea_run_prompt(
    *,
    session: CreativeSession,
    idea: CreativeIdea,
    request: CreativeIdeaRunRequest,
    run_type: str,
    team_memory: list[dict[str, Any]],
    personal_memory: list[dict[str, Any]],
) -> tuple[str, str]:
    action = "评估现有创意" if run_type == "evaluate" else "基于质检结果优化现有创意"
    instructions = """你是 Unique Vision 的 Hermes 创意质检/迭代 Agent。

必须遵守：
1. 只处理输入中的目标创意，不修改订单或业务状态。
2. 评估时必须使用 creative-rubric-evaluator；迭代时必须同时使用 creative-rubric-evaluator 与 creative-iteration-loop。
3. 如果 delegate_task 可用，委派 rubric_evaluator、production_evaluator、risk_evaluator 并行独立审查。
4. 如果 execute_code 可用，用 Python 汇总评分并判断是否达到 target_score。
5. 迭代输出必须说明哪些维度分数上升、为什么上升、对应改动是什么，供前端直接展示。
6. 输出 ReAct-style 审计轨迹，但只写面向用户的摘要，不输出隐藏思考链。
7. 如果设计师方向和评分建议冲突，优先保留设计师方向的核心意图，并说明取舍。
8. 输出必须是严格 JSON object，不要 Markdown、不要代码块。
"""
    target_idea = _serialize_idea(idea, [])
    designer_direction = _effective_designer_direction(session, request.designer_direction)
    output_schema: dict[str, Any]
    if run_type == "evaluate":
        output_schema = {
            "session_summary": "一句话综合判断",
            "react_trace": [
                {
                    "step": 1,
                    "phase": "plan/action/observation/reflection/decision",
                    "role": "rubric_evaluator",
                    "tool_name": "creative-rubric-evaluator",
                    "input_summary": "本步输入摘要",
                    "output_summary": "本步输出摘要",
                    "observation": "观察到的评分问题或约束",
                    "reflection_summary": "面向用户的反思摘要，不能包含隐藏思考链",
                    "decision": "本步决定",
                    "next_action": "下一步动作",
                    "score_snapshot": {"total_score": 0},
                    "dimension_deltas": [],
                }
            ],
            "review": {
                "rubric_version": "creative_qc_v1",
                "scores": {
                    item["key"]: {"score": 0, "max": item["max"], "reason": ""}
                    for item in RUBRIC
                },
                "total_score": 0,
                "grade": "A/B/C/D",
                "core_issues": ["核心问题"],
                "recommendations": ["优化建议"],
                "risk_flags": ["风险点"],
                "summary": "综合判断",
            },
            "iteration_summary": [],
            "team_memory_candidates": [],
        }
    else:
        output_schema = {
            "session_summary": "一句话说明如何优化",
            "react_trace": [
                {
                    "step": 1,
                    "phase": "plan/action/observation/reflection/decision",
                    "role": "iteration_agent",
                    "tool_name": "creative-iteration-loop",
                    "input_summary": "本步输入摘要",
                    "output_summary": "本步输出摘要",
                    "observation": "观察到的扣分点",
                    "reflection_summary": "面向用户的反思摘要，不能包含隐藏思考链",
                    "decision": "本步决定",
                    "next_action": "下一步动作",
                    "score_snapshot": {"total_score": 0},
                    "dimension_deltas": [],
                }
            ],
            "selected_idea_index": 0,
            "iteration_summary": [
                {
                    "round": 1,
                    "action": "优化",
                    "score_before": 0,
                    "score_after": 0,
                    "score_delta": 0,
                    "focus": "本轮主要优化的问题",
                    "summary": "本轮改了什么",
                    "agent_explanation": "为什么这些修改会提升评分，必须具体到创意机制/传播机制/执行机制",
                    "dimension_deltas": [
                        {
                            "key": "visual_impact",
                            "name": "视觉冲击力",
                            "score_before": 10,
                            "score_after": 13,
                            "delta": 3,
                            "change": "从普通产品露出改为第一秒强反差破屏视觉",
                            "why": "观众第一眼能看到更明确的主视觉和动作峰值，停留/拍摄动机更强",
                        }
                    ],
                    "key_improvements": [
                        {"key": "visual_impact", "delta": 3, "why": "上涨原因"}
                    ],
                }
            ],
            "ideas": [
                {
                    "title": "优化后方案名",
                    "core_concept": "核心创意",
                    "spatial_mechanism": "裸眼3D空间机制",
                    "story_outline": "画面/分镜/节奏",
                    "production_notes": "执行要点、素材需求、周期建议",
                    "risk_notes": "风险与规避",
                    "tags": ["标签"],
                    "review": {
                        "rubric_version": "creative_qc_v1",
                        "scores": {
                            item["key"]: {"score": 0, "max": item["max"], "reason": ""}
                            for item in RUBRIC
                        },
                        "total_score": 0,
                        "grade": "A/B/C/D",
                        "core_issues": ["核心问题"],
                        "recommendations": ["优化建议"],
                        "risk_flags": ["风险点"],
                        "summary": "综合判断",
                    },
                }
            ],
            "team_memory_candidates": [],
        }

    input_payload = {
        "workflow": {
            "goal": action,
            "run_type": run_type,
            "max_rounds": request.max_rounds,
            "target_score": request.target_score,
            "focus": request.focus,
            "designer_direction": designer_direction,
            "use_parallel_evaluators": request.use_parallel_evaluators,
            "recommended_skills": [
                "creative-rubric-evaluator",
                "creative-iteration-loop",
            ],
            "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        },
        "rubric": RUBRIC,
        "brief": session.brief_json or {},
        "designer_direction": designer_direction,
        "seed_ideas": session.seed_ideas or [],
        "target_idea": target_idea,
        "team_memory": team_memory,
        "personal_memory": personal_memory,
        "output_schema": output_schema,
    }
    return instructions, json.dumps(input_payload, ensure_ascii=False, indent=2)


def _build_continue_prompt(
    *,
    session: CreativeSession,
    target_idea: CreativeIdea,
    feedback: CreativeDesignerFeedback,
    request: CreativeContinueRunRequest,
    history: dict[str, Any],
    team_memory: list[dict[str, Any]],
    personal_memory: list[dict[str, Any]],
) -> tuple[str, str]:
    instructions = """你是 Unique Vision 的 Hermes 创意继续迭代 Agent，正在接手设计师中途反馈。

必须遵守：
1. 这是人类介入后的继续迭代，不是从零重写。必须继承目标方案、历史评估、历史迭代和设计师反馈。
2. 先判断设计师反馈属于：保留、删除、强化、转向、降成本、降风险、换风格、补细节。
3. 如果设计师反馈与评分建议冲突，优先说明取舍；不能直接忽略设计师反馈。
4. 输出 ReAct-style 审计轨迹，但只写面向用户的摘要，不输出隐藏思考链。
5. 每轮迭代必须说明哪些维度分数上升、为什么上升、对应改动是什么。
6. 输出严格 JSON object，不要 Markdown、不要代码块。
"""
    target = _serialize_idea(target_idea, [])
    feedback_payload = _serialize_feedback(feedback)
    output_schema = {
        "session_summary": "一句话说明如何吸收设计师反馈继续优化",
        "react_trace": [
            {
                "step": 1,
                "phase": "plan/action/observation/reflection/decision",
                "role": "continue_iteration_agent",
                "tool_name": "creative-iteration-loop",
                "input_summary": "本步输入摘要，包含设计师反馈",
                "output_summary": "本步输出摘要",
                "observation": "观察到的历史问题、设计师偏好或评分约束",
                "reflection_summary": "面向用户的反思摘要，不能包含隐藏思考链",
                "decision": "如何采纳或调整设计师反馈",
                "next_action": "下一步动作",
                "score_snapshot": {"total_score": 0},
                "dimension_deltas": [],
            }
        ],
        "selected_idea_index": 0,
        "iteration_summary": [
            {
                "round": 1,
                "action": "根据设计师反馈继续优化",
                "score_before": 0,
                "score_after": 0,
                "score_delta": 0,
                "focus": "本轮主要吸收的设计师反馈",
                "summary": "本轮改了什么",
                "agent_explanation": "为什么这些修改既回应反馈又提升评分",
                "dimension_deltas": [
                    {
                        "key": "spreadability",
                        "name": "传播性",
                        "score_before": 9,
                        "score_after": 12,
                        "delta": 3,
                        "change": "加入更明确的拍摄瞬间和人群聚集点",
                        "why": "设计师要求更有社交传播感，因此把视觉峰值前置并增加可拍摄动作",
                    }
                ],
                "key_improvements": [],
            }
        ],
        "ideas": [
            {
                "title": "继续迭代后的方案名",
                "core_concept": "核心创意",
                "spatial_mechanism": "裸眼3D空间机制",
                "story_outline": "画面/分镜/节奏",
                "production_notes": "执行要点、素材需求、周期建议",
                "risk_notes": "风险与规避",
                "tags": ["标签"],
                "review": {
                    "rubric_version": "creative_qc_v1",
                    "scores": {
                        item["key"]: {"score": 0, "max": item["max"], "reason": ""}
                        for item in RUBRIC
                    },
                    "total_score": 0,
                    "grade": "A/B/C/D",
                    "core_issues": ["核心问题"],
                    "recommendations": ["优化建议"],
                    "risk_flags": ["风险点"],
                    "summary": "综合判断",
                },
            }
        ],
        "team_memory_candidates": [],
    }
    input_payload = {
        "workflow": {
            "goal": "根据设计师反馈继续迭代创意方案",
            "run_type": "continue_with_feedback",
            "max_rounds": request.max_rounds,
            "target_score": request.target_score,
            "feedback_priority": feedback.priority,
            "use_parallel_evaluators": request.use_parallel_evaluators,
            "recommended_skills": [
                "creative-rubric-evaluator",
                "creative-iteration-loop",
            ],
            "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        },
        "rubric": RUBRIC,
        "brief": session.brief_json or {},
        "designer_direction": session.designer_direction or "",
        "seed_ideas": session.seed_ideas or [],
        "target_idea": target,
        "designer_feedback": feedback_payload,
        "history": history,
        "team_memory": team_memory,
        "personal_memory": personal_memory,
        "output_schema": output_schema,
    }
    return instructions, json.dumps(input_payload, ensure_ascii=False, indent=2)


async def _load_memory(
    db: AsyncSession,
    *,
    admin_id: str,
    use_team: bool,
    use_personal: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    team_memory: list[dict[str, Any]] = []
    personal_memory: list[dict[str, Any]] = []
    if use_team:
        result = await db.execute(
            select(CreativeMemoryEntry)
            .where(CreativeMemoryEntry.scope == "team", CreativeMemoryEntry.status == "approved")
            .order_by(desc(CreativeMemoryEntry.updated_at))
            .limit(20)
        )
        team_memory = [_serialize_memory(item) for item in result.scalars().all()]
    if use_personal:
        result = await db.execute(
            select(CreativeMemoryEntry)
            .where(
                CreativeMemoryEntry.scope == "personal",
                CreativeMemoryEntry.owner_id == admin_id,
                CreativeMemoryEntry.status == "approved",
            )
            .order_by(desc(CreativeMemoryEntry.updated_at))
            .limit(20)
        )
        personal_memory = [_serialize_memory(item) for item in result.scalars().all()]
    return team_memory, personal_memory


async def _get_accessible_session_or_404(db: AsyncSession, session_id: str, admin_id: str) -> CreativeSession:
    result = await db.execute(
        select(CreativeSession).where(
            CreativeSession.id == session_id,
            or_(CreativeSession.visibility == "team", CreativeSession.created_by_id == admin_id),
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="创意会话不存在")
    return session


async def _get_order_or_404(db: AsyncSession, order_id: str) -> Order:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


async def _get_run_or_404(db: AsyncSession, run_id: str) -> CreativeRun:
    run = await _get_run_or_none(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="创意 Agent 运行不存在")
    return run


async def _get_run_or_none(db: AsyncSession, run_id: str) -> Optional[CreativeRun]:
    result = await db.execute(select(CreativeRun).where(CreativeRun.id == run_id))
    return result.scalar_one_or_none()


async def _get_idea_or_404(db: AsyncSession, idea_id: str) -> CreativeIdea:
    result = await db.execute(select(CreativeIdea).where(CreativeIdea.id == idea_id))
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="创意方案不存在")
    return idea


def _build_order_brief(order: Order) -> dict[str, Any]:
    order_data = order.order_data or {}
    order_type = order.order_type.value if hasattr(order.order_type, "value") else str(order.order_type)
    status = order.status.value if hasattr(order.status, "value") else str(order.status)
    return {
        "source": "order",
        "source_order_id": order.id,
        "order_number": order.order_number,
        "order_type": order_type,
        "order_status": status,
        "project_name": order_data.get("project_name") or order_data.get("projectName") or order_data.get("brand") or "",
        "brand_or_customer": order_data.get("brand") or order_data.get("company") or order_data.get("customerName") or "",
        "target_goal": order_data.get("target_goal") or order_data.get("goal") or order_data.get("purpose") or "",
        "media_location": order_data.get("city_location") or order_data.get("location") or order_data.get("city") or "",
        "screen_resource": {
            "type": order_data.get("screen_type") or order_data.get("screenType") or "",
            "size": order_data.get("screen_size") or order_data.get("screenSize") or "",
            "resolution": order_data.get("resolution") or "",
            "shape": order_data.get("screen_shape") or order_data.get("screenShape") or "",
        },
        "theme_concept": order_data.get("theme_concept") or order_data.get("themeConcept") or order_data.get("content") or "",
        "target_audience": order_data.get("target_audience") or order_data.get("audience") or "",
        "budget_range": order_data.get("budget_range") or order_data.get("budget") or "",
        "timeline": order_data.get("deadline") or order_data.get("timeline") or order_data.get("delivery_time") or "",
        "constraints": order_data.get("constraints") or order_data.get("requirements") or "",
        "raw_order_data": order_data,
    }


async def _record_run_event(
    db: AsyncSession,
    run: CreativeRun,
    event_type: str,
    message: str = "",
    payload: Optional[dict[str, Any]] = None,
    *,
    source: str = "backend",
) -> CreativeRunEvent:
    max_sequence = (
        await db.execute(select(func.max(CreativeRunEvent.sequence)).where(CreativeRunEvent.run_id == run.id))
    ).scalar() or 0
    event = CreativeRunEvent(
        run_id=run.id,
        session_id=run.session_id,
        sequence=max_sequence + 1,
        event_type=event_type[:60],
        message=message,
        payload_json=payload or {},
        source=source,
    )
    db.add(event)
    await db.flush()
    return event


def _serialize_session(session: CreativeSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title,
        "created_by_id": session.created_by_id,
        "created_by_name": session.created_by_name,
        "visibility": session.visibility,
        "source_type": session.source_type,
        "source_order_id": session.source_order_id,
        "customer_user_id": session.customer_user_id,
        "brief": session.brief_json or {},
        "designer_direction": session.designer_direction or "",
        "seed_ideas": session.seed_ideas or [],
        "status": session.status,
        "selected_idea_id": session.selected_idea_id,
        "created_at": _iso(session.created_at),
        "updated_at": _iso(session.updated_at),
    }


def _serialize_idea(idea: CreativeIdea, reviews: list[CreativeReview]) -> dict[str, Any]:
    return {
        "id": idea.id,
        "session_id": idea.session_id,
        "parent_id": idea.parent_id,
        "run_id": idea.run_id,
        "version": idea.version,
        "title": idea.title,
        "core_concept": idea.core_concept,
        "spatial_mechanism": idea.spatial_mechanism,
        "story_outline": idea.story_outline,
        "production_notes": idea.production_notes,
        "risk_notes": idea.risk_notes,
        "tags": idea.tags or [],
        "status": idea.status,
        "score": idea.score,
        "created_by_role": idea.created_by_role,
        "created_at": _iso(idea.created_at),
        "updated_at": _iso(idea.updated_at),
        "reviews": [_serialize_review(review) for review in reviews],
    }


def _serialize_review(review: CreativeReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "idea_id": review.idea_id,
        "run_id": review.run_id,
        "rubric_version": review.rubric_version,
        "scores": review.scores_json or {},
        "total_score": review.total_score,
        "grade": review.grade,
        "core_issues": review.core_issues or [],
        "recommendations": review.recommendations or [],
        "risk_flags": review.risk_flags or [],
        "summary": review.summary,
        "created_at": _iso(review.created_at),
    }


def _serialize_run(run: CreativeRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "session_id": run.session_id,
        "run_type": run.run_type,
        "status": run.status,
        "provider": run.provider,
        "hermes_run_id": run.hermes_run_id,
        "hermes_session_id": run.hermes_session_id,
        "previous_response_id": run.previous_response_id,
        "input": run.input_json or {},
        "output": run.output_json or {},
        "error": run.error,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "created_at": _iso(run.created_at),
        "updated_at": _iso(run.updated_at),
    }


def _serialize_event(event: CreativeRunEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "run_id": event.run_id,
        "session_id": event.session_id,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "message": event.message,
        "payload": event.payload_json or {},
        "source": event.source,
        "created_at": _iso(event.created_at),
    }


def _serialize_agent_step(step: CreativeAgentStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "session_id": step.session_id,
        "run_id": step.run_id,
        "step_index": step.step_index,
        "phase": step.phase,
        "role": step.role,
        "tool_name": step.tool_name,
        "input_summary": step.input_summary,
        "output_summary": step.output_summary,
        "observation": step.observation,
        "reflection_summary": step.reflection_summary,
        "decision": step.decision,
        "next_action": step.next_action,
        "score_snapshot": step.score_snapshot or {},
        "dimension_deltas": step.dimension_deltas or [],
        "payload": step.payload_json or {},
        "created_at": _iso(step.created_at),
    }


def _serialize_feedback(feedback: CreativeDesignerFeedback) -> dict[str, Any]:
    return {
        "id": feedback.id,
        "session_id": feedback.session_id,
        "run_id": feedback.run_id,
        "target_idea_id": feedback.target_idea_id,
        "feedback_text": feedback.feedback_text,
        "priority": feedback.priority,
        "constraints": feedback.constraints or [],
        "liked_parts": feedback.liked_parts or [],
        "disliked_parts": feedback.disliked_parts or [],
        "requested_changes": feedback.requested_changes or [],
        "status": feedback.status,
        "created_by_id": feedback.created_by_id,
        "created_by_name": feedback.created_by_name,
        "created_at": _iso(feedback.created_at),
        "updated_at": _iso(feedback.updated_at),
    }


def _serialize_iteration(iteration: CreativeIteration) -> dict[str, Any]:
    return {
        "id": iteration.id,
        "session_id": iteration.session_id,
        "run_id": iteration.run_id,
        "round_index": iteration.round_index,
        "action": iteration.action,
        "score_before": iteration.score_before,
        "score_after": iteration.score_after,
        "score_delta": iteration.score_delta,
        "focus": iteration.focus,
        "summary": iteration.summary,
        "agent_explanation": iteration.agent_explanation,
        "dimension_deltas": iteration.dimension_deltas or [],
        "key_improvements": iteration.key_improvements or [],
        "payload": iteration.payload_json or {},
        "created_at": _iso(iteration.created_at),
    }


def _serialize_memory(entry: CreativeMemoryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "scope": entry.scope,
        "owner_id": entry.owner_id,
        "kind": entry.kind,
        "content": entry.content,
        "tags": entry.tags or [],
        "status": entry.status,
        "created_by_id": entry.created_by_id,
        "created_at": _iso(entry.created_at),
        "updated_at": _iso(entry.updated_at),
    }


def _parse_json_output(output_text: str) -> dict[str, Any]:
    text = (output_text or "").strip()
    if not text:
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {"items": value}
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            value = json.loads(fence.group(1))
            return value if isinstance(value, dict) else {"items": value}
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(text[start : end + 1])
            return value if isinstance(value, dict) else {"items": value}
        except json.JSONDecodeError:
            return {}
    return {}


def _review_payload_for(parsed: dict[str, Any], idea_payload: dict[str, Any], index: int) -> dict[str, Any]:
    review = (
        idea_payload.get("review")
        or idea_payload.get("evaluation")
        or idea_payload.get("quality_review")
        or idea_payload.get("scorecard")
    )
    if isinstance(review, dict):
        return review
    reviews = _as_list(parsed.get("reviews") or parsed.get("evaluations"))
    if index < len(reviews) and isinstance(reviews[index], dict):
        return reviews[index]
    return {}


def _extract_total_score(review_payload: dict[str, Any], idea_payload: dict[str, Any]) -> int:
    for key in ("total_score", "score", "total", "final_score"):
        value = review_payload.get(key) if review_payload else None
        if value is None:
            value = idea_payload.get(key)
        parsed = _to_int(value)
        if parsed is not None:
            return max(0, min(100, parsed))

    scores = review_payload.get("scores") if review_payload else None
    if isinstance(scores, dict):
        total = 0
        found = False
        for value in scores.values():
            score = _score_value(value)
            if score is not None:
                total += score
                found = True
        if found:
            return max(0, min(100, total))
    return 0


def _build_dimension_deltas(item: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = _as_list(
        item.get("dimension_deltas")
        or item.get("score_changes")
        or item.get("dimension_changes")
        or item.get("improved_dimensions")
    )
    normalized: list[dict[str, Any]] = []
    for delta in explicit:
        if not isinstance(delta, dict):
            continue
        key = _dimension_key(delta.get("key") or delta.get("dimension"))
        score_before = _to_int(delta.get("score_before") or delta.get("before"))
        score_after = _to_int(delta.get("score_after") or delta.get("after"))
        delta_value = _score_delta(score_before, score_after, delta.get("delta"))
        if not key and not delta_value:
            continue
        normalized.append({
            "key": key,
            "name": _dimension_name(key, delta.get("name") or delta.get("dimension_name") or delta.get("dimension")),
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta_value,
            "change": _text_value(delta.get("change") or delta.get("what_changed") or delta.get("modification")),
            "why": _text_value(delta.get("why") or delta.get("reason") or delta.get("explanation")),
        })

    if normalized:
        return sorted(normalized, key=lambda d: d.get("delta") or 0, reverse=True)

    before_scores = item.get("scores_before") or item.get("before_scores")
    after_scores = item.get("scores_after") or item.get("after_scores")
    if not isinstance(before_scores, dict) or not isinstance(after_scores, dict):
        return []

    for raw_key, before_value in before_scores.items():
        key = _dimension_key(raw_key)
        after_value = after_scores.get(raw_key)
        if after_value is None and key:
            after_value = after_scores.get(key)
        score_before = _score_value(before_value)
        score_after = _score_value(after_value)
        delta_value = _score_delta(score_before, score_after, None)
        if delta_value is None or delta_value == 0:
            continue
        normalized.append({
            "key": key,
            "name": _dimension_name(key, raw_key),
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta_value,
            "change": "",
            "why": "",
        })
    return sorted(normalized, key=lambda d: d.get("delta") or 0, reverse=True)


def _key_improvements(dimension_deltas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    improvements = [item for item in dimension_deltas if (item.get("delta") or 0) > 0]
    return [
        {
            "key": item.get("key"),
            "name": item.get("name"),
            "delta": item.get("delta"),
            "score_before": item.get("score_before"),
            "score_after": item.get("score_after"),
            "change": item.get("change"),
            "why": item.get("why"),
        }
        for item in improvements[:5]
    ]


def _score_delta(score_before: Optional[int], score_after: Optional[int], explicit_delta: Any) -> Optional[int]:
    delta = _to_int(explicit_delta)
    if delta is not None:
        return delta
    if score_before is not None and score_after is not None:
        return score_after - score_before
    return None


def _dimension_key(value: Any) -> str:
    raw = _text_value(value)
    if not raw:
        return ""
    normalized = raw.strip().lower()
    alias_map = {
        "目标匹配度": "goal_fit",
        "goal fit": "goal_fit",
        "视觉冲击力": "visual_impact",
        "visual impact": "visual_impact",
        "裸眼3d适配度": "naked_eye_3d_fit",
        "裸眼3D适配度": "naked_eye_3d_fit",
        "3d fit": "naked_eye_3d_fit",
        "传播性": "spreadability",
        "spreadability": "spreadability",
        "品牌资产关联度": "brand_asset_fit",
        "brand asset fit": "brand_asset_fit",
        "执行可行性": "execution_feasibility",
        "execution feasibility": "execution_feasibility",
        "成本收益比": "cost_benefit",
        "cost benefit": "cost_benefit",
        "原创性与差异化": "originality",
        "originality": "originality",
        "情绪感染力": "emotional_power",
        "emotional power": "emotional_power",
        "合规与风险": "compliance_risk",
        "compliance risk": "compliance_risk",
    }
    return alias_map.get(raw) or alias_map.get(normalized) or normalized.replace(" ", "_")


def _dimension_name(key: str, fallback: Any = "") -> str:
    for item in RUBRIC:
        if item["key"] == key:
            return item["name"]
    return _text_value(fallback) or key


def _score_value(value: Any) -> Optional[int]:
    if isinstance(value, dict):
        return _to_int(value.get("score") or value.get("value"))
    return _to_int(value)


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            return int(round(float(match.group(0))))
    return None


def _selected_index(value: Any, length: int) -> Optional[int]:
    idx = _to_int(value)
    if idx is None:
        return None
    if 0 <= idx < length:
        return idx
    if 1 <= idx <= length:
        return idx - 1
    return None


def _extract_hermes_output_text(payload: dict[str, Any]) -> str:
    output = payload.get("output")
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        text = part.get("text") or part.get("output_text")
                        if text:
                            parts.append(str(text))
        return "\n".join(parts)
    if output is not None:
        return str(output)
    return ""


def _extract_hermes_error(payload: dict[str, Any]) -> str:
    error = payload.get("error") or payload.get("last_error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("detail") or error)
    return str(error or "Hermes Agent 运行失败")


def _normalize_run_status(status: str) -> str:
    value = (status or "").lower()
    if value in {"completed", "failed", "cancelled"}:
        return value
    if value in {"stopping"}:
        return "stopping"
    if value in {"queued", "pending", "created", "started", "in_progress", "running"}:
        return "running"
    return "running"


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    return [_text_value(item) for item in _as_list(value) if _text_value(item)]


def _effective_designer_direction(session: CreativeSession, override: str = "") -> str:
    return _text_value(override or session.designer_direction or (session.brief_json or {}).get("designer_direction"))


def _effective_seed_ideas(session: CreativeSession, override: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    if override:
        return override
    seed_ideas = session.seed_ideas or (session.brief_json or {}).get("seed_ideas") or []
    return [item for item in _as_list(seed_ideas) if isinstance(item, dict)]


def _normalize_phase(value: Any) -> str:
    phase = _text_value(value).lower()
    allowed = {"plan", "action", "observation", "reflection", "decision"}
    if phase in allowed:
        return phase
    if phase in {"observe", "observed"}:
        return "observation"
    if phase in {"reflect", "reason", "reasoning"}:
        return "reflection"
    if phase in {"decide", "selection", "select"}:
        return "decision"
    return "action"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _parse_event_data(value: str) -> Any:
    text = (value or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"data": text}


def _event_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        for key in ("message", "summary", "status", "type"):
            if payload.get(key):
                return _text_value(payload.get(key))[:500]
    return fallback[:500]


def _format_sse(event_type: str, payload: Any) -> str:
    return "event: %s\ndata: %s\n\n" % (
        event_type,
        json.dumps(payload, ensure_ascii=False, default=str),
    )


def _text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value).strip()


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value)
