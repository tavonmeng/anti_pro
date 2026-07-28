import json

import pytest

from app.services.ai_brief_state import (
    MEDIA_3D_BRIEF_FIELDS,
    build_brief_update_messages,
    build_brief_state_context,
    create_empty_brief_state,
    evaluate_creative_readiness,
    load_agent_state,
    merge_brief_updates,
    save_agent_state,
    update_agent_state_from_message,
)
from app.services.ai_image_understanding import IMAGE_CONTEXT_MARKER


def test_empty_media_brief_state_uses_current_3d_custom_fields():
    state = create_empty_brief_state("ai_3d_custom")

    assert list(state["fields"].keys()) == MEDIA_3D_BRIEF_FIELDS
    assert state["filled_fields"] == []
    assert "theme_concept" in state["missing_fields"]
    assert state["readiness"]["level"] == "insufficient"


def test_brief_update_prompt_treats_explicit_uncertainty_as_a_confirmed_field_state():
    messages = build_brief_update_messages(
        "不确定",
        [{"role": "assistant", "content": "预计上刊时间大概是什么时候？"}],
        create_empty_brief_state("ai_3d_custom"),
    )

    system_prompt = messages[0]["content"]
    assert "明确回答“不确定”“待定”或“暂未确认”" in system_prompt
    assert "将对应字段更新为“待定”" in system_prompt
    assert "后续不要因此重复追问" in system_prompt


@pytest.mark.asyncio
async def test_brief_extractor_uses_same_authoritative_window_for_repeated_short_answer(monkeypatch, tmp_path):
    captured = {}
    long_previous_user_message = "此前的项目补充。" + ("这是一段较早的详细上下文。" * 100) + "此前补充结束。"
    long_budget_question = (
        "已确认收到化妆品.png。" + ("这是与项目预算相关的专业分析。" * 100)
        + "项目制作预算大概在什么范围？"
    )

    async def _mock_state_parser(payload, *, timeout=None):
        captured.update(json.loads(payload["messages"][1]["content"]))
        return {"choices": [{"message": {"content": '{"updates":{"budget":"没有"},"events":[]}'}}]}

    async def _mock_context_compactor(payload, *, timeout=None, attempts=None):
        return {"choices": [{"message": {"content": "压缩的较早上下文"}}]}

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_state_parser)
    monkeypatch.setattr("app.services.ai_context.post_chat_completion", _mock_context_compactor)

    initial_state = {
        "current_agent": "brief_agent",
        "stage": "brief_building",
        "business_type": "ai_3d_custom",
        "brief_state": create_empty_brief_state("ai_3d_custom"),
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
    }
    save_agent_state("session-budget-answer", "user-budget-answer", initial_state)
    history = [
        {"client_message_id": "user-earlier", "role": "user", "content": long_previous_user_message},
        {"client_message_id": "assistant-photo", "role": "assistant", "content": "您手头有现场实拍图吗？"},
        {"client_message_id": "user-photo", "role": "user", "content": "没有"},
        {
            "client_message_id": "assistant-budget",
            "role": "assistant",
            "content": long_budget_question,
        },
    ]

    state = await update_agent_state_from_message(
        session_id="session-budget-answer",
        user_id="user-budget-answer",
        business_type="ai_3d_custom",
        message="没有",
        history=history,
        source_message_id="user-budget",
        memory_hints={},
    )

    assert captured["last_assistant_question"] == history[-1]["content"]
    assert captured["recent_history"] == [
        {"role": "user", "content": "压缩的较早上下文"},
        {"role": "assistant", "content": "您手头有现场实拍图吗？"},
        {"role": "user", "content": "没有"},
    ]
    assert state["brief_state"]["fields"]["budget"]["value"] == "没有"
    context_messages = state["agent_context_window"]["messages"]
    assert [item["source_message_id"] for item in context_messages][-2:] == [
        "assistant-budget",
        "user-budget",
    ]
    assert [item["content"] for item in context_messages].count("没有") == 2


def test_new_conversation_state_has_no_selected_subagent(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))

    state = load_agent_state("session-new", "user-new", "ai_3d_custom")

    assert state["current_agent"] is None
    assert state["stage"] == "intent_routing"


@pytest.mark.asyncio
async def test_direct_brief_update_activates_brief_agent_for_unrouted_state(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "")

    state = await update_agent_state_from_message(
        session_id="session-direct-brief",
        user_id="user-direct-brief",
        business_type="ai_3d_custom",
        message="想做一个裸眼3D视频，先梳理需求",
        history=[],
        source_message_id="msg-direct-brief",
        memory_hints={},
    )

    assert state["current_agent"] == "brief_agent"
    assert state["stage"] == "brief_building"


