from types import SimpleNamespace

from app.services.ai_brief_agent import (
    build_brief_agent_instruction,
    build_brief_memory_hints,
    mark_creative_evaluation_hint_shown,
    select_next_brief_question,
    sanitize_brief_agent_reply,
    should_show_creative_evaluation_hint,
)
from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates


def _agent_state_with(updates: dict[str, str]) -> dict:
    return {
        "current_agent": "brief_agent",
        "stage": "brief_building",
        "business_type": "ai_3d_custom",
        "brief_state": merge_brief_updates(create_empty_brief_state("ai_3d_custom"), updates),
    }


def test_brief_agent_next_question_uses_three_brief_categories_in_order():
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

    assert next_question["category"] == "basic_info"
    assert next_question["label"] == "基础信息"
    assert "viewing_path" in next_question["missing_fields"]
    assert "media_specs" not in next_question["missing_fields"]


def test_brief_agent_does_not_jump_to_technical_specs_when_context_is_missing():
    agent_state = _agent_state_with(
        {
            "city_location": "杭州湖滨银泰in77 L型大屏",
            "theme_concept": "毛绒质感熊猫，从屏幕里探出",
            "art_direction": "柔软、亲和、有打卡感",
        }
    )

    next_question = select_next_brief_question(agent_state["brief_state"])

    assert next_question["category"] == "basic_info"
    assert "media_specs" not in next_question["missing_fields"]
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


def test_brief_agent_hands_memory_specs_candidate_to_llm_and_preserves_fallback_details():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感的大熊猫",
            "city_location": "杭州湖滨银泰in77 L型地标大屏",
            "art_direction": "毛绒质感",
        }
    )
    agent_state["brief_state"]["pending_confirmation"] = {
        "id": "pending-specs",
        "field": "media_specs",
        "label": "屏幕规格",
        "candidate_value": "L型屏，100m x 70m，L型，L型结构，约100m x 70m，L型地标大屏，约宽100m x 高70m",
        "source": "memory_candidate",
        "status": "pending",
    }

    next_question = select_next_brief_question(agent_state["brief_state"])
    instruction = build_brief_agent_instruction(agent_state)

    assert next_question["field"] == "media_specs"
    assert "可能有这些参数" not in next_question["question"]
    assert "有一组可参考规格" not in next_question["question"]
    assert "100m" in next_question["question"]
    assert "70m" in next_question["question"]
    assert "建议下一问" not in instruction
    assert "候选信息" in instruction
    assert "L型屏，100m x 70m，L型，L型结构" in instruction
    assert "必须带出候选信息里的核心内容" in instruction
    assert "不能只说" in instruction
    assert "不要原样罗列" in instruction
    assert "自行合并" in instruction


def test_brief_agent_instruction_encourages_professional_context_before_next_question():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感的大熊猫",
            "city_location": "杭州湖滨银泰in77 L型地标大屏",
            "art_direction": "治愈、柔软、有互动感",
        }
    )

    instruction = build_brief_agent_instruction(agent_state)

    assert "按信息复杂度" in instruction
    assert "关键 Brief 信息" in instruction
    assert "不要为了显得专业而写成小报告" in instruction
    assert "1-2 句" not in instruction
    assert "专业判断" in instruction
    assert "不是每轮必须" in instruction
    assert "不要只做机械确认" in instruction
    assert "承接必须优先回应用户最新输入" in instruction
    assert "不要复述上一轮 assistant 的专业判断" in instruction
    assert "避免连续使用同一种过渡句式" in instruction
    assert "信息密度较高" in instruction
    assert "至少两个短段落" in instruction
    assert "最后一个问题单独成段" in instruction
    assert "少量加粗关键事实或关键判断" in instruction
    assert "凡是会进入 Brief 的内容信息都属于重点信息" in instruction
    assert "只加粗具体 Brief 内容" in instruction
    assert "不加粗模板词" in instruction
    assert "如果只是短答确认或简单追问，可以不加粗" not in instruction
    assert "只有纯确认或一句话短追问可以不加粗" in instruction
    assert "同时承担解释、判断和引导" in instruction
    assert "阅读锚点" in instruction
    assert "每轮最多加粗 1 处" not in instruction
    assert "不要每轮都使用固定标题" in instruction
    assert "基础信息" in instruction
    assert "创意方向" in instruction
    assert "技术与交付" in instruction
    assert "下一问可覆盖的缺口字段" in instruction
    assert "不要问用户想先确认哪一项" in instruction
    assert "建议下一问" not in instruction


