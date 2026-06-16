"""创意工作台业务服务。

系统只负责持久化 brief、运行记录和结果；Hermes Agent 负责生成、委派评估与迭代。
"""

import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
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
    CreativeSkillUpdate,
)
from app.services.creative_evaluator_tool import (
    compact_brief_for_evaluator,
    compact_idea_for_evaluator,
    normalize_core_target_score,
    score_ideas_tool,
)
from app.services.ai_client import post_chat_completion
from app.services.hermes_client import HermesClient


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "stopped"}

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

HERMES_CORE_RUBRIC = RUBRIC[:3]


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
        brief = {**_build_order_brief(order), **brief}

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


async def delete_session(
    db: AsyncSession,
    *,
    session_id: str,
    admin_id: str,
) -> dict[str, Any]:
    session = await _get_accessible_session_or_404(db, session_id, admin_id)
    active_result = await db.execute(
        select(CreativeRun)
        .where(CreativeRun.session_id == session.id, CreativeRun.status.in_(["queued", "running", "stopping"]))
        .order_by(desc(CreativeRun.created_at))
    )
    active_runs = active_result.scalars().all()
    for run in active_runs:
        if run.hermes_run_id:
            try:
                await HermesClient().stop_run(run.hermes_run_id)
            except HTTPException:
                pass
    await db.delete(session)
    await db.commit()
    return {"id": session_id, "deleted": True}


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

    provider = _agent_provider(request.provider)
    run = CreativeRun(
        session_id=session.id,
        run_type="auto_optimize",
        status="queued",
        provider=provider,
        hermes_session_id=f"creative:{session.id}" if provider == "hermes" else None,
        input_json={
            "request": _model_dump(request),
            "brief": session.brief_json or {},
            "designer_direction": _effective_designer_direction(session, request.designer_direction),
            "seed_ideas": _effective_seed_ideas(session, request.seed_ideas),
            "team_memory_count": len(team_memory),
            "personal_memory_count": len(personal_memory),
            "team_memory": _compact_memory_for_prompt(team_memory),
            "personal_memory": _compact_memory_for_prompt(personal_memory, limit=5),
            "agent_provider": provider,
            "hermes_profile": settings.HERMES_CREATIVE_PROFILE,
            "agent_prompt": {
                "instructions": instructions,
                "input_text": input_text,
            },
        },
    )
    db.add(run)
    session.status = "running"
    await db.flush()
    await _record_run_event(
        db,
        run,
        "backend.queued",
        _queued_message(provider, "创意自动优化运行"),
        {"run_type": run.run_type, "request": _model_dump(request)},
    )
    await db.commit()
    await db.refresh(run)

    if _uses_backend_evaluator_tool(run) or provider == "direct_ai":
        return _serialize_run(run)

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
    provider = _agent_provider(request.provider)
    run = CreativeRun(
        session_id=session.id,
        run_type=run_type,
        status="queued",
        provider=provider,
        hermes_session_id=f"creative:{session.id}" if provider == "hermes" else None,
        input_json={
            "request": _model_dump(request),
            "brief": session.brief_json or {},
            "designer_direction": _effective_designer_direction(session, request.designer_direction),
            "seed_ideas": session.seed_ideas or [],
            "target_idea_id": idea.id,
            "target_idea": _serialize_idea(idea, []),
            "team_memory_count": len(team_memory),
            "personal_memory_count": len(personal_memory),
            "agent_provider": provider,
            "hermes_profile": settings.HERMES_CREATIVE_PROFILE,
            "agent_prompt": {
                "instructions": instructions,
                "input_text": input_text,
            },
        },
    )
    db.add(run)
    session.status = "running"
    await db.flush()
    await _record_run_event(
        db,
        run,
        "backend.queued",
        _queued_message(provider, "单方案评估/迭代运行"),
        {"run_type": run.run_type, "idea_id": idea.id, "request": _model_dump(request)},
    )
    await db.commit()
    await db.refresh(run)

    if _uses_backend_evaluator_tool(run) or provider == "direct_ai":
        return _serialize_run(run)

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

    provider = _agent_provider(request.provider)
    run = CreativeRun(
        session_id=session.id,
        run_type="continue_with_feedback",
        status="queued",
        provider=provider,
        hermes_session_id=f"creative:{session.id}" if provider == "hermes" else None,
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
            "agent_provider": provider,
            "hermes_profile": settings.HERMES_CREATIVE_PROFILE,
            "agent_prompt": {
                "instructions": instructions,
                "input_text": input_text,
            },
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
        _queued_message(provider, "设计师反馈继续迭代运行"),
        {"run_type": run.run_type, "feedback_id": feedback.id, "target_idea_id": target_idea.id},
    )
    await db.commit()
    await db.refresh(run)

    if provider == "direct_ai":
        return _serialize_run(run)

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
    elif normalized in {"failed", "cancelled", "stopped"}:
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
    elif _run_timed_out(run):
        await _mark_run_timed_out(db, session=session, run=run)
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


async def wait_for_run_completion(db: AsyncSession, run_id: str) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    if _uses_backend_evaluator_tool(run) and run.status not in TERMINAL_STATUSES:
        return await _process_backend_tool_run(db, run_id)

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
    async with async_session_maker() as db:
        run = await _get_run_or_none(db, run_id)
        if run and _uses_backend_evaluator_tool(run) and run.status not in TERMINAL_STATUSES:
            try:
                await _process_backend_tool_run(db, run_id)
            except Exception:
                return
            return

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
            result = await db.execute(select(CreativeSession).where(CreativeSession.id == run.session_id))
            session = result.scalar_one_or_none()
            if session:
                await _mark_run_timed_out(db, session=session, run=run)
            else:
                run.status = "failed"
                run.error = "后台轮询超时，创意会话不存在"
                run.finished_at = datetime.now()
            await db.commit()