def test_merge_brief_updates_tracks_version_sources_and_overwrites():
    state = create_empty_brief_state("ai_3d_custom")

    updated = merge_brief_updates(
        state,
        {
            "theme_concept": "巨型猫从 L 型转角屏探出，与商场入口互动",
            "city_location": "成都核心商圈商场主入口",
            "budget": "30万左右",
        },
        source_message_id="msg-1",
    )
    updated = merge_brief_updates(updated, {"budget": "15万"}, source_message_id="msg-2")

    assert updated["version"] == 2
    assert updated["fields"]["theme_concept"]["value"] == "巨型猫从 L 型转角屏探出，与商场入口互动"
    assert updated["fields"]["theme_concept"]["source_message_ids"] == ["msg-1"]
    assert updated["fields"]["budget"]["value"] == "15万"
    assert updated["fields"]["budget"]["source_message_ids"] == ["msg-1", "msg-2"]
    assert updated["overwrites"][-1]["field"] == "budget"
    assert updated["overwrites"][-1]["old_value"] == "30万左右"
    assert updated["overwrites"][-1]["new_value"] == "15万"


def test_creative_readiness_levels_follow_media_3d_brief_fields():
    state = create_empty_brief_state("ai_3d_custom")
    insufficient = merge_brief_updates(state, {"theme_concept": "巨型猫探出屏幕"})

    provisional = merge_brief_updates(
        state,
        {
            "theme_concept": "巨型猫从 L 型转角屏探出，与商场入口互动",
            "city_location": "成都核心商圈商场主入口",
            "audience_scene": "年轻消费者和周末逛街人群",
            "resource_background": "新商业体开业造势，主入口人流密集",
        },
    )

    formal = merge_brief_updates(
        provisional,
        {
            "art_direction": "治愈、柔软、有打卡感",
            "viewing_path": "主入口广场正面与街口斜侧观看",
            "media_specs": "L 型转角屏，约 3840x2160",
            "content_review": "避免攻击性动作和坠落感",
            "online_time": "下个月底",
        },
    )

    assert evaluate_creative_readiness(insufficient)["level"] == "insufficient"
    assert evaluate_creative_readiness(provisional)["level"] == "provisional"
    assert evaluate_creative_readiness(formal)["level"] == "formal"


@pytest.mark.asyncio
async def test_creative_feedback_updates_context_without_merging_into_brief(monkeypatch, tmp_path):
    async def _unexpected_state_parser(*_, **__):
        raise AssertionError("creative review feedback must not run Brief extraction")

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _unexpected_state_parser)

    brief_state = merge_brief_updates(
        create_empty_brief_state("ai_3d_custom"),
        {"theme_concept": "大熊猫与酸奶在L型屏转角互动"},
        source_message_id="msg-original",
    )
    initial_state = {
        "current_agent": "creative_direction_agent",
        "stage": "creative_direction_review",
        "business_type": "ai_3d_custom",
        "brief_state": brief_state,
        "pending_creative_direction": {"status": "awaiting_feedback"},
    }
    save_agent_state("session-creative-feedback", "user-creative-feedback", initial_state)

    state = await update_agent_state_from_message(
        session_id="session-creative-feedback",
        user_id="user-creative-feedback",
        business_type="ai_3d_custom",
        message="还不行，必须有其他元素",
        history=[],
        source_message_id="msg-feedback",
        memory_hints={},
    )

    assert state["brief_state"]["fields"]["theme_concept"]["value"] == "大熊猫与酸奶在L型屏转角互动"
    assert state["brief_state"]["applied_message_ids"] == ["msg-original"]
    assert state["pending_creative_direction"]["status"] == "awaiting_feedback"
    assert state["agent_context_window"]["messages"][-1]["content"] == "还不行，必须有其他元素"


@pytest.mark.asyncio
async def test_state_update_does_not_use_regex_fallback_when_llm_extracts_nothing(monkeypatch, tmp_path):
    async def _mock_state_parser(payload, *, timeout=None):
        return {"choices": [{"message": {"content": '{"updates":{},"events":[]}'}}]}

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_state_parser)

    state = await update_agent_state_from_message(
        session_id="session-no-regex-fallback",
        user_id="user-no-regex-fallback",
        business_type="ai_3d_custom",
        message="杭州湖滨银泰in77 L型大屏，4K规格，下个月上刊，预算20w，毛绒质感熊猫。",
        history=[],
        source_message_id="msg-no-regex",
        memory_hints={},
    )

    fields = state["brief_state"]["fields"]
    assert fields["city_location"]["value"] == ""
    assert fields["media_specs"]["value"] == ""
    assert fields["online_time"]["value"] == ""
    assert fields["budget"]["value"] == ""
    assert fields["theme_concept"]["value"] == ""


