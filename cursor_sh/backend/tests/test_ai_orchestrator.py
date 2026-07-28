import json

import pytest

from app.api import ai as ai_module
from app.services.ai_orchestrator import (
    OrchestratorContext,
    advance_creative_direction_iteration,
    build_router_messages,
    decide_route,
)


class _FakeUser:
    id = "user-test"
    username = "测试用户"


@pytest.mark.asyncio
async def test_router_payload_contains_state_without_agent_prompts():
    context = OrchestratorContext(
        session_id="session-test",
        message="预算大概30万，月底上线",
        history=[
            {"role": "user", "content": "我们想做杭州商场裸眼3D"},
            {"role": "assistant", "content": "这次主要想做什么内容？"},
        ],
        current_agent="brief_agent",
        stage="brief_building",
        business_type="ai_3d_custom",
        memory_context="RAW_MEMORY_CONTEXT_SHOULD_NOT_ENTER_ROUTER：杭州巨屏",
        brief_state={
            "fields": {
                "theme_concept": {"value": "巨型猫从 L 型转角屏探出"},
                "city_location": {"value": "成都核心商圈"},
            },
            "readiness": {"level": "provisional"},
        },
    )

    messages = build_router_messages(context)
    payload_text = "\n".join(m["content"] for m in messages)

    assert "brief_agent" in payload_text
    assert "brief_building" in payload_text
    assert "杭州商场裸眼3D" in payload_text
    assert "预算大概30万" in payload_text
    assert "巨型猫从 L 型转角屏探出" in payload_text
    assert "provisional" in payload_text
    assert "RAW_MEMORY_CONTEXT_SHOULD_NOT_ENTER_ROUTER" not in payload_text
    assert "系统提示词" not in payload_text
    assert "完整业务 Prompt" not in payload_text


def test_initial_router_payload_preserves_unselected_agent_state():
    context = OrchestratorContext(
        session_id="session-initial",
        message="我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
        history=[],
        current_agent=None,
        stage="intent_routing",
        business_type="ai_3d_custom",
    )

    messages = build_router_messages(context)
    payload_text = messages[1]["content"]

    assert '"current_agent": null' in payload_text
    assert '"stage": "intent_routing"' in payload_text
    assert "首次路由" in payload_text
    assert "基于图片可以从哪些方向展开" in payload_text


def test_router_payload_exposes_immediately_preceding_assistant_message():
    context = OrchestratorContext(
        session_id="session-adjacent-turn",
        message="没有",
        history=[
            {"role": "assistant", "content": "还有其他现场照片吗？"},
            {"role": "user", "content": "没有"},
            {"role": "assistant", "content": "项目制作预算大概在什么范围？"},
        ],
        current_agent="brief_agent",
        stage="brief_building",
        business_type="ai_3d_custom",
    )

    messages = build_router_messages(context)
    payload = json.loads(messages[1]["content"])

    assert payload["immediate_context"] == {
        "last_assistant_message": "项目制作预算大概在什么范围？"
    }
    assert payload["recent_history"] == [
        {"role": "assistant", "content": "还有其他现场照片吗？"},
        {"role": "user", "content": "没有"},
    ]


def test_router_preserves_full_current_turn_and_long_assistant_context():
    long_reply = (
        "阶段性创意评估。" + ("这是成立点、风险点和优化方向的详细分析。" * 120)
        + "最后想确认一下：醒狮风格偏向传统写实，还是现代卡通？"
    )
    context = OrchestratorContext(
        session_id="session-long-adjacent-turn",
        message="偏向于卡通",
        history=[
            {"role": "assistant", "content": long_reply},
        ],
        current_agent="creative_diagnosis_agent",
        stage="creative_diagnosis",
        business_type="ai_3d_custom",
        pending_evaluation={"status": "awaiting_feedback"},
    )

    messages = build_router_messages(context)
    payload = json.loads(messages[1]["content"])

    assert payload["current_user_message"] == "偏向于卡通"
    assert payload["recent_history"] == []
    assert payload["immediate_context"]["last_assistant_message"] == long_reply
    assert "中间内容已压缩" not in payload["immediate_context"]["last_assistant_message"]