async def _process_backend_tool_run(db: AsyncSession, run_id: str) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    result = await db.execute(select(CreativeSession).where(CreativeSession.id == run.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="创意会话不存在")
    if run.status in TERMINAL_STATUSES:
        return _serialize_run(run)

    prompt = (run.input_json or {}).get("agent_prompt") or {}
    instructions = _text_value(prompt.get("instructions"))
    input_text = _text_value(prompt.get("input_text"))
    if not instructions or not input_text:
        run.status = "failed"
        run.error = f"{_provider_label(run.provider)} 创意 Agent 缺少运行 prompt"
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(db, run, f"{_provider_event_prefix(run.provider)}.failed", run.error, {})
        await db.commit()
        await db.refresh(run)
        return _serialize_run(run)

    if run.run_type == "auto_optimize":
        return await _run_backend_auto_tool_agent(
            db,
            session=session,
            run=run,
            model_name=_tool_flow_model_name(run.provider),
        )

    if run.run_type == "evaluate":
        return await _run_backend_evaluate_tool_agent(
            db,
            session=session,
            run=run,
            model_name=_tool_flow_model_name(run.provider),
        )

    return await _run_direct_ai_agent(
        db,
        session=session,
        run=run,
        instructions=instructions,
        input_text=input_text,
    )


async def stop_run(db: AsyncSession, run_id: str) -> dict[str, Any]:
    run = await _get_run_or_404(db, run_id)
    if run.status in TERMINAL_STATUSES:
        return _serialize_run(run)
    result = await db.execute(select(CreativeSession).where(CreativeSession.id == run.session_id))
    session = result.scalar_one_or_none()
    if run.hermes_run_id:
        await HermesClient().stop_run(run.hermes_run_id)
        run.status = "stopping"
        await _record_run_event(db, run, "backend.stopping", "已向 Agent 发送停止请求", {"run_id": run.id})
    else:
        run.status = "stopped"
        run.finished_at = run.finished_at or datetime.now()
        if session:
            session.status = "stopped"
        await _record_run_event(db, run, "backend.stopped", "Agent 运行已停止", {"run_id": run.id})
    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def _mark_run_timed_out(db: AsyncSession, *, session: CreativeSession, run: CreativeRun) -> None:
    if run.hermes_run_id:
        try:
            await HermesClient().stop_run(run.hermes_run_id)
        except HTTPException:
            pass
    run.status = "failed"
    run.error = run.error or "Hermes 创意运行超时，已自动停止。可以切换 Direct 或重新启动。"
    run.finished_at = run.finished_at or datetime.now()
    session.status = "failed"
    await _record_run_event(
        db,
        run,
        "backend.timeout",
        "Hermes 创意运行超过后台等待时间，已自动停止并标记为失败",
        {"run_id": run.id, "hermes_run_id": run.hermes_run_id},
    )


def _run_timed_out(run: CreativeRun) -> bool:
    timeout = float(settings.HERMES_CREATIVE_BACKGROUND_TIMEOUT or 300.0)
    anchor = run.started_at or run.created_at
    if not anchor:
        return False
    now = datetime.now(anchor.tzinfo) if getattr(anchor, "tzinfo", None) else datetime.now()
    return (now - anchor).total_seconds() > timeout


async def get_hermes_status() -> dict[str, Any]:
    if not settings.HERMES_AGENT_ENABLED:
        if settings.AI_API_KEY:
            return {
                "enabled": True,
                "healthy": True,
                "mode": "direct_ai",
                "message": "内置创意 Agent 已启用，使用当前后台大模型配置",
                "model": settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME,
                "creative_profile": settings.HERMES_CREATIVE_PROFILE,
                "skills_dir": settings.HERMES_CREATIVE_SKILLS_DIR,
                "required_toolsets": [],
                "providers": _provider_status(hermes_healthy=False),
            }
        return {
            "enabled": False,
            "healthy": False,
            "message": "Hermes Agent 未启用",
            "creative_profile": settings.HERMES_CREATIVE_PROFILE,
            "skills_dir": settings.HERMES_CREATIVE_SKILLS_DIR,
            "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
            "providers": _provider_status(hermes_healthy=False),
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
        "model": settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME,
        "creative_profile": settings.HERMES_CREATIVE_PROFILE,
        "skills_dir": settings.HERMES_CREATIVE_SKILLS_DIR,
        "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        "providers": _provider_status(hermes_healthy=True),
    }


async def _run_direct_ai_agent(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    instructions: str,
    input_text: str,
) -> dict[str, Any]:
    run.status = "running"
    run.provider = "direct_ai"
    run.started_at = run.started_at or datetime.now()
    model_name = settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME
    output_json = dict(run.output_json or {})
    output_json["direct_ai_model"] = model_name
    run.output_json = output_json
    await _record_run_event(
        db,
        run,
        "direct_ai.started",
        "内置创意 Agent 已启动",
        {"model": model_name},
        source="backend",
    )
    await db.commit()
    await db.refresh(run)

    if run.run_type == "auto_optimize":
        return await _run_backend_auto_tool_agent(db, session=session, run=run, model_name=model_name)

    try:
        response = await post_chat_completion(
            {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": input_text},
                ],
                "temperature": 0.7,
            },
            timeout=float(settings.HERMES_HTTP_TIMEOUT or settings.AI_HTTP_TIMEOUT or 120.0),
        )
        output_text = _extract_chat_completion_text(response)
        output_json = dict(run.output_json or {})
        output_json["direct_ai_response"] = response
        output_json["raw_output"] = output_text
        run.output_json = output_json

        if not output_text:
            run.status = "failed"
            run.error = "内置创意 Agent 未返回有效内容"
            run.finished_at = datetime.now()
            session.status = "failed"
            await _record_run_event(db, run, "direct_ai.failed", run.error, {"response": response})
        else:
            await _persist_creative_output(db, session=session, run=run, output_text=output_text)
            run.finished_at = run.finished_at or datetime.now()
            if run.error:
                run.status = "failed"
                session.status = "failed"
                await _record_run_event(
                    db,
                    run,
                    "direct_ai.parse_failed",
                    run.error,
                    {"output_preview": output_text[:1000]},
                )
            else:
                run.status = "completed"
                session.status = "completed"
                await _record_run_event(
                    db,
                    run,
                    "direct_ai.completed",
                    "内置创意 Agent 已完成并保存结果",
                    {"run_id": run.id},
                )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(db, run, "direct_ai.failed", "内置创意 Agent 调用失败", {"error": run.error})
        await db.commit()
        raise

    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def _run_backend_evaluate_tool_agent(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    model_name: str,
) -> dict[str, Any]:
    input_json = run.input_json or {}
    request = input_json.get("request") or {}
    brief = input_json.get("brief") if isinstance(input_json.get("brief"), dict) else (session.brief_json or {})
    target_idea = input_json.get("target_idea") if isinstance(input_json.get("target_idea"), dict) else {}
    target_score = _to_int(request.get("target_score")) or 85
    core_target_score = normalize_core_target_score(target_score)
    event_prefix = _provider_event_prefix(run.provider)
    provider_label = _provider_label(run.provider)

    if not target_idea:
        run.status = "failed"
        run.error = f"{provider_label} evaluator tool 缺少目标创意"
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(db, run, f"{event_prefix}.failed", run.error, {})
        await db.commit()
        await db.refresh(run)
        return _serialize_run(run)

    run.status = "running"
    run.started_at = run.started_at or datetime.now()
    output_json = dict(run.output_json or {})
    output_json[f"{event_prefix}_tool_model"] = model_name
    run.output_json = output_json
    await _record_run_event(
        db,
        run,
        f"{event_prefix}.tool_flow_started",
        f"{provider_label} 单方案评估已切换为后端 evaluator tool",
        {
            "provider": run.provider,
            "model": model_name,
            "target_idea_id": input_json.get("target_idea_id"),
            "raw_target_score": target_score,
            "core_target_score": core_target_score,
        },
    )
    await db.commit()

    try:
        score_result = await score_ideas_tool(
            brief=brief,
            ideas=[target_idea],
            target_score=target_score,
            model_name=model_name,
            timeout=float(settings.HERMES_HTTP_TIMEOUT or settings.AI_HTTP_TIMEOUT or 120.0),
        )
        review_payload = _as_list(score_result.get("scores"))
        review = review_payload[0] if review_payload and isinstance(review_payload[0], dict) else {}
        review = {
            **review,
            "rubric_version": score_result.get("rubric_version") or "backend_core_v1",
        }
        await _record_run_event(
            db,
            run,
            "tool.score_ideas",
            "单方案 evaluator tool 已完成评分",
            {
                "tool_name": score_result.get("tool_name"),
                "duration_ms": score_result.get("duration_ms"),
                "target_score": score_result.get("target_score"),
                "best_score": score_result.get("best_score"),
                "target_reached": score_result.get("target_reached"),
                "compact_input": score_result.get("compact_input"),
                "scores": score_result.get("scores"),
                "compact_score_matrix": score_result.get("compact_score_matrix"),
            },
        )

        output_payload = {
            "session_summary": (
                f"{provider_label} evaluator tool 完成评分，"
                f"核心得分 {review.get('total_score') or 0}/40。"
            ),
            "react_trace": [
                {
                    "step": 1,
                    "phase": "observation",
                    "role": "backend_evaluator_tool",
                    "tool_name": "score_ideas",
                    "input_summary": f"目标创意 + 压缩 brief；目标 {core_target_score}/40",
                    "output_summary": f"得分 {review.get('total_score') or 0}/40",
                    "observation": _text_value(score_result.get("compact_score_matrix")),
                    "reflection_summary": _tool_round_focus(score_result),
                    "decision": "达到目标" if score_result.get("target_reached") else "建议继续优化",
                    "next_action": "finalize" if score_result.get("target_reached") else "iterate",
                    "score_snapshot": {
                        "total_score": review.get("total_score") or 0,
                        "target_score": core_target_score,
                    },
                    "dimension_deltas": [],
                }
            ],
            "review": review,
            "iteration_summary": [],
            "team_memory_candidates": [],
            "evaluator_tool_results": [score_result],
        }
        output_text = json.dumps(output_payload, ensure_ascii=False)
        output_json = dict(run.output_json or {})
        output_json["evaluator_tool_results"] = [score_result]
        output_json["raw_output"] = output_text
        run.output_json = output_json

        await _persist_creative_output(db, session=session, run=run, output_text=output_text)
        run.finished_at = run.finished_at or datetime.now()
        if run.error:
            run.status = "failed"
            session.status = "failed"
            await _record_run_event(db, run, f"{event_prefix}.parse_failed", run.error, {})
        else:
            run.status = "completed"
            session.status = "completed"
            await _record_run_event(
                db,
                run,
                f"{event_prefix}.completed",
                f"{provider_label} evaluator tool 评分流程已完成并保存结果",
                {
                    "best_score": score_result.get("best_score"),
                    "target_reached": score_result.get("target_reached"),
                },
            )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(
            db,
            run,
            f"{event_prefix}.failed",
            f"{provider_label} evaluator tool 调用失败",
            {"error": run.error},
        )
        await db.commit()
        raise

    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


