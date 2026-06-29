from types import SimpleNamespace

from app.services.memory_service import (
    _merge_preferences,
    _normalize_conversation_screens,
    _sanitize_memory_record_for_reuse,
    build_memory_context,
)


def test_memory_context_does_not_expose_reusable_budget_or_online_time():
    memory = SimpleNamespace(
        company_info={},
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
            "preferred_styles": ["毛绒质感"],
            "budget_range": "20w",
            "online_time": "下月初上刊",
            "notes": "客户上次预算20w，下月初上刊；喜欢治愈风格",
        },
        past_projects=[],
        agent_notes="上次预算20w；下月初上刊；偏好毛绒质感",
    )

    context = build_memory_context(memory)

    assert "杭州" in context
    assert "毛绒质感" in context
    assert "20w" not in context
    assert "预算范围" not in context
    assert "预算20w" not in context
    assert "下月初" not in context
    assert "上刊" not in context


def test_memory_learning_merge_drops_budget_and_online_time_fields():
    merged = _merge_preferences(
        {"preferred_styles": ["写实"]},
        {
            "preferred_styles": ["毛绒质感"],
            "budget_range": "20w",
            "online_time": "下月初上刊",
            "notes": "客户预算20w；下月初上刊；偏好治愈风格",
        },
    )

    assert merged["preferred_styles"] == ["写实", "毛绒质感"]
    assert "budget_range" not in merged
    assert "online_time" not in merged
    assert "20w" not in str(merged)
    assert "下月初" not in str(merged)
    assert "上刊" not in str(merged)
    assert "偏好治愈风格" in merged["notes"]


def test_conversation_screen_notes_drop_sensitive_project_schedule_and_budget():
    screens = _normalize_conversation_screens(
        [
            {
                "city": "杭州",
                "name": "湖滨银泰in77 L型大屏",
                "specs": "L型屏，4K",
                "notes": "主入口正面观看；下月初上刊；预算20w",
            }
        ]
    )

    assert screens[0]["notes"] == "主入口正面观看"
    assert "20w" not in str(screens)
    assert "下月初" not in str(screens)
    assert "上刊" not in str(screens)


def test_sanitize_memory_record_removes_legacy_sensitive_project_fields():
    memory = SimpleNamespace(
        project_preferences={
            "preferred_styles": ["毛绒质感"],
            "budget_range": "20w",
            "online_time": "下月初上刊",
            "notes": "预算20w；下月初上刊；偏好治愈风格",
            "_field_updated": {
                "budget_range": "2026-06-01",
                "online_time": "2026-06-01",
                "preferred_styles": "2026-06-01",
            },
        },
        screen_resources=[
            {
                "city": "杭州",
                "name": "湖滨银泰in77 L型大屏",
                "notes": "主入口正面观看；下月初上刊；预算20w",
            }
        ],
        agent_notes="预算20w；下月初上刊；偏好毛绒质感",
    )

    changed = _sanitize_memory_record_for_reuse(memory)

    assert changed is True
    assert memory.project_preferences["preferred_styles"] == ["毛绒质感"]
    assert memory.project_preferences["notes"] == "偏好治愈风格"
    assert "budget_range" not in memory.project_preferences
    assert "online_time" not in memory.project_preferences
    assert memory.project_preferences["_field_updated"] == {"preferred_styles": "2026-06-01"}
    assert memory.screen_resources[0]["notes"] == "主入口正面观看"
    assert memory.agent_notes == "偏好毛绒质感"
    assert "20w" not in str(memory.project_preferences)
    assert "下月初" not in str(memory.screen_resources)
    assert "上刊" not in memory.agent_notes
