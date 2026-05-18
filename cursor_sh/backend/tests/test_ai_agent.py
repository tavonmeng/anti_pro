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