@pytest.mark.asyncio
async def test_state_update_maps_short_delivery_answers_from_previous_question(monkeypatch, tmp_path):
    captured_payloads = []

    async def _mock_state_parser(payload, *, timeout=None):
        captured_payloads.append(payload)
        request_text = payload["messages"][-1]["content"]
        if '"current_user_message": "mp4"' in request_text:
            return {"choices": [{"message": {"content": '{"updates":{"tech_delivery":"视频格式 MP4"},"events":[]}'}}]}
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"updates":{"tech_delivery":"视频格式 MP4；'
                            '帧率、色彩空间等技术参数无特殊要求，可按通用交付规范执行"},"events":[]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_state_parser)

    first_state = await update_agent_state_from_message(
        session_id="session-short-tech",
        user_id="user-short-tech",
        business_type="ai_3d_custom",
        message="mp4",
        history=[
            {
                "role": "assistant",
                "content": "交付规范这边有固定要求吗？比如视频格式是MP4还是MOV、帧率25fps还是30fps、色彩空间Rec.709或sRGB。",
            }
        ],
        source_message_id="msg-mp4",
        memory_hints={},
    )

    tech_delivery = first_state["brief_state"]["fields"]["tech_delivery"]["value"]
    assert "MP4" in tech_delivery
    first_payload_text = captured_payloads[-1]["messages"][-1]["content"]
    assert "last_assistant_question" in first_payload_text
    assert "交付规范这边有固定要求吗" in first_payload_text

    second_state = await update_agent_state_from_message(
        session_id="session-short-tech",
        user_id="user-short-tech",
        business_type="ai_3d_custom",
        message="没有",
        history=[
            {
                "role": "assistant",
                "content": "为了确保画面流畅且色彩还原准确，帧率和色彩空间有固定要求吗？比如30fps配合Rec.709或sRGB。",
            }
        ],
        source_message_id="msg-no-tech",
        memory_hints={},
    )

    tech_delivery = second_state["brief_state"]["fields"]["tech_delivery"]["value"]
    assert "MP4" in tech_delivery
    assert "无特殊要求" in tech_delivery


@pytest.mark.asyncio
async def test_image_only_state_update_keeps_only_neutral_site_photo_fact(monkeypatch, tmp_path):
    async def _mock_state_parser(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"updates":{'
                            '"city_location":"图片摘要：城市街景和高楼",'
                            '"theme_concept":"巨型网球破墙而出",'
                            '"online_time":"图片摘要中没有时间但模型误填",'
                            '"site_photos":"参考图：巨型网球破墙而出，毛绒纤维质感明显"'
                            '},"events":[]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_state_parser)

    state = await update_agent_state_from_message(
        session_id="session-image-only",
        user_id="user-image-only",
        business_type="ai_3d_custom",
        message=(
            "[已上传文件: reference.png]\n\n"
            f"{IMAGE_CONTEXT_MARKER}\n"
            "文件：reference.png\n"
            "图片类型：参考设计/风格图\n"
            "视觉摘要：巨型网球冲破建筑外墙，具备裸眼3D破屏效果。"
        ),
        history=[],
        source_message_id="msg-image-only",
        memory_hints={},
    )

    fields = state["brief_state"]["fields"]
    assert fields["site_photos"]["value"] == "已上传图片素材"
    assert fields["city_location"]["value"] == ""
    assert fields["theme_concept"]["value"] == ""
    assert fields["art_direction"]["value"] == ""
    assert fields["media_specs"]["value"] == ""
    assert fields["online_time"]["value"] == ""

    context_message = state["agent_context_window"]["messages"][-1]["content"]
    assert IMAGE_CONTEXT_MARKER not in context_message
    assert "reference.png" not in context_message
    assert "巨型网球" not in context_message
    assert "用户上传了图片素材" in context_message


@pytest.mark.asyncio
async def test_image_context_is_not_sent_to_brief_state_parser(monkeypatch, tmp_path):
    captured_payload = {}

    async def _mock_state_parser(payload, *, timeout=None):
        captured_payload.update(payload)
        return {"choices": [{"message": {"content": '{"updates":{},"events":[]}'}}]}

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_state_parser)

    await update_agent_state_from_message(
        session_id="session-image-parser",
        user_id="user-image-parser",
        business_type="ai_3d_custom",
        message=(
            "这张是杭州 in77 的现场参考\n"
            "[已上传文件: reference.png]\n\n"
            f"{IMAGE_CONTEXT_MARKER}\n"
            "文件：reference.png\n"
            "图片类型：参考设计/风格图\n"
            "视觉摘要：巨型网球冲破建筑外墙，具备裸眼3D破屏效果。"
        ),
        history=[],
        source_message_id="msg-image-text",
        memory_hints={},
    )

    payload_text = "\n".join(item["content"] for item in captured_payload["messages"])
    assert "这张是杭州 in77 的现场参考" in payload_text
    assert IMAGE_CONTEXT_MARKER not in payload_text
    assert "reference.png" not in payload_text
    assert "巨型网球" not in payload_text


@pytest.mark.asyncio
async def test_state_update_turns_memory_hint_into_pending_confirmation(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "")

    state = await update_agent_state_from_message(
        session_id="session-memory-candidate",
        user_id="user-memory-candidate",
        business_type="ai_3d_custom",
        message="我想做毛绒质感的大熊猫",
        history=[],
        source_message_id="msg-subject",
        memory_hints={"city_location": "杭州巨屏（湖滨银泰in77 L型地标大屏）"},
    )

    brief_state = state["brief_state"]
    fields = brief_state["fields"]
    assert fields["city_location"]["value"] == ""

    pending = brief_state["pending_confirmation"]
    assert pending["field"] == "city_location"
    assert pending["candidate_value"] == "杭州巨屏（湖滨银泰in77 L型地标大屏）"
    assert pending["status"] == "pending"

    context = build_brief_state_context(state)
    assert "待用户确认" in context
    assert "杭州巨屏" in context


@pytest.mark.asyncio
async def test_state_update_preserves_latest_assistant_and_current_user_messages(monkeypatch, tmp_path):
    long_history_message = "创意方向草案：毛绒大熊猫从L型屏幕深处探出，与路人挥手互动。" * 40
    history = [{"role": "assistant", "content": long_history_message}]
    original_history = [dict(item) for item in history]

    async def _mock_brief_parser(payload, *, timeout=None):
        return {"choices": [{"message": {"content": '{"updates":{},"events":[]}'}}]}

    async def _mock_context_compactor(payload, *, timeout=None, attempts=None):
        return {"choices": [{"message": {"content": "压缩摘要：毛绒大熊猫从L型屏幕探出，与路人互动。"}}]}

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_brief_parser)
    monkeypatch.setattr("app.services.ai_context.post_chat_completion", _mock_context_compactor)

    state = await update_agent_state_from_message(
        session_id="session-context-window",
        user_id="user-context-window",
        business_type="ai_3d_custom",
        message="评估一下刚才这个方向",
        history=history,
        source_message_id="user-msg-1",
        memory_hints={},
    )

    assert history == original_history
    context_messages = state["agent_context_window"]["messages"]
    assert context_messages[0]["content"] == long_history_message
    assert context_messages[0]["compacted"] is False
    assert context_messages[-1]["content"] == "评估一下刚才这个方向"
    assert len(context_messages[0]["content"]) > 700


@pytest.mark.asyncio
async def test_state_parser_confirms_pending_memory_candidate(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "")

    memory_hints = {"city_location": "杭州巨屏（湖滨银泰in77 L型地标大屏）"}
    await update_agent_state_from_message(
        session_id="session-confirm-candidate",
        user_id="user-confirm-candidate",
        business_type="ai_3d_custom",
        message="我想做毛绒质感的大熊猫",
        history=[],
        source_message_id="msg-subject",
        memory_hints=memory_hints,
    )

    async def _mock_state_parser(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"events":[{"type":"confirm_pending","field":"city_location",'
                            '"value":"杭州巨屏（湖滨银泰in77 L型地标大屏）"}]}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_state_parser)

    state = await update_agent_state_from_message(
        session_id="session-confirm-candidate",
        user_id="user-confirm-candidate",
        business_type="ai_3d_custom",
        message="这个点位可以",
        history=[],
        source_message_id="msg-confirm",
        memory_hints=memory_hints,
    )

    brief_state = state["brief_state"]
    assert brief_state["pending_confirmation"] is None
    assert brief_state["fields"]["city_location"]["value"] == "杭州巨屏（湖滨银泰in77 L型地标大屏）"
    assert "msg-confirm" in brief_state["fields"]["city_location"]["source_message_ids"]


@pytest.mark.asyncio
async def test_pending_confirmation_blocks_rule_update_when_parser_has_no_event(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "")

    memory_hints = {"city_location": "杭州巨屏（湖滨银泰in77 L型地标大屏）"}
    await update_agent_state_from_message(
        session_id="session-pending-without-event",
        user_id="user-pending-without-event",
        business_type="ai_3d_custom",
        message="我想做毛绒质感的大熊猫",
        history=[],
        source_message_id="msg-subject",
        memory_hints=memory_hints,
    )

    state = await update_agent_state_from_message(
        session_id="session-pending-without-event",
        user_id="user-pending-without-event",
        business_type="ai_3d_custom",
        message="这个点位可以",
        history=[],
        source_message_id="msg-ambiguous",
        memory_hints=memory_hints,
    )

    brief_state = state["brief_state"]
    assert brief_state["fields"]["city_location"]["value"] == ""
    assert brief_state["pending_confirmation"]["field"] == "city_location"
    assert brief_state["pending_confirmation"]["candidate_value"] == "杭州巨屏（湖滨银泰in77 L型地标大屏）"
