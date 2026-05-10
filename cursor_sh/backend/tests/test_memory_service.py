from app.models.user_memory import UserMemory
from app.services import memory_service
from app.services.memory_service import build_memory_context


def test_build_memory_context_includes_usage_rules_and_advisor_cues():
    memory = UserMemory(
        user_id="user-1",
        company_info={
            "name": "测试传媒",
            "description": "专注核心商圈户外媒体运营",
            "advantages": ["核心商圈", "高客流"],
            "crawled_at": "2026-05-01T12:00:00",
        },
        screen_resources=[
            {
                "city": "成都",
                "location": "春熙路",
                "type": "L型LED",
                "resolution": "3840x2160",
                "last_seen_at": "2026-05-02T12:00:00",
            },
        ],
        project_preferences={
            "common_cities": ["成都"],
            "preferred_styles": ["未来科技"],
            "budget_range": "30-60万",
        },
        past_projects=[
            {"project_name": "春熙路裸眼3D项目", "city": "成都", "status": "completed"},
        ],
        agent_notes="客户偏好高效沟通。",
    )

    context = build_memory_context(memory)

    assert "【客户记忆使用规则】" in context
    assert "当前结构化需求状态优先于历史记忆" in context
    assert "【顾问线索：客户背景】" in context
    assert "信息时间：2026-05-01" in context
    assert "【顾问线索：已知屏幕资源" in context
    assert "更新时间2026-05-02" in context
    assert "不要默认选用" in context
    assert "【顾问线索：历史偏好" in context


def test_build_memory_context_limits_screen_resources():
    memory = UserMemory(
        user_id="user-1",
        screen_resources=[
            {"city": f"城市{i}", "location": f"点位{i}"}
            for i in range(7)
        ],
    )

    context = build_memory_context(memory)

    assert "城市0" in context
    assert "城市4" in context
    assert "城市5" not in context
    assert "另有 2 块资源未展开" in context


def test_memory_stamp_helpers_keep_compatible_shapes():
    company = memory_service._stamp_company_info(
        {"name": "测试传媒", "crawl_status": "success"},
        "2026-05-10T12:00:00",
    )
    screens = memory_service._stamp_screen_resources(
        [{"city": "成都", "location": "春熙路"}],
        "2026-05-10T12:00:00",
    )
    preferences = memory_service._stamp_project_preferences(
        {"budget_range": "30-60万"},
        "2026-05-10T12:00:00",
    )

    assert company["updated_at"] == "2026-05-10T12:00:00"
    assert company["crawled_at"] == "2026-05-10T12:00:00"
    assert isinstance(screens, list)
    assert screens[0]["first_seen_at"] == "2026-05-10T12:00:00"
    assert screens[0]["last_seen_at"] == "2026-05-10T12:00:00"
    assert preferences["last_updated"] == "2026-05-10T12:00:00"


def test_screen_resource_stamp_preserves_first_seen_for_existing_resource():
    screens = memory_service._stamp_screen_resources(
        [{"city": "成都", "location": "春熙路", "type": "L型LED"}],
        "2026-05-10T12:00:00",
        [{"city": "成都", "location": "春熙路", "type": "L型LED", "first_seen_at": "2026-05-01T12:00:00"}],
    )

    assert screens[0]["first_seen_at"] == "2026-05-01T12:00:00"
    assert screens[0]["last_seen_at"] == "2026-05-10T12:00:00"
