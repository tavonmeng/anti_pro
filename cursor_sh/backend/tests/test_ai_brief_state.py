import pytest

from app.services.ai_brief_state import (
    MEDIA_3D_BRIEF_FIELDS,
    build_brief_state_context,
    create_empty_brief_state,
    deterministic_media_brief_updates,
    evaluate_creative_readiness,
    merge_brief_updates,
    update_agent_state_from_message,
)


def test_empty_media_brief_state_uses_current_3d_custom_fields():
    state = create_empty_brief_state("ai_3d_custom")

    assert list(state["fields"].keys()) == MEDIA_3D_BRIEF_FIELDS
    assert state["filled_fields"] == []
    assert "theme_concept" in state["missing_fields"]
    assert state["readiness"]["level"] == "insufficient"


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


def test_deterministic_updates_detect_4k_and_l_type_screen_specs():
    updates = deterministic_media_brief_updates(
        "杭州湖滨银泰in77 L型大屏，4K规格，下个月上刊，预算20w，毛绒质感熊猫。"
    )

    assert "city_location" in updates
    assert "media_specs" in updates
    assert "online_time" in updates
    assert "budget" in updates


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