def test_router_uses_prepared_history_without_secondary_compaction():
    older_message = "较早消息开头。……（中间内容已压缩）……较早消息末尾的重要结论。"
    latest_user_message = "广州醒狮非遗"
    latest_assistant_message = (
        "阶段性创意评估。" + ("详细分析。" * 200) + "偏传统写实还是现代卡通？"
    )
    context = OrchestratorContext(
        session_id="session-history-preservation",
        message="偏向于卡通",
        history=[
            {"role": "user", "content": older_message},
            {"role": "user", "content": latest_user_message},
            {"role": "assistant", "content": latest_assistant_message},
        ],
        current_agent="creative_diagnosis_agent",
        stage="creative_diagnosis",
        business_type="ai_3d_custom",
        pending_evaluation={"status": "awaiting_feedback"},
    )

    messages = build_router_messages(context)
    payload = json.loads(messages[1]["content"])

    assert payload["recent_history"] == [
        {"role": "user", "content": older_message},
        {"role": "user", "content": latest_user_message},
    ]
    assert payload["immediate_context"]["last_assistant_message"] == latest_assistant_message


@pytest.mark.asyncio
async def test_initial_creative_exploration_selects_creative_direction_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        assert '"current_agent": null' in payload["messages"][1]["content"]
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent",'
                            '"reason":"用户明确要求基于图片探索创意延展方向"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-initial-creative",
            message="我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
            history=[],
            current_agent=None,
            stage="intent_routing",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.intent == "creative_direction"
    assert route.target_agent == "creative_direction_agent"
    assert route.stage == "creative_direction"


@pytest.mark.asyncio
async def test_router_payload_declares_brief_to_order_goal():
    context = OrchestratorContext(
        session_id="session-test",
        message="帮我看看这个创意适不适合裸眼3D",
        history=[],
        current_agent="brief_agent",
        stage="brief_building",
        business_type="ai_3d_custom",
    )

    messages = build_router_messages(context)
    payload_text = "\n".join(m["content"] for m in messages)

    assert "Brief" in payload_text
    assert "control_action" in payload_text
    assert "ready_to_extract" not in payload_text
    assert "finish_brief_now" in payload_text
    assert "handoff_requested" in payload_text
    assert "表单" in payload_text
    assert "第 5 轮起状态变为 exit_recommended" in payload_text
    assert "readiness" in payload_text
    assert "不代表可以提取表单" in payload_text
    assert "immediate_context.last_assistant_message 里的实际提问" in payload_text
    assert "回答其他字段时的相同短句不能触发整理" in payload_text
    assert "immediate_context.last_assistant_message" in payload_text
    assert "不能覆盖这一邻接关系" in payload_text


def test_router_keeps_completed_creative_diagnosis_for_next_turn_routing():
    context = OrchestratorContext(
        session_id="session-diagnosis-followup",
        message="为什么你更推荐方向一？",
        history=[
            {"role": "assistant", "content": "阶段性创意评估：方向一的前三秒钩子更强。"},
        ],
        current_agent="creative_diagnosis_agent",
        stage="creative_diagnosis",
        business_type="ai_3d_custom",
    )

    messages = build_router_messages(context)
    payload_text = "\n".join(item["content"] for item in messages)

    assert "pending_evaluation.status 为 awaiting_feedback" in payload_text
    assert "继续追问评估依据" in payload_text
    assert "直接回答上一条 creative_diagnosis_agent" in payload_text
    assert "只有 current_user_message 明确要求修改、改写、优化、生成或产出" in payload_text
    assert "补充偏好或条件，不等于要求产出方案" in payload_text
    assert "明确继续需求梳理或仅补充普通项目需求时 switch 到 brief_agent" in payload_text


def test_orchestrator_advances_creative_iteration_and_recommends_exit_at_fifth_output():
    state = {
        "pending_creative_direction": {
            "status": "awaiting_feedback",
            "iteration_count": 4,
            "iteration_limit": 5,
            "exit_recommended": False,
        }
    }

    next_state = advance_creative_direction_iteration(
        state,
        prompt_message="再优化一次",
        reason="creative_direction_generated",
    )

    pending = next_state["pending_creative_direction"]
    assert pending["iteration_count"] == 5
    assert pending["status"] == "exit_recommended"
    assert pending["exit_recommended"] is True
    assert next_state["current_agent"] == "creative_direction_agent"
    assert next_state["stage"] == "creative_direction_exit_recommended"