def test_brief_agent_instruction_does_not_expose_choice_template_question():
    agent_state = _agent_state_with(
        {
            "city_location": "杭州湖滨银泰in77 L型地标大屏",
            "viewing_path": "利用L型屏转角强化纵深感",
            "media_specs": "L型大屏，4K规格",
            "theme_concept": "四个宠物形象",
            "art_direction": "纵深感",
            "site_photos": "已上传图片素材",
        }
    )

    instruction = build_brief_agent_instruction(agent_state)

    assert "投放点位、现场观看关系或目标受众" not in instruction
    assert "您现在方便先确认哪一项" not in instruction
    assert "不要问用户想先确认哪一项" in instruction
    assert "直接问一个具体问题" in instruction


def test_brief_agent_adds_non_blocking_creative_evaluation_hint_once():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感大熊猫与商场环境互动",
            "art_direction": "治愈、柔软、有互动感",
            "city_location": "杭州湖滨银泰in77 L型地标大屏",
        }
    )

    instruction = build_brief_agent_instruction(agent_state)

    assert should_show_creative_evaluation_hint(agent_state) is True
    assert "非阻塞创意评估提醒" in instruction
    assert "如果用户已有自己的创意概念，可以随时发来做创意评估" in instruction
    assert "如果没有，后续也会基于当前 Brief 生成一版 AI 创意方向" in instruction
    assert "不要要求用户回答“有/没有”" in instruction
    assert "不要把下一问锁定为屏幕规格、交付时间或任何固定字段" in instruction

    shown_state = mark_creative_evaluation_hint_shown(agent_state)

    assert should_show_creative_evaluation_hint(shown_state) is False
    assert "非阻塞创意评估提醒" not in build_brief_agent_instruction(shown_state)


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
    assert "L型屏，4K" in hints["media_specs"]
    assert "budget" not in hints
    assert "online_time" not in hints
    assert "20w" not in str(hints)
    assert "下月初" not in str(hints)
    assert "上刊" not in str(hints)


def test_brief_memory_hints_can_list_multiple_candidates_for_one_field():
    memory = SimpleNamespace(
        screen_resources=[
            {
                "city": "杭州",
                "name": "湖滨银泰in77 L型大屏",
                "specs": "L型屏，4K",
            },
            {
                "city": "深圳",
                "name": "万象天地主广场大屏",
                "specs": "户外曲面屏，8K",
            },
        ],
        project_preferences={},
    )

    hints = build_brief_memory_hints(memory)

    assert "杭州 湖滨银泰in77 L型大屏" in hints["city_location"]
    assert "深圳 万象天地主广场大屏" in hints["city_location"]
    assert "L型屏，4K" in hints["media_specs"]
    assert "户外曲面屏，8K" in hints["media_specs"]


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

    assert next_question["category"] == "tech_delivery"
    assert "site_photos" in next_question["missing_fields"]
    assert "Brief 附件" not in next_question["question"]
    assert "作为 Brief" not in next_question["question"]


def test_brief_agent_sanitizer_observes_redundant_specs_question_without_rewriting_reply():
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

    assert sanitized == reply


def test_brief_agent_sanitizer_observes_template_question_without_rewriting_reply():
    agent_state = _agent_state_with(
        {
            "city_location": "杭州湖滨银泰in77 L型地标大屏",
            "viewing_path": "利用L型屏转角强化纵深感",
            "media_specs": "L型大屏，4K规格",
            "theme_concept": "四个宠物形象",
            "art_direction": "纵深感",
            "site_photos": "已上传图片素材",
        }
    )
    reply = (
        "纯艺术展示这个定位能让宠物形象少受品牌信息干扰，更适合做成地标屏上的治愈型视觉内容。\n\n"
        "基础信息这边，我想先补一个最影响判断的点：投放点位、现场观看关系或目标受众里，您现在方便先确认哪一项？"
    )

    sanitized = sanitize_brief_agent_reply(reply, agent_state)

    assert sanitized == reply


def test_brief_agent_does_not_override_pending_confirmation_question():
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

    assert sanitized == reply


def test_brief_agent_does_not_treat_lead_in_text_as_filled_field_question():
    agent_state = _agent_state_with(
        {
            "theme_concept": "毛绒质感的大熊猫",
            "city_location": "杭州湖滨银泰in77 L型地标大屏",
            "art_direction": "毛绒质感",
        }
    )
    agent_state["brief_state"]["pending_confirmation"] = {
        "id": "pending-specs",
        "field": "media_specs",
        "label": "屏幕规格",
        "candidate_value": "L型屏，100m x 70m，L型地标大屏",
        "source": "memory_candidate",
        "status": "pending",
    }
    reply = (
        "收到，已保存参考素材 hero.jpeg。\n\n"
        "点位方向我先记录。我们了解到这块屏幕大致是 L 型地标大屏，"
        "尺寸约 100m x 70m；这次先按这个规格来适配吗？如果参数有更新，也可以直接告诉我。"
    )

    sanitized = sanitize_brief_agent_reply(reply, agent_state)

    assert sanitized == reply
