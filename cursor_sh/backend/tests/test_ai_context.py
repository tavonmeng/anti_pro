import pytest

from app.services import ai_context


@pytest.mark.asyncio
async def test_append_agent_context_message_preserves_latest_two_and_compacts_older_long_message(monkeypatch):
    calls = []

    async def _mock_completion(payload, *, timeout=None, attempts=None):
        calls.append(payload)
        return {"choices": [{"message": {"content": "压缩摘要：毛绒大熊猫从L型屏探出，与路人互动。"}}]}

    monkeypatch.setattr(ai_context.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_context, "post_chat_completion", _mock_completion)

    long_text = "毛绒大熊猫从L型屏探出。" * 80
    state, current_content = await ai_context.append_agent_context_message(
        {},
        role="assistant",
        content=long_text,
        source_message_id="long-1",
    )
    assert current_content == long_text
    assert state["agent_context_window"]["messages"][0]["content"] == long_text
    assert state["agent_context_window"]["messages"][0]["compacted"] is False
    assert calls == []

    state, _ = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="偏向于卡通",
        source_message_id="short-1",
    )
    state, _ = await ai_context.append_agent_context_message(
        state,
        role="assistant",
        content="收到，我会继续评估。",
        source_message_id="short-2",
    )

    messages = state["agent_context_window"]["messages"]
    assert messages[0]["content"] == "压缩摘要：毛绒大熊猫从L型屏探出，与路人互动。"
    assert messages[0]["compacted"] is True
    assert [item["content"] for item in messages[-2:]] == [
        "偏向于卡通",
        "收到，我会继续评估。",
    ]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_sync_agent_context_window_preserves_latest_two_and_compacts_older_long_message(monkeypatch):
    calls = []

    async def _mock_completion(payload, *, timeout=None, attempts=None):
        calls.append(payload)
        return {"choices": [{"message": {"content": "压缩后的长方案摘要"}}]}

    monkeypatch.setattr(ai_context.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_context, "post_chat_completion", _mock_completion)

    older_long_text = "这是一版较早的长创意方向。" * 90
    latest_long_text = (
        "阶段性创意评估。" + ("成立点、风险点与优化建议。" * 90)
        + "醒狮风格偏向传统写实还是现代卡通？"
    )
    history = [{"role": "user", "content": f"消息{i}"} for i in range(5)]
    history.extend(
        [
            {"role": "assistant", "content": older_long_text},
            {"role": "user", "content": "广州醒狮非遗"},
            {"role": "assistant", "content": latest_long_text},
        ]
    )
    original_history = [dict(item) for item in history]

    state = await ai_context.sync_agent_context_window_from_history({}, history)

    assert history == original_history
    messages = state["agent_context_window"]["messages"]
    assert len(messages) == 8
    assert messages[-3]["content"] == "压缩后的长方案摘要"
    assert messages[-3]["compacted"] is True
    assert messages[-2]["content"] == "广州醒狮非遗"
    assert messages[-1]["content"] == latest_long_text
    assert messages[-1]["compacted"] is False
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_sync_agent_context_window_rebuilds_order_and_preserves_repeated_short_answers(monkeypatch):
    async def _unexpected_completion(*args, **kwargs):
        raise AssertionError("short messages should not require compaction")

    monkeypatch.setattr(ai_context.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_context, "post_chat_completion", _unexpected_completion)

    state = {
        "agent_context_window": {
            "messages": [
                {
                    "role": "assistant",
                    "content": "有现场实拍图吗？",
                    "source_message_id": "old-assistant",
                    "fingerprint": "stale",
                },
                {
                    "role": "user",
                    "content": "没有",
                    "source_message_id": "old-user",
                    "fingerprint": "stale",
                },
            ]
        }
    }
    history = [
        {"client_message_id": "a1", "role": "assistant", "content": "有现场实拍图吗？"},
        {"client_message_id": "u1", "role": "user", "content": "没有"},
        {
            "client_message_id": "a2",
            "role": "assistant",
            "content": "已确认收到化妆品.png。项目制作预算大概在什么范围？",
        },
        {"client_message_id": "u2", "role": "user", "content": "没有"},
    ]

    next_state = await ai_context.sync_agent_context_window_from_history(state, history)
    messages = next_state["agent_context_window"]["messages"]

    assert [item["content"] for item in messages] == [item["content"] for item in history]
    assert [item["source_message_id"] for item in messages] == ["a1", "u1", "a2", "u2"]
    assert [item["content"] for item in messages].count("没有") == 2


@pytest.mark.asyncio
async def test_append_agent_context_message_keeps_same_text_with_different_message_ids():
    state = {}
    state, _ = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="没有",
        source_message_id="answer-1",
    )
    state, _ = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="没有",
        source_message_id="answer-2",
    )

    messages = state["agent_context_window"]["messages"]
    assert [item["source_message_id"] for item in messages] == ["answer-1", "answer-2"]


@pytest.mark.asyncio
async def test_append_agent_context_message_keeps_repeated_text_without_message_ids():
    state = {}
    state, _ = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="没有",
    )
    state, _ = await ai_context.append_agent_context_message(
        state,
        role="user",
        content="没有",
    )

    assert [item["content"] for item in state["agent_context_window"]["messages"]] == [
        "没有",
        "没有",
    ]


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