async def _run_backend_auto_tool_agent(
    db: AsyncSession,
    *,
    session: CreativeSession,
    run: CreativeRun,
    model_name: str,
) -> dict[str, Any]:
    input_json = run.input_json or {}
    request = input_json.get("request") or {}
    brief = input_json.get("brief") if isinstance(input_json.get("brief"), dict) else (session.brief_json or {})
    designer_direction = _text_value(input_json.get("designer_direction") or session.designer_direction)
    seed_ideas = [item for item in _as_list(input_json.get("seed_ideas")) if isinstance(item, dict)]
    max_rounds = max(1, min(8, _to_int(request.get("max_rounds")) or 4))
    idea_count = max(1, min(5, _to_int(request.get("idea_count")) or 3))
    target_score = _to_int(request.get("target_score")) or 85
    core_target_score = normalize_core_target_score(target_score)
    strategy = _text_value(request.get("strategy") or "balanced")
    hard_constraints = _as_str_list(request.get("hard_constraints"))
    negative_examples = _as_str_list(request.get("negative_examples"))
    team_memory = [item for item in _as_list(input_json.get("team_memory")) if isinstance(item, dict)]
    personal_memory = [item for item in _as_list(input_json.get("personal_memory")) if isinstance(item, dict)]
    event_prefix = _provider_event_prefix(run.provider)
    provider_label = _provider_label(run.provider)

    run.status = "running"
    run.started_at = run.started_at or datetime.now()
    output_json = dict(run.output_json or {})
    output_json[f"{event_prefix}_tool_model"] = model_name
    run.output_json = output_json
    await _record_run_event(
        db,
        run,
        f"{event_prefix}.tool_flow_started",
        f"{provider_label} 自动优化已切换为后端 tool 评分流程",
        {
            "provider": run.provider,
            "model": model_name,
            "max_rounds": max_rounds,
            "idea_count": idea_count,
            "raw_target_score": target_score,
            "core_target_score": core_target_score,
        },
    )
    await db.commit()

    llm_traces: list[dict[str, Any]] = []
    evaluator_results: list[dict[str, Any]] = []
    iterations: list[dict[str, Any]] = []
    react_trace: list[dict[str, Any]] = []
    ideas: list[dict[str, Any]] = []
    previous_score_result: dict[str, Any] | None = None

    try:
        for round_index in range(1, max_rounds + 1):
            if round_index == 1:
                prompt = _build_direct_ai_generation_prompt(
                    brief=brief,
                    designer_direction=designer_direction,
                    seed_ideas=seed_ideas,
                    idea_count=idea_count,
                    strategy=strategy,
                    hard_constraints=hard_constraints,
                    negative_examples=negative_examples,
                    team_memory=team_memory,
                    personal_memory=personal_memory,
                )
                event_type = f"{event_prefix}.generate_ideas"
                event_message = f"第 {round_index} 轮：生成候选创意"
            else:
                prompt = _build_direct_ai_refine_prompt(
                    brief=brief,
                    ideas=ideas,
                    previous_score_result=previous_score_result or {},
                    designer_direction=designer_direction,
                    idea_count=idea_count,
                    strategy=strategy,
                    hard_constraints=hard_constraints,
                    team_memory=team_memory,
                    personal_memory=personal_memory,
                )
                event_type = f"{event_prefix}.refine_ideas"
                event_message = f"第 {round_index} 轮：基于 tool 评分精修创意"

            await _record_run_event(
                db,
                run,
                event_type,
                event_message,
                {"round": round_index, "prompt_chars": len(prompt["user"])},
            )
            await db.commit()

            generation_started = time.monotonic()
            response = await post_chat_completion(
                {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": prompt["system"]},
                        {"role": "user", "content": prompt["user"]},
                    ],
                    "temperature": 0.65 if round_index == 1 else 0.45,
                },
                timeout=float(settings.HERMES_HTTP_TIMEOUT or settings.AI_HTTP_TIMEOUT or 120.0),
            )
            output_text = _extract_chat_completion_text(response)
            parsed = _parse_json_output(output_text)
            ideas = _normalize_generated_ideas(parsed, fallback_ideas=ideas, idea_count=idea_count)
            if not ideas:
                run.status = "failed"
                run.error = f"{provider_label} 创意生成未返回 ideas"
                run.finished_at = datetime.now()
                session.status = "failed"
                await _record_run_event(
                    db,
                    run,
                    f"{event_prefix}.parse_failed",
                    run.error,
                    {"round": round_index, "output_preview": output_text[:1000]},
                )
                await db.commit()
                await db.refresh(run)
                return _serialize_run(run)

            generated_event_type = f"{event_prefix}.ideas_generated"
            await _record_run_event(
                db,
                run,
                generated_event_type,
                f"第 {round_index} 轮：已生成 {len(ideas)} 个候选方案",
                {
                    "round": round_index,
                    "tool_name": event_type,
                    "duration_ms": int((time.monotonic() - generation_started) * 1000),
                    "idea_count": len(ideas),
                    "idea_titles": [_text_value(item.get("title") or item.get("name")) for item in ideas],
                    "ideas": _ideas_for_event_summary(ideas),
                    "response_usage": response.get("usage") if isinstance(response, dict) else None,
                    "output_chars": len(output_text),
                    "next_action": "score_ideas",
                },
            )
            await db.commit()

            llm_traces.append({
                "round": round_index,
                "tool_name": event_type,
                "response_usage": response.get("usage") if isinstance(response, dict) else None,
                "output_chars": len(output_text),
                "idea_titles": [_text_value(item.get("title") or item.get("name")) for item in ideas],
            })
            react_trace.append({
                "step": len(react_trace) + 1,
                "phase": "action",
                "role": "orchestrator",
                "tool_name": event_type,
                "input_summary": f"第 {round_index} 轮，输入压缩 brief、设计方向和上一轮评分",
                "output_summary": f"生成 {len(ideas)} 个候选方案",
                "observation": "创意生成阶段不打分，等待 score_ideas tool 独立评估",
                "reflection_summary": "",
                "decision": "调用 evaluator tool",
                "next_action": "score_ideas",
                "score_snapshot": {},
                "dimension_deltas": [],
            })

            score_result = await score_ideas_tool(
                brief=brief,
                ideas=ideas,
                target_score=target_score,
                model_name=model_name,
                timeout=float(settings.HERMES_HTTP_TIMEOUT or settings.AI_HTTP_TIMEOUT or 120.0),
            )
            evaluator_results.append(score_result)
            await _record_run_event(
                db,
                run,
                "tool.score_ideas",
                f"第 {round_index} 轮：evaluator tool 已完成评分",
                {
                    "round": round_index,
                    "tool_name": score_result.get("tool_name"),
                    "duration_ms": score_result.get("duration_ms"),
                    "target_score": score_result.get("target_score"),
                    "best_index": score_result.get("best_index"),
                    "best_score": score_result.get("best_score"),
                    "target_reached": score_result.get("target_reached"),
                    "compact_input": score_result.get("compact_input"),
                    "scores": score_result.get("scores"),
                    "score_summaries": _scores_for_event_summary(score_result.get("scores")),
                    "compact_score_matrix": score_result.get("compact_score_matrix"),
                    "next_action": "finalize" if score_result.get("target_reached") else f"{event_prefix}.refine_ideas",
                },
            )
            await db.commit()

            previous_best = (
                _to_int(previous_score_result.get("best_score")) if isinstance(previous_score_result, dict) else None
            )
            best_score = _to_int(score_result.get("best_score")) or 0
            iteration = {
                "round": round_index,
                "action": "生成并评分" if round_index == 1 else "基于 evaluator tool 评分精修",
                "score_before": previous_best if previous_best is not None else 0,
                "score_after": best_score,
                "score_delta": _score_delta(previous_best if previous_best is not None else 0, best_score, None),
                "focus": _tool_round_focus(score_result),
                "summary": _tool_round_summary(score_result, round_index),
                "agent_explanation": "本轮只把评分交给 score_ideas tool，主流程根据 tool 的结构化分数决定是否继续精修。",
                "dimension_deltas": _dimension_deltas_between_score_results(previous_score_result, score_result),
            }
            iterations.append(iteration)
            react_trace.append({
                "step": len(react_trace) + 1,
                "phase": "observation",
                "role": "backend_evaluator_tool",
                "tool_name": "score_ideas",
                "input_summary": f"{len(ideas)} 个方案 + 压缩 brief；目标 {core_target_score}/{40}",
                "output_summary": f"最佳方案 {score_result.get('best_index')}，得分 {best_score}/{40}",
                "observation": _text_value(score_result.get("compact_score_matrix")),
                "reflection_summary": _tool_round_focus(score_result),
                "decision": "达到目标，停止迭代" if score_result.get("target_reached") else "未达到目标，继续精修",
                "next_action": "finalize" if score_result.get("target_reached") else f"{event_prefix}.refine_ideas",
                "score_snapshot": {
                    "total_score": best_score,
                    "best_index": score_result.get("best_index"),
                    "target_score": core_target_score,
                },
                "dimension_deltas": iteration["dimension_deltas"],
            })

            previous_score_result = score_result
            if score_result.get("target_reached"):
                break

        if not previous_score_result:
            run.status = "failed"
            run.error = f"{provider_label} tool 流程未产生评分结果"
            run.finished_at = datetime.now()
            session.status = "failed"
            await db.commit()
            await db.refresh(run)
            return _serialize_run(run)

        final_ideas = _attach_tool_reviews_to_ideas(ideas, previous_score_result)
        final_payload = {
            "session_summary": _final_tool_session_summary(
                previous_score_result,
                len(evaluator_results),
                core_target_score,
                provider_label=provider_label,
            ),
            "react_trace": react_trace,
            "selected_idea_index": previous_score_result.get("best_index", 0),
            "iteration_summary": iterations,
            "ideas": final_ideas,
            "team_memory_candidates": [],
            "evaluator_tool_results": evaluator_results,
            f"{event_prefix}_tool_trace": llm_traces,
        }
        output_text = json.dumps(final_payload, ensure_ascii=False)
        output_json = dict(run.output_json or {})
        output_json[f"{event_prefix}_tool_trace"] = llm_traces
        output_json["evaluator_tool_results"] = evaluator_results
        output_json["raw_output"] = output_text
        run.output_json = output_json

        await _persist_creative_output(db, session=session, run=run, output_text=output_text)
        run.finished_at = run.finished_at or datetime.now()
        if run.error:
            run.status = "failed"
            session.status = "failed"
            await _record_run_event(db, run, f"{event_prefix}.parse_failed", run.error, {})
        else:
            run.status = "completed"
            session.status = "completed"
            await _record_run_event(
                db,
                run,
                f"{event_prefix}.completed",
                f"{provider_label} tool 评分流程已完成并保存结果",
                {
                    "rounds": len(evaluator_results),
                    "best_score": previous_score_result.get("best_score"),
                    "target_reached": previous_score_result.get("target_reached"),
                },
            )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.finished_at = datetime.now()
        session.status = "failed"
        await _record_run_event(
            db,
            run,
            f"{event_prefix}.failed",
            f"{provider_label} tool 流程调用失败",
            {"error": run.error},
        )
        await db.commit()
        raise

    await db.commit()
    await db.refresh(run)
    return _serialize_run(run)


