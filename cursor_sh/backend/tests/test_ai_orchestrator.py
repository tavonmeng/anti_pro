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
    assert "需求收集完成" in payload_text
    assert "表单" in payload_text
    assert "确认下单" in payload_text
    assert "评估完成后" in payload_text


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
