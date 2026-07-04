import pytest

from app.services import ai_context


@pytest.mark.asyncio
async def test_append_agent_context_message_compacts_only_long_messages(monkeypatch):
    calls = []

    async def _mock_completion(payload, *, timeout=None, attempts=None):
        calls.append(payload)
        return {"choices": [{"message": {"content": "压缩摘要：毛绒大熊猫从L型屏探出，与路人互动。"}}]}

    monkeypatch.setattr(ai_context.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_context, "post_chat_completion", _mock_completion)

    state = {}
    short_state, short_content = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="短消息",
        source_message_id="short-1",
    )
    long_text = "毛绒大熊猫从L型屏探出。" * 80
    next_state, compact_content = await ai_context.append_agent_context_message(
        short_state,
        role="user",
        content=long_text,
        source_message_id="long-1",
    )

    messages = next_state["agent_context_window"]["messages"]
    assert short_content == "短消息"
    assert messages[0]["content"] == "短消息"
    assert compact_content == "压缩摘要：毛绒大熊猫从L型屏探出，与路人互动。"
    assert messages[1]["content"] == compact_content
    assert messages[1]["compacted"] is True
    assert len(messages[1]["content"]) <= ai_context.AGENT_CONTEXT_MAX_MESSAGE_CHARS
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_sync_agent_context_window_preserves_raw_history_and_limits_window(monkeypatch):
    async def _mock_completion(payload, *, timeout=None, attempts=None):
        return {"choices": [{"message": {"content": "压缩后的长方案摘要"}}]}

    monkeypatch.setattr(ai_context.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_context, "post_chat_completion", _mock_completion)

    long_text = "这是一版很长的创意方向。" * 90
    history = [{"role": "user", "content": f"消息{i}"} for i in range(7)]
    history.append({"role": "assistant", "content": long_text})
    original_history = [dict(item) for item in history]

    state = await ai_context.sync_agent_context_window_from_history({}, history)

    assert history == original_history
    messages = state["agent_context_window"]["messages"]
    assert len(messages) == 8
    assert messages[-1]["content"] == "压缩后的长方案摘要"
    assert all(len(item["content"]) <= ai_context.AGENT_CONTEXT_MAX_MESSAGE_CHARS for item in messages)


@pytest.mark.asyncio
async def test_append_agent_context_message_deduplicates_by_source_message_id(monkeypatch):
    async def _unexpected_completion(*args, **kwargs):
        raise AssertionError("duplicate message should not be compacted again")

    monkeypatch.setattr(ai_context.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_context, "post_chat_completion", _unexpected_completion)

    state = {
        "agent_context_window": {
            "version": 1,
            "max_messages": 8,
            "max_chars_per_message": 700,
            "messages": [
                {
                    "role": "user",
                    "content": "已存在的压缩消息",
                    "source_message_id": "message-1",
                    "compacted": True,
                    "original_chars": 1200,
                }
            ],
        }
    }

    next_state, content = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="新内容不会被使用",
        source_message_id="message-1",
    )

    assert content == "已存在的压缩消息"
    assert len(next_state["agent_context_window"]["messages"]) == 1