def _build_direct_ai_generation_prompt(
    *,
    brief: dict[str, Any],
    designer_direction: str,
    seed_ideas: list[dict[str, Any]],
    idea_count: int,
    strategy: str,
    hard_constraints: list[str],
    negative_examples: list[str],
    team_memory: list[dict[str, Any]],
    personal_memory: list[dict[str, Any]],
) -> dict[str, str]:
    compact_brief = compact_brief_for_evaluator(brief)
    payload = {
        "task": "生成裸眼3D商业创意方案，不要评分",
        "idea_count": idea_count,
        "strategy": strategy,
        "skill_guidance": _skill_guidance_for_prompt([
            "creative-concept-generator",
            "naked-eye-3d-scriptwriter",
        ]),
        "brief": compact_brief,
        "designer_direction": designer_direction,
        "seed_ideas": [compact_idea_for_evaluator(item, index) for index, item in enumerate(seed_ideas[:5])],
        "hard_constraints": hard_constraints,
        "negative_examples": negative_examples,
        "agent_memory": {
            "team": _compact_memory_for_prompt(team_memory),
            "personal": _compact_memory_for_prompt(personal_memory, limit=5),
        },
        "output_schema": _direct_ai_ideas_schema(idea_count),
    }
    return {
        "system": (
            "你是 Unique Vision 的创意生成 Agent，服务裸眼3D/户外大屏商业创意。"
            "本阶段只生成方案，不做评分，不输出 review。先按 creative-concept-generator 生成不同核心机制的创意，"
            "再按 naked-eye-3d-scriptwriter 写成有连续时间范围的裸眼3D分镜脚本，允许使用0.5秒或0.1秒精度。"
            "agent_memory 是已审核启用的团队/个人经验，可作为偏好、约束和方法论参考；"
            "若与 brief 或设计师方向冲突，优先服从 brief 和设计师方向。"
            "输出必须是严格 JSON object，不要 Markdown。所有面向用户的字符串用简体中文；"
            "tags、risk_notes、summary、Memory 候选等也必须使用简体中文；"
            "方案脚本必须按连续时间范围描述具体画面，允许使用0.5秒或0.1秒精度，并说明前中后景、屏幕边缘、遮挡/透视/破框关系和品牌落点。"
        ),
        "user": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }


def _build_direct_ai_refine_prompt(
    *,
    brief: dict[str, Any],
    ideas: list[dict[str, Any]],
    previous_score_result: dict[str, Any],
    designer_direction: str,
    idea_count: int,
    strategy: str,
    hard_constraints: list[str],
    team_memory: list[dict[str, Any]],
    personal_memory: list[dict[str, Any]],
) -> dict[str, str]:
    compact_state = {
        "task": "根据 evaluator tool 的结构化评分精修方案，不要自行评分",
        "idea_count": idea_count,
        "strategy": strategy,
        "brief": compact_brief_for_evaluator(brief),
        "designer_direction": designer_direction,
        "hard_constraints": hard_constraints,
        "agent_memory": {
            "team": _compact_memory_for_prompt(team_memory),
            "personal": _compact_memory_for_prompt(personal_memory, limit=5),
        },
        "previous_ideas": [compact_idea_for_evaluator(item, index) for index, item in enumerate(ideas[:idea_count])],
        "skill_guidance": _skill_guidance_for_prompt([
            "creative-iteration-loop",
            "naked-eye-3d-scriptwriter",
        ]),
        "previous_score_result": {
            "best_index": previous_score_result.get("best_index"),
            "best_score": previous_score_result.get("best_score"),
            "target_score": previous_score_result.get("target_score"),
            "compact_score_matrix": previous_score_result.get("compact_score_matrix"),
            "scores": previous_score_result.get("scores"),
        },
        "output_schema": _direct_ai_ideas_schema(idea_count),
    }
    return {
        "system": (
            "你是 Unique Vision 的创意精修 Agent。只能根据 score_ideas tool 的问题和建议优化方案，"
            "不要新增自评分，不要输出 review。优先修复最低分维度，同时保留设计师方向。"
            "agent_memory 是已审核启用的团队/个人经验，用来校准偏好、约束和方法论；"
            "若与 brief、设计师方向或 tool 评分建议冲突，优先服从后三者。"
            "输出必须是严格 JSON object，不要 Markdown。所有面向用户的字符串、标签和风险说明都必须使用简体中文。"
        ),
        "user": json.dumps(compact_state, ensure_ascii=False, separators=(",", ":")),
    }


def _direct_ai_ideas_schema(idea_count: int) -> dict[str, Any]:
    return {
        "ideas": [
            {
                "title": f"方案名 {index + 1}",
                "core_concept": "创意概念：约45字",
                "spatial_mechanism": "灵感来源/裸眼3D机制：约45字",
                "story_outline": "方案脚本：约120-180字，必须按连续时间段写具体画面，时间点可用整数秒或小数秒，并说明空间层次和品牌落点",
                "production_notes": "风格参考：约45字",
                "risk_notes": "风险与规避",
                "tags": ["中文标签"],
            }
            for index in range(idea_count)
        ]
    }


