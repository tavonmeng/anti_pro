from types import SimpleNamespace

from app.services.ai_brief_agent import (
    build_brief_memory_hints,
    select_next_brief_question,
    sanitize_brief_agent_reply,
)
from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates


def _agent_state_with(updates: dict[str, str]) -> dict:
    return {
        "current_agent": "brief_agent",
        "stage": "brief_building",
        "business_type": "ai_3d_custom",
        "brief_state": merge_brief_updates(create_empty_brief_state("ai_3d_custom"), updates),
    }


def test_brief_agent_next_question_skips_filled_location_and_specs():
    agent_state = _agent_state_with(
        {
            "city_location": "杭州湖滨银泰in77 L型大屏",
            "media_specs": "L型大屏，4K规格",
            "theme_concept": "毛绒质感熊猫，慵懒趴姿，与周围环境互动并冲出屏幕",
            "art_direction": "毛绒质感，亲和，有停留和拍摄点",
            "audience_scene": "商圈年轻消费者和游客",
            "budget": "20w",
            "online_time": "下个月上刊",
            "site_photos": "已上传参考文件",
        }
    )

    next_question = select_next_brief_question(agent_state["brief_state"])

    assert next_question["field"] not in {"city_location", "media_specs"}
    assert next_question["field"] == "viewing_path"
    assert "观看" in next_question["question"] or "动线" in next_question["question"]


def test_brief_agent_does_not_jump_to_technical_specs_when_context_is_missing():
    agent_state = _agent_state_with(
        {
            "city_location": "杭州湖滨银泰in77 L型大屏",
            "theme_concept": "毛绒质感熊猫，从屏幕里探出",
            "art_direction": "柔软、亲和、有打卡感",
        }
    )

    next_question = select_next_brief_question(agent_state["brief_state"])

    assert next_question["field"] in {"viewing_path", "audience_scene", "resource_background"}
    assert next_question["field"] != "media_specs"
    assert "分辨率" not in next_question["question"]


def test_brief_agent_next_question_uses_pending_city_confirmation():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感的大熊猫",
            "art_direction": "毛绒质感",
        }
    )
    agent_state["brief_state"]["pending_confirmation"] = {
        "id": "pending-city",
        "field": "city_location",
        "label": "投放城市与媒体位置",
        "candidate_value": "杭州 杭州巨屏（湖滨银泰in77 L型地标大屏）",
        "source": "memory_candidate",
        "status": "pending",
    }

    next_question = select_next_brief_question(agent_state["brief_state"])

    assert next_question["field"] == "city_location"
    assert "我们了解到" in next_question["question"]
    assert "杭州巨屏（湖滨银泰in77 L型地标大屏）" in next_question["question"]
    assert "杭州 杭州巨屏" not in next_question["question"]
    assert "当前 Brief" not in next_question["question"]
    assert "待确认" not in next_question["question"]
    assert "哪个城市" not in next_question["question"]


def test_brief_memory_hints_do_not_reuse_sensitive_budget_or_online_time():
    memory = SimpleNamespace(
        screen_resources=[
            {
                "city": "杭州",
                "name": "湖滨银泰in77 L型大屏",
                "specs": "L型屏，4K",
                "notes": "主入口正面观看；下月初上刊；预算20w",
            }
        ],
        project_preferences={
            "common_cities": ["杭州"],
            "budget_range": "20w",
            "online_time": "下月初上刊",
        },
    )

    hints = build_brief_memory_hints(memory)

    assert hints["city_location"] == "杭州 湖滨银泰in77 L型大屏"
    assert hints["media_specs"] == "L型屏，4K"
    assert "budget" not in hints
    assert "online_time" not in hints
    assert "20w" not in str(hints)
    assert "下月初" not in str(hints)
    assert "上刊" not in str(hints)


def test_brief_agent_site_photos_question_does_not_call_materials_brief_attachment():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感熊猫，慵懒趴姿，与周围环境互动并冲出屏幕",
            "city_location": "杭州湖滨银泰in77 L型大屏",
            "viewing_path": "商圈主入口正面和斜侧观看",
            "audience_scene": "商圈年轻消费者和游客",
            "art_direction": "毛绒质感，亲和，有停留和拍摄点",
            "resource_background": "商圈地标屏内容焕新",
            "media_specs": "L型大屏，4K规格",
            "online_time": "下个月上刊",
            "content_review": "避免惊吓动作",
            "special_requirements": "希望突出治愈感",
        }
    )

    next_question = select_next_brief_question(agent_state["brief_state"])

    assert next_question["field"] == "site_photos"
    assert "Brief 附件" not in next_question["question"]
    assert "作为 Brief" not in next_question["question"]


def test_brief_agent_sanitizes_redundant_specs_question_from_model_reply():
    agent_state = _agent_state_with(
        {
            "city_location": "杭州湖滨银泰in77 L型大屏",
            "media_specs": "L型大屏，4K规格",
            "theme_concept": "毛绒质感熊猫，慵懒趴姿，与周围环境互动并冲出屏幕",
            "art_direction": "毛绒质感",
            "audience_scene": "商圈年轻消费者和游客",
            "budget": "20w",
            "online_time": "下个月上刊",
            "site_photos": "已上传参考文件",
        }
    )
    reply = (
        "结合您提供的素材和之前的沟通，目前项目核心要素已明确："
        "杭州湖滨银泰in77 L型大屏、毛绒质感熊猫、慵懒趴姿、4K规格、下个月上刊、预算20w。\n\n"
        "我还需要再补充一个关键信息：这次项目对应的投放点位或屏幕规格目前方便确认吗？"
        "如果暂时没有完整参数，先说城市、屏幕位置或已有规格也可以。"
    )

    sanitized = sanitize_brief_agent_reply(reply, agent_state)

    assert "投放点位或屏幕规格" not in sanitized
    assert "城市、屏幕位置或已有规格" not in sanitized
    assert "观看" in sanitized or "动线" in sanitized


def test_brief_agent_sanitizes_generic_city_question_with_pending_confirmation():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感的大熊猫",
            "art_direction": "毛绒质感",
        }
    )
    agent_state["brief_state"]["pending_confirmation"] = {
        "id": "pending-city",
        "field": "city_location",
        "label": "投放城市与媒体位置",
        "candidate_value": "杭州",
        "source": "memory_candidate",
        "status": "pending",
    }
    reply = "这个方向我先记下。为了判断画面尺度和现场观看关系，想确认一下这条内容大概会投放在哪个城市或哪块屏幕？"

    sanitized = sanitize_brief_agent_reply(reply, agent_state)

    assert "杭州" in sanitized
    assert "哪个城市或哪块屏幕" not in sanitized