@pytest.mark.asyncio
async def test_router_can_return_finish_brief_control_action(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"brief_building",'
                            '"target_agent":"brief_agent","stage":"brief_building",'
                            '"control_action":"finish_brief_now",'
                            '"reason":"用户明确希望停止追问并直接整理需求"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="先这样，直接帮我整理吧",
            history=[{"role": "user", "content": "杭州大屏，想做宠物裸眼3D"}],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "stay"
    assert route.target_agent == "brief_agent"
    assert route.intent == "brief_building"
    assert route.control_action == "finish_brief_now"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_brief_flow_routes_creative_direction_generation_to_direction_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"用户要生成创意方向"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="根据上面的信息帮我生成一个创意方案",
            history=[{"role": "user", "content": "我们想做杭州西湖主题的裸眼3D内容"}],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.stage == "creative_direction"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_business_intro_request_routes_via_llm_router(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"business_intro",'
                            '"target_agent":"business_intro_agent","stage":"business_intro",'
                            '"reason":"用户要了解公司业务"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="介绍一下你们可以提供哪些服务",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "business_intro_agent"
    assert route.stage == "business_intro"
    assert route.intent == "business_intro"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_creative_revision_after_evaluation_routes_to_direction_agent_via_llm(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"用户要求基于上一轮评估优化现有方案"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="这个方案优化一下",
            history=[
                {
                    "role": "user",
                    "content": "创意概念：水滴凝结成瓶，冰晶沿L型屏曲面飞散，最后露出品牌瓶身。",
                },
                {
                    "role": "assistant",
                    "content": "阶段性创意评估：成立点是空间感强，风险点是品牌识别滞后，优化方向是前置品牌资产。",
                },
            ],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    payload_text = "\n".join(item["content"] for item in captured_payload["messages"])
    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"
    assert "基于评估结果继续产出优化稿" in payload_text
    assert "不要把单独的“优化一下/帮我改一下/能不能再调整”当作 creative_diagnosis" in payload_text


@pytest.mark.asyncio
async def test_order_agent_can_leave_order_query_through_llm_router(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"用户在订单查询上下文里提出了新的创意延展需求"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
            history=[{"role": "assistant", "content": "当前账户下暂无订单记录。"}],
            current_agent="order_agent",
            stage="order_query",
            business_type="ai_3d_custom",
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert "当前处于 order_agent" in payload_text
    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.stage == "creative_direction"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_generic_view_reference_image_request_is_not_order_query_hard_guard(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"用户想基于参考图看创意方向"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="帮我查看这张参考图能做哪些创意方向",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_brief_flow_routes_attachment_only_upload_through_llm_router(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"brief_building",'
                            '"target_agent":"brief_agent","stage":"brief_building",'
                            '"reason":"用户只是上传素材补充 Brief，没有提出创意生成或评估意图"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message=(
                "[已上传文件: screen-photo.png]\n\n"
                "[图片理解摘要]\n"
                "文件：screen-photo.png\n"
                "视觉摘要：这是一张户外裸眼3D大屏现场图，可作为参考素材。"
            ),
            history=[
                {
                    "role": "assistant",
                    "content": "需求方向基本清楚了。您这边是否还有现场实拍图、屏幕照片或其他参考素材可以补充？",
                }
            ],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
            has_attachments=True,
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert '"upload_only_material": true' in payload_text
    assert '"user_authored_text": ""' in payload_text
    assert "上传素材是 Brief 收集的一部分" in payload_text
    assert route.action == "stay"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"
    assert route.intent == "brief_building"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_brief_flow_routes_image_with_creative_extension_text_to_direction_agent(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"用户明确要求基于图片做创意延展"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message=(
                "基于这张图做一些创意延展\n"
                "[已上传文件: reference.png]\n\n"
                "[图片理解摘要]\n"
                "文件：reference.png\n"
                "视觉摘要：这是一张带毛绒质感角色的参考设计图。"
            ),
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
            has_attachments=True,
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert '"upload_only_material": false' in payload_text
    assert '"user_authored_text": "基于这张图做一些创意延展"' in payload_text
    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_pending_creative_direction_image_upload_routes_through_llm_router(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"用户上传图片是在补全上一轮创意延展任务"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message=(
                "[已上传文件: reference.png]\n\n"
                "[图片理解摘要]\n"
                "文件：reference.png\n"
                "视觉摘要：这是一张毛绒动物参考设计图。"
            ),
            history=[
                {"role": "user", "content": "我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。"},
                {"role": "assistant", "content": "我还没有看到这轮消息里有图片附件，所以不能直接基于图片内容做创意延展。"},
            ],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
            pending_creative_direction={
                "status": "awaiting_image",
                "source": "creative_direction_agent",
                "prompt_message": "我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
            },
            has_attachments=True,
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert '"pending_creative_direction"' in payload_text
    assert '"status": "awaiting_image"' in payload_text
    assert '"upload_only_material": true' in payload_text
    assert "补全上一轮创意方向任务" in payload_text
    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_pending_creative_direction_feedback_stays_in_direction_agent(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction_review",'
                            '"control_action":"none","reason":"用户正在补充创意方向中的元素要求"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="还不行，必须有其他元素",
            history=[
                {"role": "assistant", "content": "**创意方向草案**：3D熊猫与酸奶在L型屏转角互动。"},
            ],
            current_agent="creative_direction_agent",
            stage="creative_direction_review",
            business_type="ai_3d_custom",
            pending_creative_direction={
                "status": "awaiting_feedback",
                "source": "creative_direction_agent",
            },
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert '"status": "awaiting_feedback"' in payload_text
    assert "增加/删除/替换元素" in payload_text
    assert route.action == "stay"
    assert route.target_agent == "creative_direction_agent"
    assert route.stage == "creative_direction_review"
    assert route.intent == "creative_direction"
    assert route.control_action == "none"


@pytest.mark.asyncio
async def test_pending_creative_direction_explicit_confirmation_returns_to_brief(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"brief_building",'
                            '"target_agent":"brief_agent","stage":"brief_building",'
                            '"control_action":"none","reason":"用户确认方向并要求继续梳理需求"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="这个方向可以，继续梳理需求吧",
            history=[
                {"role": "assistant", "content": "**创意方向草案**：3D熊猫、酸奶和竹叶形成空间互动。"},
            ],
            current_agent="creative_direction_agent",
            stage="creative_direction_review",
            business_type="ai_3d_custom",
            pending_creative_direction={"status": "awaiting_feedback"},
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"
    assert route.control_action == "none"


@pytest.mark.asyncio
async def test_exit_recommended_creative_direction_can_continue_when_user_explicitly_requests_revision(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction_exit_recommended",'
                            '"control_action":"none","reason":"用户明确要求继续修改一个关键元素"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="继续改，把竹叶换成水珠",
            history=[{"role": "assistant", "content": "当前方向已完成5轮迭代，建议确认后返回Brief。"}],
            current_agent="creative_direction_agent",
            stage="creative_direction_exit_recommended",
            business_type="ai_3d_custom",
            pending_creative_direction={
                "status": "exit_recommended",
                "iteration_count": 5,
                "iteration_limit": 5,
                "exit_recommended": True,
            },
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert '"status": "exit_recommended"' in payload_text
    assert "软提醒，不是强制退出" in payload_text
    assert route.action == "stay"
    assert route.target_agent == "creative_direction_agent"
    assert route.stage == "creative_direction_exit_recommended"
    assert route.control_action == "none"


@pytest.mark.asyncio
async def test_exit_recommended_creative_direction_returns_to_brief_after_confirmation(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"brief_building",'
                            '"target_agent":"brief_agent","stage":"brief_building",'
                            '"control_action":"none","reason":"用户接受退出建议并确认当前方向"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="可以，就按这一版，继续Brief吧",
            history=[],
            current_agent="creative_direction_agent",
            stage="creative_direction_exit_recommended",
            business_type="ai_3d_custom",
            pending_creative_direction={
                "status": "exit_recommended",
                "iteration_count": 5,
                "exit_recommended": True,
            },
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"
    assert route.control_action == "none"


@pytest.mark.asyncio
async def test_exit_recommended_creative_diagnosis_can_continue_when_user_asks_followup(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"creative_diagnosis",'
                            '"target_agent":"creative_diagnosis_agent","stage":"creative_diagnosis_exit_recommended",'
                            '"control_action":"none","reason":"用户仍有一个关键评估问题"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-diagnosis-exit-recommended",
            message="再比较一下两个方向的执行风险",
            history=[{"role": "assistant", "content": "这轮评估经过几次推演，建议先回到需求梳理。"}],
            current_agent="creative_diagnosis_agent",
            stage="creative_diagnosis_exit_recommended",
            business_type="ai_3d_custom",
            pending_evaluation={
                "status": "exit_recommended",
                "iteration_count": 5,
                "iteration_limit": 5,
                "exit_recommended": True,
            },
        )
    )

    payload_text = "\n".join(item["content"] for item in captured_payload["messages"])
    assert '"status": "exit_recommended"' in payload_text
    assert "软提醒，不是强制退出" in payload_text
    assert route.action == "stay"
    assert route.target_agent == "creative_diagnosis_agent"
    assert route.stage == "creative_diagnosis_exit_recommended"


@pytest.mark.asyncio
async def test_exit_recommended_creative_diagnosis_returns_to_brief_after_confirmation(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"brief_building",'
                            '"target_agent":"brief_agent","stage":"brief_building",'
                            '"control_action":"none","reason":"用户接受评估结论并继续需求梳理"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-diagnosis-exit-confirmed",
            message="可以，先按这个结论，继续梳理需求吧",
            history=[],
            current_agent="creative_diagnosis_agent",
            stage="creative_diagnosis_exit_recommended",
            business_type="ai_3d_custom",
            pending_evaluation={
                "status": "exit_recommended",
                "iteration_count": 5,
                "iteration_limit": 5,
                "exit_recommended": True,
            },
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"


@pytest.mark.asyncio
async def test_upload_image_summary_does_not_route_to_business_intro(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_direction",'
                            '"target_agent":"creative_direction_agent","stage":"creative_direction",'
                            '"reason":"pending 创意方向任务正在等待图片"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message=(
                "[已上传文件: reference.png]\n\n"
                "[图片理解摘要]\n"
                "文件：reference.png\n"
                "视觉摘要：这张图可以用于业务服务方向判断。"
            ),
            history=[
                {"role": "user", "content": "我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。"},
            ],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
            pending_creative_direction={
                "status": "awaiting_image",
                "source": "creative_direction_agent",
                "prompt_message": "我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
            },
            has_attachments=True,
        )
    )

    payload_text = "\n".join(m["content"] for m in captured_payload["messages"])
    assert '"user_authored_text": ""' in payload_text
    assert route.action == "switch"
    assert route.target_agent == "creative_direction_agent"
    assert route.intent == "creative_direction"
    assert route.source == "llm_router"


@pytest.mark.asyncio
async def test_initial_3d_video_brief_kickoff_selects_brief_agent(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"brief_building",'
                            '"target_agent":"brief_agent","reason":"用户只是开始梳理3D视频需求"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="想做一个3D视频，先帮我梳理一下大概方向。",
            history=[],
            current_agent=None,
            stage="intent_routing",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"
    assert route.intent == "brief_building"
    assert captured_payload["messages"][0]["role"] == "system"
    assert "想做一个3D视频" in captured_payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_mixed_brief_with_budget_routes_through_llm_router(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"stay","intent":"brief_building",'
                            '"target_agent":"brief_agent","stage":"brief_building",'
                            '"reason":"用户是在梳理包含预算约束的完整项目需求"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    message = (
        "你好，我们是一个新茶饮品牌，想在上海商圈的大屏做一支裸眼3D视频，"
        "主要是新品上市造势。现在只有大概方向：想要一杯饮品从屏幕里冲出来，"
        "有冰块、水花和品牌杯。预算和屏幕尺寸还没完全确定，"
        "你先帮我判断这个需求应该怎么拆。"
    )
    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message=message,
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "stay"
    assert route.target_agent == "brief_agent"
    assert route.intent == "brief_building"
    assert route.reason == "用户是在梳理包含预算约束的完整项目需求"
    assert route.source == "llm_router"
    assert message in captured_payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_brief_flow_routes_explicit_creative_evaluation_to_diagnosis_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_diagnosis",'
                            '"target_agent":"creative_diagnosis_agent","stage":"creative_diagnosis",'
                            '"reason":"用户要评估创意"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="这个巨型猫创意适不适合裸眼3D？",
            history=[{"role": "assistant", "content": "这次主要想做什么内容？"}],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "creative_diagnosis_agent"
    assert route.stage == "creative_diagnosis"
    assert route.intent == "creative_diagnosis"


@pytest.mark.asyncio
async def test_pending_creative_diagnosis_routes_next_concept_back_to_diagnosis_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        raise AssertionError("pending creative diagnosis should route before llm router")

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="毛绒大熊猫从L型屏幕里探出来，和路人互动",
            history=[{"role": "assistant", "content": "可以，我会从可行性、裸眼3D适配、传播价值和优化空间几个角度帮您看。"}],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
            pending_evaluation={"status": "awaiting_target"},
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "creative_diagnosis_agent"
    assert route.stage == "creative_diagnosis"
    assert route.intent == "creative_diagnosis"
    assert route.source == "rule"


@pytest.mark.asyncio
async def test_unclear_router_result_stays_in_current_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"action":"clarify","intent":"unclear","target_agent":"general_agent","reason":"不确定"}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="那就这样",
            history=[{"role": "assistant", "content": "是否按这个方向继续整理 Brief？"}],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "stay"
    assert route.target_agent == "brief_agent"
    assert route.intent == "unclear"


@pytest.mark.asyncio
async def test_router_switches_only_for_valid_target_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"action":"switch","intent":"order_query","target_agent":"order_agent","reason":"用户要查订单"}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="帮我查一下订单进度",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.intent == "order_query"
    assert route.target_agent == "order_agent"


@pytest.mark.asyncio
async def test_router_failure_stays_in_current_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        raise RuntimeError("router unavailable")

    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-test",
            message="这个流程怎么做",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "stay"
    assert route.target_agent == "brief_agent"
    assert "fallback" in route.reason


@pytest.mark.asyncio
async def test_initial_router_failure_falls_back_to_brief_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        raise RuntimeError("router unavailable")

    monkeypatch.setattr("app.services.ai_orchestrator.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_orchestrator.post_chat_completion", _mock_completion)

    route = await decide_route(
        OrchestratorContext(
            session_id="session-initial-fallback",
            message="帮我处理一下这个项目",
            history=[],
            current_agent=None,
            stage="intent_routing",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "switch"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"
    assert route.source == "fallback"


@pytest.mark.asyncio
async def test_ai_orchestrate_persists_first_selected_agent(monkeypatch):
    saved_states = []

    async def _mock_decide_route(context):
        assert context.current_agent is None
        assert context.stage == "intent_routing"
        return ai_module.RouteDecision(
            action="switch",
            intent="creative_direction",
            target_agent="creative_direction_agent",
            stage="creative_direction",
            business_type="ai_3d_custom",
            reason="用户明确要求创意延展",
        )

    monkeypatch.setattr(
        ai_module,
        "load_agent_state",
        lambda *_: {
            "current_agent": None,
            "stage": "intent_routing",
            "business_type": "ai_3d_custom",
            "brief_state": {},
            "agent_context_window": {"messages": []},
            "pending_evaluation": None,
            "pending_creative_direction": None,
        },
    )
    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda _session, _user, state: saved_states.append(state))

    response = await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-first-selection",
            message="基于图片做一些创意延展",
            history=[],
            current_agent=None,
            stage="intent_routing",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    assert response["target_agent"] == "creative_direction_agent"
    assert response["agent_state"]["current_agent"] == "creative_direction_agent"
    assert response["agent_state"]["stage"] == "creative_direction"
    assert saved_states[-1]["current_agent"] == "creative_direction_agent"


@pytest.mark.asyncio
async def test_ai_orchestrate_endpoint_returns_route(monkeypatch):
    async def _mock_decide_route(context):
        assert context.current_agent == "brief_agent"
        assert context.stage == "brief_building"
        return ai_module.RouteDecision(
            action="switch",
            intent="order_query",
            target_agent="order_agent",
            stage="order_query",
            business_type="ai_3d_custom",
            reason="用户要查询订单",
        )

    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)
    monkeypatch.setattr(
        ai_module,
        "load_agent_state",
        lambda *_: {
            "current_agent": "brief_agent",
            "stage": "brief_building",
            "brief_state": {},
            "agent_context_window": {"messages": []},
            "pending_evaluation": None,
            "pending_creative_direction": None,
        },
    )

    response = await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-test",
            message="帮我查一下订单进度",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    assert response["action"] == "switch"
    assert response["intent"] == "order_query"
    assert response["target_agent"] == "order_agent"


@pytest.mark.asyncio
async def test_ai_orchestrate_is_read_only_for_brief_state(monkeypatch):
    persisted_state = {
        "current_agent": "brief_agent",
        "stage": "brief_building",
        "brief_state": {
            "fields": {},
            "applied_message_ids": [],
        },
        "agent_context_window": {"messages": []},
        "pending_evaluation": None,
        "pending_creative_direction": None,
    }

    async def _unexpected_state_update(**_):
        raise AssertionError("Router must not extract or update Brief state")

    async def _mock_decide_route(context):
        assert context.brief_state["applied_message_ids"] == []
        assert context.message == "[已上传文件: cat.png]"
        return ai_module.RouteDecision(
            action="stay",
            intent="brief_building",
            target_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )

    monkeypatch.setattr(ai_module, "load_agent_state", lambda *_: persisted_state)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _unexpected_state_update)
    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)

    response = await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-test",
            message="[已上传文件: cat.png]",
            user_message_id="user-upload-1",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    assert response["agent_state"]["brief_state"]["applied_message_ids"] == []


@pytest.mark.asyncio
async def test_ai_orchestrate_routes_with_authoritative_sliding_window(monkeypatch):
    saved_states = []
    persisted_state = {
        "current_agent": "brief_agent",
        "stage": "brief_building",
        "brief_state": {"fields": {}, "applied_message_ids": []},
        "agent_context_window": {
            "messages": [
                {
                    "role": "assistant",
                    "content": "您手头有现场实拍图吗？",
                    "source_message_id": "stale-assistant",
                    "fingerprint": "stale",
                }
            ]
        },
        "pending_evaluation": None,
        "pending_creative_direction": None,
    }
    long_budget_question = (
        "已确认收到化妆品.png。" + ("这是与项目预算相关的专业分析。" * 100)
        + "项目制作预算大概在什么范围？"
    )
    long_previous_user_message = "此前的项目补充。" + ("这是一段较早的详细上下文。" * 100) + "此前补充结束。"
    history = [
        {
            "client_message_id": "user-earlier",
            "role": "user",
            "content": long_previous_user_message,
        },
        {
            "client_message_id": "assistant-budget",
            "role": "assistant",
            "content": long_budget_question,
        }
    ]

    async def _mock_context_compactor(payload, *, timeout=None, attempts=None):
        return {"choices": [{"message": {"content": "压缩的较早上下文"}}]}

    async def _mock_decide_route(context):
        assert context.history[0]["role"] == "user"
        assert context.history[0]["content"] == "压缩的较早上下文"
        assert context.history[-1] == {"role": "assistant", "content": long_budget_question}
        assert context.message == "没有"
        return ai_module.RouteDecision(
            action="stay",
            intent="brief_building",
            target_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )

    monkeypatch.setattr(ai_module, "load_agent_state", lambda *_: persisted_state)
    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda _session, _user, state: saved_states.append(state))
    monkeypatch.setattr("app.services.ai_context.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_context.post_chat_completion", _mock_context_compactor)

    await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-authoritative-window",
            message="没有",
            user_message_id="user-budget-answer",
            history=history,
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    saved_messages = saved_states[-1]["agent_context_window"]["messages"]
    assert [item["source_message_id"] for item in saved_messages] == [
        "user-earlier",
        "assistant-budget",
        "user-budget-answer",
    ]
    assert saved_states[-1]["brief_state"]["applied_message_ids"] == []


@pytest.mark.asyncio
async def test_ai_orchestrate_uses_persisted_creative_review_state_and_keeps_pending(monkeypatch):
    saved_states = []
    creative_state = {
        "current_agent": "creative_direction_agent",
        "stage": "creative_direction_review",
        "business_type": "ai_3d_custom",
        "brief_state": {},
        "agent_context_window": {"messages": []},
        "pending_evaluation": None,
        "pending_creative_direction": {"status": "awaiting_feedback"},
    }

    async def _mock_decide_route(context):
        assert context.current_agent == "creative_direction_agent"
        assert context.stage == "creative_direction_review"
        assert context.pending_creative_direction["status"] == "awaiting_feedback"
        return ai_module.RouteDecision(
            action="stay",
            intent="creative_direction",
            target_agent="creative_direction_agent",
            stage="creative_direction_review",
            business_type="ai_3d_custom",
        )

    monkeypatch.setattr(ai_module, "load_agent_state", lambda *_: creative_state)
    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda _session, _user, state: saved_states.append(state))

    response = await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-test",
            message="还不行，必须有其他元素",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    assert response["target_agent"] == "creative_direction_agent"
    assert response["agent_state"]["pending_creative_direction"]["status"] == "awaiting_feedback"
    assert response["agent_state"]["stage"] == "creative_direction_review"
    assert saved_states[-1]["pending_creative_direction"]["status"] == "awaiting_feedback"


@pytest.mark.asyncio
async def test_ai_orchestrate_uses_persisted_diagnosis_state_over_frontend_mode_and_can_exit(monkeypatch):
    saved_states = []
    diagnosis_state = {
        "current_agent": "creative_diagnosis_agent",
        "stage": "creative_diagnosis_review",
        "business_type": "ai_3d_custom",
        "brief_state": {},
        "agent_context_window": {"messages": []},
        "pending_evaluation": {
            "status": "awaiting_feedback",
            "iteration_count": 2,
            "iteration_limit": 5,
        },
        "pending_creative_direction": None,
    }

    async def _mock_decide_route(context):
        assert context.current_agent == "creative_diagnosis_agent"
        assert context.stage == "creative_diagnosis_review"
        assert context.pending_evaluation["status"] == "awaiting_feedback"
        return ai_module.RouteDecision(
            action="switch",
            intent="brief_building",
            target_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
            reason="用户接受评估并继续梳理需求",
        )

    monkeypatch.setattr(ai_module, "load_agent_state", lambda *_: diagnosis_state)
    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda _session, _user, state: saved_states.append(state))

    response = await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-diagnosis-exit",
            message="可以，继续梳理需求吧",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    assert response["target_agent"] == "brief_agent"
    assert response["agent_state"]["pending_evaluation"] is None
    assert response["agent_state"]["current_agent"] == "brief_agent"
    assert response["agent_state"]["stage"] == "brief_building"
    assert saved_states[-1]["current_agent"] == "brief_agent"


@pytest.mark.asyncio
async def test_ai_orchestrate_clears_pending_creative_review_only_when_route_exits(monkeypatch):
    creative_state = {
        "current_agent": "creative_direction_agent",
        "stage": "creative_direction_review",
        "business_type": "ai_3d_custom",
        "brief_state": {},
        "agent_context_window": {"messages": []},
        "pending_evaluation": None,
        "pending_creative_direction": {"status": "awaiting_feedback"},
    }

    async def _mock_decide_route(context):
        return ai_module.RouteDecision(
            action="switch",
            intent="brief_building",
            target_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )

    monkeypatch.setattr(ai_module, "load_agent_state", lambda *_: creative_state)
    monkeypatch.setattr(ai_module, "decide_route", _mock_decide_route)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda *_: None)

    response = await ai_module.ai_orchestrate(
        ai_module.OrchestrateRequest(
            session_id="session-test",
            message="这个方向可以，继续梳理需求吧",
            history=[],
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        ),
        _FakeUser(),
    )

    assert response["target_agent"] == "brief_agent"
    assert response["agent_state"]["pending_creative_direction"] is None
    assert response["agent_state"]["current_agent"] == "brief_agent"
    assert response["agent_state"]["stage"] == "brief_building"