def _ideas_for_event_summary(ideas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for index, idea in enumerate(_as_list(ideas)):
        if not isinstance(idea, dict):
            continue
        summaries.append({
            "idea_index": index,
            "title": _limit_text(idea.get("title") or idea.get("name") or f"方案 {index + 1}", 80),
            "core_concept": _limit_text(
                idea.get("core_concept") or idea.get("creative_concept") or idea.get("concept"),
                180,
            ),
            "spatial_mechanism": _limit_text(
                idea.get("spatial_mechanism") or idea.get("naked_eye_3d_mechanism"),
                180,
            ),
            "story_outline": _limit_text(idea.get("story_outline") or idea.get("script"), 260),
            "production_notes": _limit_text(idea.get("production_notes") or idea.get("style_reference"), 160),
        })
    return summaries


def _scores_for_event_summary(scores: Any) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in _as_list(scores):
        if not isinstance(item, dict):
            continue
        score_map = item.get("scores") if isinstance(item.get("scores"), dict) else {}
        summaries.append({
            "idea_index": item.get("idea_index"),
            "total_score": item.get("total_score"),
            "grade": item.get("grade"),
            "summary": _limit_text(item.get("summary"), 160),
            "goal_fit": score_map.get("goal_fit"),
            "visual_impact": score_map.get("visual_impact"),
            "naked_eye_3d_fit": score_map.get("naked_eye_3d_fit"),
            "core_issues": _as_str_list(item.get("core_issues"))[:3],
            "recommendations": _as_str_list(item.get("recommendations"))[:3],
            "risk_flags": _as_str_list(item.get("risk_flags"))[:2],
        })
    return summaries


def _normalize_generated_ideas(
    parsed: dict[str, Any],
    *,
    fallback_ideas: list[dict[str, Any]],
    idea_count: int,
) -> list[dict[str, Any]]:
    ideas_payload = _as_list(
        parsed.get("ideas")
        or parsed.get("final_ideas")
        or parsed.get("optimized_ideas")
        or parsed.get("idea_versions")
    )
    if not ideas_payload and isinstance(parsed.get("idea"), dict):
        ideas_payload = [parsed["idea"]]
    normalized = [item for item in ideas_payload if isinstance(item, dict)]
    if not normalized and fallback_ideas:
        return fallback_ideas[:idea_count]
    return normalized[:idea_count]


def _skill_guidance_for_prompt(skill_names: list[str]) -> list[dict[str, str]]:
    guidance: list[dict[str, str]] = []
    for name in skill_names:
        try:
            path = _skill_file_path(name)
            if not path.exists():
                continue
            skill = _serialize_skill_file(path, include_content=True)
            guidance.append({
                "name": name,
                "description": _limit_text(skill.get("description") or "", 300),
                "content_excerpt": _limit_text(skill.get("content") or "", 2600),
            })
        except HTTPException:
            continue
        except OSError:
            continue
    return guidance


def _attach_tool_reviews_to_ideas(ideas: list[dict[str, Any]], score_result: dict[str, Any]) -> list[dict[str, Any]]:
    score_by_index = {
        _to_int(item.get("idea_index")) or 0: item
        for item in _as_list(score_result.get("scores"))
        if isinstance(item, dict)
    }
    final_ideas: list[dict[str, Any]] = []
    for index, idea in enumerate(ideas):
        payload = dict(idea)
        review = score_by_index.get(index) or {}
        payload["review"] = {
            "rubric_version": score_result.get("rubric_version") or "backend_core_v1",
            "scores": review.get("scores") or {},
            "total_score": review.get("total_score") or 0,
            "grade": review.get("grade") or _grade(_to_int(review.get("total_score")) or 0),
            "core_issues": _as_list(review.get("core_issues")),
            "recommendations": _as_list(review.get("recommendations")),
            "risk_flags": _as_list(review.get("risk_flags")),
            "summary": _text_value(review.get("summary")),
        }
        final_ideas.append(payload)
    return final_ideas


def _tool_round_focus(score_result: dict[str, Any]) -> str:
    best_index = _to_int(score_result.get("best_index")) or 0
    scores = _as_list(score_result.get("scores"))
    best = scores[best_index] if best_index < len(scores) and isinstance(scores[best_index], dict) else {}
    recommendations = _as_str_list(best.get("recommendations")) if isinstance(best, dict) else []
    issues = _as_str_list(best.get("core_issues")) if isinstance(best, dict) else []
    if recommendations:
        return "；".join(recommendations[:2])
    if issues:
        return "；".join(issues[:2])
    return "围绕目标匹配、视觉冲击和裸眼3D适配继续提升"


def _tool_round_summary(score_result: dict[str, Any], round_index: int) -> str:
    best_score = _to_int(score_result.get("best_score")) or 0
    best_index = _to_int(score_result.get("best_index")) or 0
    status = "已达到目标" if score_result.get("target_reached") else "尚未达到目标"
    return f"第 {round_index} 轮 evaluator tool 选择方案 {best_index}，核心得分 {best_score}/40，{status}。"


def _final_tool_session_summary(
    score_result: dict[str, Any],
    rounds: int,
    target_score: int,
    *,
    provider_label: str,
) -> str:
    best_score = _to_int(score_result.get("best_score")) or 0
    best_index = _to_int(score_result.get("best_index")) or 0
    status = "达到" if score_result.get("target_reached") else "未达到"
    return f"{provider_label} tool 流程完成 {rounds} 轮，最佳方案 {best_index} 得分 {best_score}/40，{status}目标 {target_score}/40。"


def _dimension_deltas_between_score_results(
    previous_score_result: dict[str, Any] | None,
    current_score_result: dict[str, Any],
) -> list[dict[str, Any]]:
    if not previous_score_result:
        return []
    previous_best = _score_item_for_best(previous_score_result)
    current_best = _score_item_for_best(current_score_result)
    if not previous_best or not current_best:
        return []
    deltas: list[dict[str, Any]] = []
    for item in HERMES_CORE_RUBRIC:
        key = item["key"]
        before = _score_value((previous_best.get("scores") or {}).get(key))
        after = _score_value((current_best.get("scores") or {}).get(key))
        delta = _score_delta(before, after, None)
        if delta is None or delta == 0:
            continue
        deltas.append({
            "key": key,
            "name": item["name"],
            "score_before": before,
            "score_after": after,
            "delta": delta,
            "change": "",
            "why": _text_value(((current_best.get("scores") or {}).get(key) or {}).get("reason"))
            if isinstance((current_best.get("scores") or {}).get(key), dict)
            else "",
        })
    return sorted(deltas, key=lambda item: item.get("delta") or 0, reverse=True)


def _score_item_for_best(score_result: dict[str, Any]) -> dict[str, Any]:
    best_index = _to_int(score_result.get("best_index")) or 0
    for item in _as_list(score_result.get("scores")):
        if not isinstance(item, dict):
            continue
        if (_to_int(item.get("idea_index")) or 0) == best_index:
            return item
    return {}


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


async def list_skill_entries() -> list[dict[str, Any]]:
    root = _skills_root()
    if not root.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/SKILL.md")):
        if not path.is_file():
            continue
        items.append(_serialize_skill_file(path, include_content=False))
    return items


async def get_skill_entry(skill_name: str) -> dict[str, Any]:
    path = _skill_file_path(skill_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return _serialize_skill_file(path, include_content=True)


async def update_skill_entry(skill_name: str, request: CreativeSkillUpdate) -> dict[str, Any]:
    path = _skill_file_path(skill_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Skill 不存在")
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Skill 内容不能为空")
    if "```" in content and content.count("```") % 2:
        raise HTTPException(status_code=400, detail="Skill Markdown 代码块未闭合")
    path.write_text(content + "\n", encoding="utf-8")
    return _serialize_skill_file(path, include_content=True)


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
                or idea_payload.get("creative_concept")
                or idea_payload.get("创意概念")
                or idea_payload.get("concept")
                or idea_payload.get("big_idea")
            ),
            spatial_mechanism=_text_value(
                idea_payload.get("spatial_mechanism")
                or idea_payload.get("inspiration_source")
                or idea_payload.get("inspiration")
                or idea_payload.get("灵感来源")
                or idea_payload.get("naked_eye_3d_mechanism")
                or idea_payload.get("3d_mechanism")
            ),
            story_outline=_text_value(
                idea_payload.get("story_outline")
                or idea_payload.get("script")
                or idea_payload.get("方案脚本")
                or idea_payload.get("timed_script")
                or idea_payload.get("story")
            ),
            production_notes=_text_value(
                idea_payload.get("production_notes")
                or idea_payload.get("style_reference")
                or idea_payload.get("style_refs")
                or idea_payload.get("风格参考")
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
    explicit_target = request.target_idea_id or feedback.target_idea_id
    target_idea_id = explicit_target or session.selected_idea_id
    if target_idea_id:
        idea = await _get_idea_or_404(db, target_idea_id)
        if idea.session_id != session.id:
            if not explicit_target:
                target_idea_id = None
            else:
                raise HTTPException(status_code=400, detail="目标方案不属于该创意会话")
        if target_idea_id:
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
        .limit(8)
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
        "recent_iterations": [_serialize_iteration_for_history(item) for item in reversed(iterations_result.scalars().all())],
        "latest_decisions": _build_latest_decisions_for_history(list(reversed(steps_result.scalars().all()))),
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
0. 所有面向用户的输出文本必须使用简体中文，包括 JSON 字符串值、方案标题、创意概念、灵感来源、方案脚本、风格参考、打分摘要、迭代说明、风险提示、ReAct 审计摘要、Memory 候选内容和 Memory 标签。不要输出英文，除非 brief 中的品牌名、专有名词、工具名、字段名或素材原文必须保留英文。
1. 只读取本轮 brief 与记忆内容，不修改订单、客户资料或业务状态。
2. 创意目标是商业可执行的传播方案，不是纯艺术赏析。
3. 自动优化评分必须使用 backend evaluator tool：score_ideas；不要使用 delegate_task 或 core_evaluator 子代理做评分。
4. score_ideas 只评估目标匹配度、视觉冲击力、裸眼3D适配度三项，必须拿到完整 brief、当前方案和约束。
5. 如果 skills 工具可用，创意生成优先加载 creative-orchestrator、creative-concept-generator、naked-eye-3d-scriptwriter；精修阶段再加载 creative-iteration-loop。评分结果必须来自 score_ideas tool，不要把 creative-rubric-evaluator 当成评分执行器。
6. 每轮迭代必须说清楚哪些评分维度上升了、每个维度为什么上升、对应改动是什么；不能只写“整体更好”。
7. 使用 ReAct-style 审计轨迹，但只输出面向用户的摘要，不要输出隐藏思考链。每一步用 plan/action/observation/reflection/decision 描述做了什么、看到了什么、决定什么。
8. 如果设计师提供了 designer_direction 或 seed_ideas，必须优先作为创作约束；如需偏离，必须在 react_trace 的 decision 里说明原因。
9. ideas 里的每个方案必须按四段短文本输出：创意概念约15%，灵感来源约15%，方案脚本约35%，风格参考约15%；四段总字数约300字。
10. 方案脚本必须写清时间范围，但节拍可以灵活；允许 0.5 秒或 0.1 秒精度，例如“0-1.5秒...；1.5-3秒...；3-5.5秒...”，不能只写抽象叙述。
11. 输出必须是一个严格 JSON object，不要 Markdown、不要代码块、不要解释性前后缀。
"""

    designer_direction = _effective_designer_direction(session, request.designer_direction)
    seed_ideas = _effective_seed_ideas(session, request.seed_ideas)
    workflow = {
        "goal": "生成并自动迭代裸眼3D创意方案",
        "max_rounds": request.max_rounds,
        "target_score": request.target_score,
        "idea_count": request.idea_count,
        "strategy": request.strategy,
        "use_parallel_evaluators": False,
        "designer_direction": designer_direction,
        "seed_ideas": seed_ideas,
        "hard_constraints": request.hard_constraints,
        "negative_examples": request.negative_examples,
        "recommended_skills": [
            "creative-orchestrator",
            "creative-concept-generator",
            "naked-eye-3d-scriptwriter",
            "creative-iteration-loop",
        ],
        "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        "evaluator_tool_hint": {
            "name": "score_ideas",
            "goal": "只评估3项核心指标：目标匹配度、视觉冲击力、裸眼3D适配度；逐项给score、max和简短扣分理由。不要评估合规、成本、制作周期、品牌安全或传播风险。",
            "owner": "backend",
        },
        "execute_code_hint": "用 Python 汇总3项核心维度得分、计算总分、判断是否达到 target_score，并选择最佳版本。",
    }
    expected_output = {
        "session_summary": "一句话说明本轮创意方向与迭代结果",
        "react_trace": [
            {
                "step": 1,
                "phase": "plan/action/observation/reflection/decision",
                "role": "orchestrator/backend_evaluator_tool",
                "tool_name": "score_ideas/execute_code/skill name",
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
                "core_concept": "创意概念：约45字，占方案约15%",
                "spatial_mechanism": "灵感来源：约45字，占方案约15%",
                "story_outline": "方案脚本：约105字，占方案约35%，必须按连续时间段写具体画面，时间点可用整数秒或小数秒，例如0-1.5秒、1.5-3秒、3-5.5秒",
                "production_notes": "风格参考：约45字，占方案约15%，写视觉风格、参考气质或镜头语言",
                "risk_notes": "风险与规避",
                "tags": ["标签"],
                "review": {
                    "rubric_version": "hermes_core_v1",
                    "scores": {
                        "goal_fit": {"score": 0, "max": 10, "reason": ""},
                        "visual_impact": {"score": 0, "max": 15, "reason": ""},
                        "naked_eye_3d_fit": {"score": 0, "max": 15, "reason": ""},
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
        "team_memory_candidates": ["值得沉淀为团队方法论的中文经验，内容和标签必须使用简体中文"],
    }

    input_payload = {
        "workflow": workflow,
        "language_policy": {
            "output_language": "简体中文",
            "strict": True,
            "allow_english_only_for": ["品牌英文名", "专有名词", "素材原文"],
            "memory_policy": "team_memory_candidates 的内容和标签必须使用简体中文",
        },
        "rubric": HERMES_CORE_RUBRIC,
        "brief": _compact_brief_for_prompt(session.brief_json or {}),
        "designer_direction": designer_direction,
        "seed_ideas": _compact_ideas_for_prompt(seed_ideas, limit=3),
        "reference_cases": _compact_reference_cases_for_prompt(request.reference_cases),
        "team_memory": _compact_memory_for_prompt(team_memory),
        "personal_memory": _compact_memory_for_prompt(personal_memory, limit=5),
        "idea_output_format": {
            "total_length_cn": "约300字",
            "sections": [
                {"field": "core_concept", "label": "创意概念", "ratio": "15%"},
                {"field": "spatial_mechanism", "label": "灵感来源", "ratio": "15%"},
                {"field": "story_outline", "label": "方案脚本", "ratio": "35%", "requirement": "按连续时间段写具体画面，可使用0.5秒或0.1秒精度"},
                {"field": "production_notes", "label": "风格参考", "ratio": "15%"},
            ],
        },
        "output_schema": expected_output,
    }
    return instructions, json.dumps(input_payload, ensure_ascii=False, separators=(",", ":"))


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
0. 所有面向用户的输出文本必须使用简体中文，包括 JSON 字符串值、方案标题、打分摘要、评分理由、迭代说明、风险提示、ReAct 审计摘要、Memory 候选内容和 Memory 标签。不要输出英文，除非 brief 中的品牌名、专有名词、工具名、字段名或素材原文必须保留英文。
1. 只处理输入中的目标创意，不修改订单或业务状态。
2. 评估时只使用轻量核心评分标准；迭代时可使用 creative-iteration-loop，但不要展开额外生产、合规或传播风险评估。
3. 评分必须使用 backend evaluator tool：score_ideas；不要使用 delegate_task 或 core_evaluator 子代理做评分。
4. 如果 execute_code 可用，用 Python 汇总 score_ideas 的3项核心评分并判断是否达到 target_score。
5. 迭代输出必须说明哪些维度分数上升、为什么上升、对应改动是什么，供前端直接展示。
6. 输出 ReAct-style 审计轨迹，但只写面向用户的摘要，不输出隐藏思考链。
7. 如果设计师方向和评分建议冲突，优先保留设计师方向的核心意图，并说明取舍。
8. 若输出优化后的 ideas，每个方案必须按四段短文本输出：创意概念约15%，灵感来源约15%，方案脚本约35%，风格参考约15%；四段总字数约300字。
9. 方案脚本必须写清时间范围，但节拍可以灵活；允许 0.5 秒或 0.1 秒精度，例如“0-1.5秒...；1.5-3秒...；3-5.5秒...”，不能只写抽象叙述。
10. 输出必须是严格 JSON object，不要 Markdown、不要代码块。
"""
    target_idea = _compact_idea_for_prompt(_serialize_idea(idea, []))
    designer_direction = _effective_designer_direction(session, request.designer_direction)
    output_schema: dict[str, Any]
    if run_type == "evaluate":
        output_schema = {
            "session_summary": "一句话综合判断",
            "react_trace": [
                {
                    "step": 1,
                    "phase": "plan/action/observation/reflection/decision",
                    "role": "backend_evaluator_tool",
                    "tool_name": "score_ideas",
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
                "rubric_version": "hermes_core_v1",
                "scores": {
                    item["key"]: {"score": 0, "max": item["max"], "reason": ""}
                    for item in HERMES_CORE_RUBRIC
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
                    "core_concept": "创意概念：约45字，占方案约15%",
                    "spatial_mechanism": "灵感来源：约45字，占方案约15%",
                    "story_outline": "方案脚本：约105字，占方案约35%，必须按连续时间段写具体画面，时间点可用整数秒或小数秒，例如0-1.5秒、1.5-3秒、3-5.5秒",
                    "production_notes": "风格参考：约45字，占方案约15%，写视觉风格、参考气质或镜头语言",
                    "risk_notes": "风险与规避",
                    "tags": ["标签"],
                    "review": {
                        "rubric_version": "hermes_core_v1",
                        "scores": {
                            item["key"]: {"score": 0, "max": item["max"], "reason": ""}
                            for item in HERMES_CORE_RUBRIC
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
            "use_parallel_evaluators": False,
            "recommended_skills": [
                "creative-iteration-loop",
            ],
            "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        },
        "language_policy": {
            "output_language": "简体中文",
            "strict": True,
            "allow_english_only_for": ["品牌英文名", "专有名词", "素材原文"],
            "memory_policy": "team_memory_candidates 的内容和标签必须使用简体中文",
        },
        "rubric": HERMES_CORE_RUBRIC,
        "brief": _compact_brief_for_prompt(session.brief_json or {}),
        "designer_direction": designer_direction,
        "seed_ideas": _compact_ideas_for_prompt(session.seed_ideas or [], limit=3),
        "target_idea": target_idea,
        "team_memory": _compact_memory_for_prompt(team_memory),
        "personal_memory": _compact_memory_for_prompt(personal_memory, limit=5),
        "idea_output_format": {
            "total_length_cn": "约300字",
            "sections": [
                {"field": "core_concept", "label": "创意概念", "ratio": "15%"},
                {"field": "spatial_mechanism", "label": "灵感来源", "ratio": "15%"},
                {"field": "story_outline", "label": "方案脚本", "ratio": "35%", "requirement": "按连续时间段写具体画面，可使用0.5秒或0.1秒精度"},
                {"field": "production_notes", "label": "风格参考", "ratio": "15%"},
            ],
        },
        "output_schema": output_schema,
    }
    return instructions, json.dumps(input_payload, ensure_ascii=False, separators=(",", ":"))


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
0. 所有面向用户的输出文本必须使用简体中文，包括 JSON 字符串值、方案标题、反馈吸收说明、方案脚本、打分摘要、迭代说明、风险提示、ReAct 审计摘要、Memory 候选内容和 Memory 标签。不要输出英文，除非 brief 中的品牌名、专有名词、工具名、字段名或素材原文必须保留英文。
1. 这是人类介入后的继续迭代，不是从零重写。必须继承目标方案、历史评估、历史迭代和设计师反馈。
2. 先判断设计师反馈属于：保留、删除、强化、转向、降成本、降风险、换风格、补细节。
3. 如果设计师反馈与评分建议冲突，优先说明取舍；不能直接忽略设计师反馈。
4. 输出 ReAct-style 审计轨迹，但只写面向用户的摘要，不输出隐藏思考链。
5. 每轮迭代必须说明哪些维度分数上升、为什么上升、对应改动是什么。
6. 输出的继续迭代方案必须按四段短文本输出：创意概念约15%，灵感来源约15%，方案脚本约35%，风格参考约15%；四段总字数约300字。
7. 方案脚本必须写清时间范围，但节拍可以灵活；允许 0.5 秒或 0.1 秒精度，例如“0-1.5秒...；1.5-3秒...；3-5.5秒...”，不能只写抽象叙述。
8. 输出严格 JSON object，不要 Markdown、不要代码块。
"""
    target = _compact_idea_for_prompt(_serialize_idea(target_idea, []))
    feedback_payload = _compact_feedback_for_prompt(_serialize_feedback(feedback))
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
                        "key": "visual_impact",
                        "name": "视觉冲击力",
                        "score_before": 9,
                        "score_after": 12,
                        "delta": 3,
                        "change": "把视觉峰值前置，并增加更清晰的主体动作",
                        "why": "设计师要求更有冲击力，因此强化第一眼识别和现场停留动机",
                    }
                ],
                "key_improvements": [],
            }
        ],
        "ideas": [
            {
                "title": "继续迭代后的方案名",
                "core_concept": "创意概念：约45字，占方案约15%",
                "spatial_mechanism": "灵感来源：约45字，占方案约15%",
                "story_outline": "方案脚本：约105字，占方案约35%，必须按连续时间段写具体画面，时间点可用整数秒或小数秒，例如0-1.5秒、1.5-3秒、3-5.5秒",
                "production_notes": "风格参考：约45字，占方案约15%，写视觉风格、参考气质或镜头语言",
                "risk_notes": "风险与规避",
                "tags": ["标签"],
                "review": {
                    "rubric_version": "hermes_core_v1",
                    "scores": {
                        item["key"]: {"score": 0, "max": item["max"], "reason": ""}
                        for item in HERMES_CORE_RUBRIC
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
            "use_parallel_evaluators": False,
            "recommended_skills": [
                "creative-iteration-loop",
            ],
            "required_toolsets": _split_csv(settings.HERMES_CREATIVE_REQUIRED_TOOLSETS),
        },
        "language_policy": {
            "output_language": "简体中文",
            "strict": True,
            "allow_english_only_for": ["品牌英文名", "专有名词", "素材原文"],
            "memory_policy": "team_memory_candidates 的内容和标签必须使用简体中文",
        },
        "rubric": HERMES_CORE_RUBRIC,
        "brief": _compact_brief_for_prompt(session.brief_json or {}),
        "designer_direction": _limit_text(session.designer_direction or "", 500),
        "seed_ideas": _compact_ideas_for_prompt(session.seed_ideas or [], limit=3),
        "target_idea": target,
        "designer_feedback": feedback_payload,
        "history": _compact_continue_history_for_prompt(history),
        "team_memory": _compact_memory_for_prompt(team_memory),
        "personal_memory": _compact_memory_for_prompt(personal_memory, limit=5),
        "idea_output_format": {
            "total_length_cn": "约300字",
            "sections": [
                {"field": "core_concept", "label": "创意概念", "ratio": "15%"},
                {"field": "spatial_mechanism", "label": "灵感来源", "ratio": "15%"},
                {"field": "story_outline", "label": "方案脚本", "ratio": "35%", "requirement": "按连续时间段写具体画面，可使用0.5秒或0.1秒精度"},
                {"field": "production_notes", "label": "风格参考", "ratio": "15%"},
            ],
        },
        "output_schema": output_schema,
    }
    return instructions, json.dumps(input_payload, ensure_ascii=False, separators=(",", ":"))


def _compact_brief_for_prompt(brief: dict[str, Any]) -> dict[str, Any]:
    compact = compact_brief_for_evaluator(brief)
    fallback_keys = [
        "project_name",
        "campaign_name",
        "brand",
        "brand_or_customer",
        "objective",
        "target_goal",
        "theme_concept",
        "content",
        "media_location",
        "city_location",
        "screen_resource_summary",
        "media_specs",
        "art_direction",
        "style",
        "constraints",
        "special_notes",
    ]
    for key in fallback_keys:
        value = (brief or {}).get(key)
        if key not in compact and value not in ("", None, [], {}):
            compact[key] = _compact_prompt_value(value, max_text=500)
    return _compact_prompt_value(compact, max_text=600, max_list=8, max_dict=24)


def _compact_ideas_for_prompt(ideas: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    return [
        _compact_idea_for_prompt(item)
        for item in _as_list(ideas)[:limit]
        if isinstance(item, dict)
    ]


def _compact_idea_for_prompt(idea: dict[str, Any]) -> dict[str, Any]:
    compact = compact_idea_for_evaluator(idea)
    for key in ("id", "version", "score", "status", "parent_id"):
        value = idea.get(key)
        if value not in ("", None, [], {}):
            compact[key] = value
    reviews = _as_list(idea.get("reviews"))
    if reviews and isinstance(reviews[0], dict):
        compact["latest_review"] = _compact_review_for_prompt(reviews[0])
    return _compact_prompt_value(compact, max_text=700, max_list=6, max_dict=18)


def _compact_review_for_prompt(review: dict[str, Any]) -> dict[str, Any]:
    return _compact_prompt_value(
        {
            "total_score": review.get("total_score"),
            "grade": review.get("grade"),
            "scores": review.get("scores"),
            "core_issues": review.get("core_issues"),
            "recommendations": review.get("recommendations"),
            "summary": review.get("summary"),
        },
        max_text=260,
        max_list=4,
        max_dict=8,
    )


def _compact_feedback_for_prompt(feedback: dict[str, Any]) -> dict[str, Any]:
    return _compact_prompt_value(
        {
            "target_idea_id": feedback.get("target_idea_id"),
            "feedback_text": feedback.get("feedback_text"),
            "priority": feedback.get("priority"),
            "constraints": feedback.get("constraints"),
            "liked_parts": feedback.get("liked_parts"),
            "disliked_parts": feedback.get("disliked_parts"),
            "requested_changes": feedback.get("requested_changes"),
        },
        max_text=450,
        max_list=5,
        max_dict=10,
    )


def _compact_continue_history_for_prompt(history: dict[str, Any]) -> dict[str, Any]:
    iterations = []
    for item in _as_list(history.get("recent_iterations"))[-4:]:
        if not isinstance(item, dict):
            continue
        iterations.append(_compact_prompt_value(
            {
                "round_index": item.get("round_index"),
                "score_before": item.get("score_before"),
                "score_after": item.get("score_after"),
                "focus": item.get("focus"),
                "summary": item.get("summary"),
                "agent_explanation": item.get("agent_explanation"),
                "key_improvements": item.get("key_improvements"),
            },
            max_text=260,
            max_list=4,
            max_dict=10,
        ))

    latest_decisions = [
        _limit_text(item, 260)
        for item in _as_str_list(history.get("latest_decisions"))[-5:]
    ]

    reviews = [
        _compact_review_for_prompt(item)
        for item in _as_list(history.get("target_idea_reviews"))[:2]
        if isinstance(item, dict)
    ]
    feedbacks = [
        _compact_feedback_for_prompt(item)
        for item in _as_list(history.get("recent_designer_feedbacks"))[:3]
        if isinstance(item, dict)
    ]
    return {
        "recent_iterations": iterations,
        "latest_decisions": latest_decisions,
        "target_idea_reviews": reviews,
        "recent_designer_feedbacks": feedbacks,
    }


def _compact_memory_for_prompt(memory: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in _as_list(memory)[:limit]:
        if not isinstance(item, dict):
            continue
        compact.append(_compact_prompt_value(
            {
                "kind": item.get("kind"),
                "content": item.get("content"),
                "tags": item.get("tags"),
            },
            max_text=260,
            max_list=4,
            max_dict=6,
        ))
    return compact


def _compact_reference_cases_for_prompt(cases: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in _as_list(cases)[:limit]:
        if not isinstance(item, dict):
            continue
        compact.append(_compact_prompt_value(item, max_text=360, max_list=4, max_dict=10))
    return compact


def _serialize_iteration_for_history(iteration: CreativeIteration) -> dict[str, Any]:
    return {
        "id": iteration.id,
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
        "created_at": _iso(iteration.created_at),
    }


def _build_latest_decisions_for_history(steps: list[CreativeAgentStep], *, limit: int = 5) -> list[str]:
    decisions: list[str] = []
    for step in steps[-limit:]:
        summary = (
            _text_value(step.decision)
            or _text_value(step.output_summary)
            or _text_value(step.observation)
            or _text_value(step.reflection_summary)
        )
        if not summary:
            continue
        prefix = " / ".join(item for item in [step.role, step.tool_name, step.phase] if item)
        score = ""
        if isinstance(step.score_snapshot, dict):
            total = step.score_snapshot.get("total_score")
            if total not in ("", None):
                score = f"；score={total}"
        decisions.append(_limit_text(f"{prefix}: {summary}{score}" if prefix else f"{summary}{score}", 320))
    return decisions


def _compact_prompt_value(
    value: Any,
    *,
    max_text: int = 500,
    max_list: int = 8,
    max_dict: int = 20,
) -> Any:
    if isinstance(value, str):
        return _limit_text(value, max_text)
    if isinstance(value, list):
        compact_items = [
            _compact_prompt_value(item, max_text=max_text, max_list=max_list, max_dict=max_dict)
            for item in value[:max_list]
        ]
        return [item for item in compact_items if item not in ("", None, [], {})]
    if isinstance(value, dict):
        compact_dict: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_dict:
                break
            compact_item = _compact_prompt_value(item, max_text=max_text, max_list=max_list, max_dict=max_dict)
            if compact_item not in ("", None, [], {}):
                compact_dict[str(key)] = compact_item
        return compact_dict
    return value


def _limit_text(value: Any, max_chars: int) -> str:
    text = _text_value(value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}..."


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
    excluded_keys = {
        "technology",
        "tech_delivery",
        "techDelivery",
        "budget",
        "budget_range",
        "budgetRange",
        "online_time",
        "onlineTime",
        "deadline",
        "timeline",
        "delivery_time",
        "deliveryTime",
    }
    creative_order_data = {key: value for key, value in order_data.items() if key not in excluded_keys}
    return {
        **creative_order_data,
        "source": "order",
        "source_order_id": order.id,
        "order_number": order.order_number,
        "order_type": order_type,
        "order_status": status,
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


def _skills_root() -> Path:
    configured = Path(settings.HERMES_CREATIVE_SKILLS_DIR or "./hermes_skills")
    candidates = [configured] if configured.is_absolute() else [
        Path.cwd() / configured,
        Path(__file__).resolve().parents[3] / configured,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def _skill_file_path(skill_name: str) -> Path:
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$", skill_name or ""):
        raise HTTPException(status_code=400, detail="Skill 名称不合法")
    root = _skills_root()
    path = (root / skill_name / "SKILL.md").resolve()
    if root not in path.parents:
        raise HTTPException(status_code=400, detail="Skill 路径不合法")
    return path


def _serialize_skill_file(path: Path, *, include_content: bool) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    title = ""
    description = ""
    in_frontmatter = lines[:1] == ["---"]
    for line in lines[1:] if in_frontmatter else []:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip().strip("\"'")
            break
    if not description:
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.strip() and not line.startswith("#") and not line.startswith("---"):
                description = line.strip()
                break
    stat = path.stat()
    payload = {
        "name": path.parent.name,
        "title": title or path.parent.name,
        "description": description[:300],
        "path": str(path),
        "updated_at": _iso(datetime.fromtimestamp(stat.st_mtime)),
    }
    if include_content:
        payload["content"] = content
    return payload


def _parse_json_output(output_text: str) -> dict[str, Any]:
    text = (output_text or "").strip()
    if not text:
        return {}
    value = _try_parse_json_value(text)
    if value is not None:
        return value if isinstance(value, dict) else {"items": value}

    fences = re.finditer(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    for fence in fences:
        value = _try_parse_json_value(fence.group(1).strip())
        if value is not None:
            return value if isinstance(value, dict) else {"items": value}

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        value = _try_parse_json_value(text[start : end + 1])
        if value is not None:
            return value if isinstance(value, dict) else {"items": value}
    if start >= 0:
        value = _try_parse_json_value(text[start:])
        if value is not None:
            return value if isinstance(value, dict) else {"items": value}
    return {}


def _try_parse_json_value(text: str) -> Any:
    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(candidate)
        if not repaired or repaired == candidate:
            return None
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None


def _repair_truncated_json(text: str) -> str:
    """Append only missing closing braces/brackets for otherwise valid JSON.

    Hermes occasionally returns a complete object body while dropping the final
    root closing brace. This helper avoids content guessing: it refuses strings
    that end inside a quoted value or contain mismatched closers.
    """
    stack: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in ("}", "]"):
            if not stack or stack.pop() != char:
                return text

    if in_string or not stack or len(stack) > 8:
        return text
    return text + "".join(reversed(stack))


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


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = [
                    _text_value(item.get("text") or item.get("content"))
                    for item in content
                    if isinstance(item, dict)
                ]
                return "\n".join(item for item in parts if item).strip()
        text = choices[0].get("text")
        if text:
            return _text_value(text)
    return ""


def _extract_hermes_error(payload: dict[str, Any]) -> str:
    error = payload.get("error") or payload.get("last_error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("detail") or error)
    return str(error or "Hermes Agent 运行失败")


def _agent_provider(requested_provider: str | None = None) -> str:
    provider = requested_provider or ("hermes" if settings.HERMES_AGENT_ENABLED else "direct_ai")
    if provider == "direct_ai":
        if not settings.AI_API_KEY:
            raise HTTPException(status_code=503, detail="Direct 大模型未配置")
        return "direct_ai"
    if provider != "hermes":
        raise HTTPException(status_code=400, detail="不支持的创意 Agent 后端")
    if not settings.HERMES_AGENT_ENABLED:
        raise HTTPException(status_code=503, detail="Hermes Agent 未启用，可切换到 Direct")
    return "hermes"


def _uses_backend_evaluator_tool(run: CreativeRun) -> bool:
    return run.run_type in {"auto_optimize", "evaluate"} and run.provider in {"direct_ai", "hermes"}


def _tool_flow_model_name(provider: str | None) -> str:
    if provider == "hermes":
        return settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME
    return settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME


def _provider_event_prefix(provider: str | None) -> str:
    return "hermes" if provider == "hermes" else "direct_ai"


def _provider_label(provider: str | None) -> str:
    return "Hermes" if provider == "hermes" else "Direct"


def _queued_message(provider: str, run_label: str) -> str:
    if provider == "direct_ai":
        return f"已创建{run_label}，准备使用 Direct 后端执行"
    if run_label == "创意自动优化运行":
        return f"已创建{run_label}，准备使用 Hermes + backend evaluator tool 执行"
    return f"已创建{run_label}，准备提交 Hermes"


def _provider_status(*, hermes_healthy: bool) -> list[dict[str, Any]]:
    hermes_available = bool(settings.HERMES_AGENT_ENABLED and hermes_healthy)
    return [
        {
            "value": "hermes",
            "label": "Hermes",
            "available": hermes_available,
            "default": hermes_available,
            "model": settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME,
        },
        {
            "value": "direct_ai",
            "label": "Direct",
            "available": bool(settings.AI_API_KEY),
            "default": not hermes_available,
            "model": settings.HERMES_CREATIVE_MODEL or settings.AI_MODEL_NAME,
        },
    ]


def _normalize_run_status(status: str) -> str:
    value = (status or "").lower()
    if value in {"completed", "failed", "cancelled", "stopped"}:
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
