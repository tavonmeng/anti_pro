import pytest

from app.api import ai as ai_module
from app.services.ai_orchestrator import (
    OrchestratorContext,
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
    assert "ready_to_extract" in payload_text
    assert "finish_brief_now" in payload_text
    assert "handoff_requested" in payload_text
    assert "表单" in payload_text
    assert "确认下单" in payload_text
    assert "评估完成后" in payload_text


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
                            '"target_agent":"creative_direction_agent","reason":"用户要生成创意方向"}'
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
async def test_upload_image_summary_does_not_trigger_business_intro_rule(monkeypatch):
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
async def test_brief_flow_uses_llm_router_for_initial_3d_video_brief_kickoff(monkeypatch):
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
            current_agent="brief_agent",
            stage="brief_building",
            business_type="ai_3d_custom",
        )
    )

    assert route.action == "stay"
    assert route.target_agent == "brief_agent"
    assert route.stage == "brief_building"
    assert route.intent == "brief_building"
    assert captured_payload["messages"][0]["role"] == "system"
    assert "想做一个3D视频" in captured_payload["messages"][1]["content"]


@pytest.mark.asyncio
async def test_brief_flow_routes_explicit_creative_evaluation_to_diagnosis_agent(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"action":"switch","intent":"creative_diagnosis",'
                            '"target_agent":"creative_diagnosis_agent","reason":"用户要评估创意"}'
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
            message="预算30万，这个巨型猫创意适不适合裸眼3D？",
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
