import pytest
from starlette.requests import Request

from app.api import ai as ai_module


def _request_without_auth() -> Request:
    return Request({"type": "http", "headers": []})


def _llm_response(content: str):
    return {"choices": [{"message": {"content": content}}]}


@pytest.mark.asyncio
async def test_ai_chat_returns_mock_reply_without_ai_key(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)

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
    assert response["state"]["is_complete"] is False
    assert "content" in response["state"]["collected_fields"]


@pytest.mark.asyncio
async def test_ai_chat_mock_completion_uses_frontend_completion_marker(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="没问题，需求已经完成",
            history=[],
        ),
        _request_without_auth(),
    )

    assert "【需求收集完成】" in response["message"]
    assert response["state"]["is_complete"] is True


@pytest.mark.asyncio
async def test_ai_chat_mock_completion_ignores_negative_completion_text(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)

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
    assert response["state"]["is_complete"] is False


def test_requirement_state_marks_missing_and_next_field(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")

    state = ai_module._build_requirement_state(
        "ai_3d_custom",
        fields={
            "brand": "耐克",
            "content": "运动鞋裸眼3D破屏效果",
            "budget": "30万",
        },
        updated_fields=["budget"],
        confidence=0.9,
    )

    assert state["collected_fields"] == ["brand", "content", "budget"]
    assert state["missing_fields"][0] == "target_group"
    assert state["next_field"] == "target_group"
    assert state["updated_fields"] == ["budget"]


def test_requirement_state_skipped_field_is_not_missing(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")

    state = ai_module._build_requirement_state(
        "ai_3d_custom",
        fields={
            "brand": "耐克",
            "content": "运动鞋裸眼3D破屏效果",
            "city": "成都太古里",
        },
        skipped_fields=["budget"],
        updated_fields=["budget"],
    )

    assert "budget" not in state["missing_fields"]
    assert "budget" in state["skipped_fields"]


def test_extract_merge_prefers_latest_state_fields(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")

    merged = ai_module._merge_state_into_extracted(
        {"brand": "耐克", "budget": "10万", "city": "成都"},
        {
            "fields": {"budget": "30万", "city": "重庆"},
            "updated_fields": ["budget", "city"],
        },
        "ai_3d_custom",
    )

    assert merged["budget"] == "30万"
    assert merged["city"] == "重庆"
    assert merged["brand"] == "耐克"


def test_extract_merge_clears_skipped_latest_field(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")

    merged = ai_module._merge_state_into_extracted(
        {"brand": "耐克", "budget": "10万"},
        {
            "fields": {"brand": "耐克"},
            "skipped_fields": ["budget"],
            "updated_fields": ["budget"],
        },
        "ai_3d_custom",
    )

    assert merged["budget"] == ""


def test_extract_merge_keeps_state_remarks(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "brand")

    merged = ai_module._merge_state_into_extracted(
        {"brand": "耐克"},
        {
            "fields": {"brand": "耐克"},
            "remarks": "客户提到内部审核周期较长，执行排期需预留缓冲。",
        },
        "ai_3d_custom",
    )

    assert merged["remarks"] == "客户提到内部审核周期较长，执行排期需预留缓冲。"


def test_extract_merge_keeps_tracked_optional_state_fields(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    merged = ai_module._merge_state_into_extracted(
        {"project_name": "春熙路项目"},
        {
            "fields": {
                "project_name": "春熙路项目",
                "budget": "60万",
                "special_requirements": "需要特殊裸眼3D破框效果",
            },
            "updated_fields": ["budget", "special_requirements"],
        },
        "ai_3d_custom",
    )

    assert merged["budget"] == "60万"
    assert merged["special_requirements"] == "需要特殊裸眼3D破框效果"


def test_completion_gate_blocks_early_llm_completion(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    state = ai_module._build_requirement_state(
        "ai_3d_custom",
        fields={
            "project_name": "分众传媒成都大屏项目",
            "city_location": "成都春熙路",
            "viewing_path": "纵向观看",
            "art_direction": "自然生态意象",
            "theme_concept": "关爱大自然",
            "media_specs": "7680x2160",
        },
    )

    reply, is_complete = ai_module._enforce_completion_gate(
        "核心需求信息已基本覆盖，我来整理。 【需求收集完成】",
        state,
        "项目背景就是关爱大自然",
    )

    assert is_complete is False
    assert "【需求收集完成】" not in reply
    assert "项目背景" in reply


def test_completion_gate_allows_user_stop_intent_with_partial_info(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    state = ai_module._build_requirement_state(
        "ai_3d_custom",
        fields={
            "project_name": "分众传媒成都大屏项目",
            "city_location": "成都春熙路",
        },
    )

    reply, is_complete = ai_module._enforce_completion_gate(
        "我先按当前信息整理，缺失项会保留为空。 【需求收集完成】",
        state,
        "先这样吧，后面再补",
    )

    assert is_complete is True
    assert "【需求收集完成】" in reply


def test_completion_gate_allows_sufficient_media_collection(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    state = ai_module._build_requirement_state(
        "ai_3d_custom",
        fields={
            "project_name": "分众传媒成都大屏项目",
            "resource_background": "春熙路核心商圈大屏",
            "audience_scene": "商圈年轻客群",
            "city_location": "成都春熙路",
            "viewing_path": "纵向观看",
            "art_direction": "自然生态意象",
            "theme_concept": "关爱大自然",
            "media_specs": "7680x2160",
        },
    )

    reply, is_complete = ai_module._enforce_completion_gate(
        "信息已经基本差不多，我来整理。 【需求收集完成】",
        state,
        "没有其他补充",
    )

    assert is_complete is True
    assert "【需求收集完成】" in reply


@pytest.mark.asyncio
async def test_post_json_chat_completion_retries_empty_content(monkeypatch):
    calls = []

    async def fake_post_chat_completion(payload, *, timeout=None):
        calls.append(payload)
        if len(calls) == 1:
            return _llm_response("")
        return _llm_response('{"fields": {"budget": "30万"}}')

    monkeypatch.setattr(ai_module, "post_chat_completion", fake_post_chat_completion)

    parsed = await ai_module._post_json_chat_completion(
        {"messages": []},
        schema_hint='{"fields": {}}',
        timeout=1.0,
    )

    assert parsed == {"fields": {"budget": "30万"}}
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_post_json_chat_completion_repairs_invalid_json_with_llm(monkeypatch):
    calls = []

    async def fake_post_chat_completion(payload, *, timeout=None):
        calls.append(payload)
        if len(calls) == 1:
            return _llm_response("预算是30万")
        return _llm_response('{"fields": {"budget": "30万"}}')

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module, "post_chat_completion", fake_post_chat_completion)

    parsed = await ai_module._post_json_chat_completion(
        {"messages": []},
        schema_hint='{"fields": {}}',
        timeout=1.0,
    )

    assert parsed == {"fields": {"budget": "30万"}}
    assert len(calls) == 2
