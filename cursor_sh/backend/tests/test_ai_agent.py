import pytest
from starlette.requests import Request

from app.api import ai as ai_module


def _request_without_auth() -> Request:
    return Request({"type": "http", "headers": []})


async def _no_existing_handoff(**_):
    return None


async def _mock_record_handoff(**_):
    return {"handoff_id": "handoff-test", "draft_order_id": "order-test", "is_new": True}


async def _mock_existing_handoff(**_):
    return {"handoff_id": "handoff-test", "draft_order_id": "order-test", "is_new": False}


@pytest.mark.asyncio
async def test_ai_chat_returns_mock_reply_without_ai_key(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我们想做一个成都太古里的裸眼3D项目",
            history=[],
        ),
        _request_without_auth(),
    )

    assert "message" in response
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_mock_completion_uses_frontend_completion_marker(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="没问题，需求已经完成",
            history=[],
        ),
        _request_without_auth(),
    )

    assert "【需求收集完成】" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_mock_completion_ignores_negative_completion_text(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="还没完成，预算和上线时间还不确定",
            history=[],
        ),
        _request_without_auth(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_handoff_request_stops_requirement_collection(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)
    monkeypatch.setattr(ai_module, "_record_handoff", _mock_record_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我不想用 AI 智能体了，帮我转人工顾问",
            history=[],
        ),
        _request_without_auth(),
    )

    assert response["handoff"] is True
    assert response["draft_order_id"] == "order-test"
    assert "专属顾问" in response["message"]
    assert "【需求收集完成】" not in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_handoff_negative_phrase_does_not_trigger(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="先不转人工，我继续补充需求",
            history=[],
        ),
        _request_without_auth(),
    )

    assert response.get("handoff") is not True
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_start_media_ai_3d_custom_uses_opening_question(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    response = await ai_module.ai_start("test-session", "ai_3d_custom")

    assert "这次大概想做什么样的内容" in response["reply"]
    assert "请先告诉我品牌或项目名称" not in response["reply"]
    assert "请先告诉我项目名称" not in response["reply"]


@pytest.mark.asyncio
async def test_ai_start_orderable_businesses_do_not_force_first_field(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    for business_type in ["ai_3d_custom", "video_purchase", "digital_art"]:
        response = await ai_module.ai_start("test-session", business_type)
        assert "请先告诉我" not in response["reply"]
        assert "这次" in response["reply"]


@pytest.mark.asyncio
async def test_ai_chat_handoff_does_not_match_artificial_intelligence(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我们想做人工智能主题的裸眼3D内容",
            history=[],
        ),
        _request_without_auth(),
    )

    assert response.get("handoff") is not True
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_existing_handoff_appends_followup(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _mock_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="补充一下，我们预算大概50万",
            history=[],
        ),
        _request_without_auth(),
    )

    assert response["handoff"] is True
    assert response["is_new"] is False
    assert "追加到人工对接记录" in response["message"]
    assert "【需求收集完成】" not in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_strips_early_completion_without_upload_wrapup(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        assert timeout == 120
        return {
            "choices": [
                {
                    "message": {
                        "content": "需求已经足够，我来整理。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module.settings, "AI_HTTP_TIMEOUT", 120)
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="下个月月底",
            history=[
                {"role": "user", "content": "我想在杭州天幕巨屏投放3D视频"},
                {"role": "assistant", "content": "面向什么受众？"},
                {"role": "user", "content": "面向游客宣传"},
                {"role": "assistant", "content": "主题是什么？"},
                {"role": "user", "content": "杭州西湖美景"},
                {"role": "assistant", "content": "风格怎么呈现？"},
                {"role": "user", "content": "写意的传统意境"},
                {"role": "assistant", "content": "需要哪些元素？"},
                {"role": "user", "content": "西湖标志性景观"},
                {"role": "assistant", "content": "时长多少？"},
                {"role": "user", "content": "30s"},
                {"role": "assistant", "content": "技术要求？"},
                {"role": "user", "content": "没有特定要求"},
            ],
        ),
        _request_without_auth(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "现场实拍图" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_stream_qwen_uses_chat_completions_without_responses_probe(monkeypatch):
    async def _unexpected_responses_stream(*_, **__):
        raise AssertionError("Qwen stream should not probe the Responses API")
        yield ""

    async def _mock_chat_stream_events(payload, *, timeout=None):
        assert payload["model"] == "qwen3.6-plus"
        assert payload["messages"][-1]["content"] == "我想做一个裸眼3D项目"
        assert timeout == 120
        yield {"type": "content", "content": "好的"}
        yield {"type": "content", "content": "，请问计划投放在哪个城市？"}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(ai_module.settings, "AI_RESPONSES_BASE_URL", "")
    monkeypatch.setattr(ai_module.settings, "AI_PREFER_RESPONSES_API", False)
    monkeypatch.setattr(ai_module.settings, "AI_MODEL_NAME", "qwen3.6-plus")
    monkeypatch.setattr(ai_module.settings, "AI_HTTP_TIMEOUT", 120)
    monkeypatch.setattr(ai_module, "stream_responses_completion", _unexpected_responses_stream)
    monkeypatch.setattr(ai_module, "stream_chat_completion_events", _mock_chat_stream_events)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat_stream(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我想做一个裸眼3D项目",
            history=[],
        ),
        _request_without_auth(),
    )

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    body = "".join(chunks)

    assert "event: delta" in body
    assert "chat_completions" in body
    assert "请问计划投放在哪个城市" in body


@pytest.mark.asyncio
async def test_qwen_chat_payload_disables_thinking_by_default(monkeypatch):
    from app.services import ai_client

    monkeypatch.setattr(ai_client.settings, "AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(ai_client.settings, "AI_MODEL_NAME", "qwen3.6-plus")
    monkeypatch.setattr(ai_client.settings, "AI_ENABLE_THINKING", False)

    payload = ai_client._prepare_chat_payload({"model": "qwen3.6-plus", "messages": []})

    assert payload["enable_thinking"] is False


def test_design_thinking_only_for_creative_plan_requests():
    assert ai_module._should_enable_design_thinking("帮我生成一个设计方案")
    assert ai_module._should_enable_design_thinking("根据上面的信息写一版策划方案")
    assert ai_module._should_enable_design_thinking("出个创意方案给客户看")

    assert not ai_module._should_enable_design_thinking("这个能不能做")
    assert not ai_module._should_enable_design_thinking("排期多久")
    assert not ai_module._should_enable_design_thinking("报价方案大概怎么定")
    assert not ai_module._should_enable_design_thinking("怎么落地执行")
