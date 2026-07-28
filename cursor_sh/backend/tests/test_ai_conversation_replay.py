from pathlib import Path

from scripts.replay_ai_conversations import (
    DEFAULT_CASES_PATH,
    evaluate_expectations,
    load_replay_cases,
)


def test_replay_fixture_contains_unique_real_conversation_cases():
    cases = load_replay_cases(DEFAULT_CASES_PATH)

    assert len(cases) >= 5
    assert len({case["id"] for case in cases}) == len(cases)
    assert "duplicate_no_after_budget_keeps_photo_and_moves_on" in {
        case["id"] for case in cases
    }
    assert all(
        case.get("expected")
        or (
            case.get("kind") == "multi_turn_router"
            and isinstance(case.get("turns"), list)
            and all(turn.get("expected") for turn in case["turns"])
        )
        for case in cases
    )
    assert sum(case.get("kind") == "multi_turn_router" for case in cases) >= 3


def test_load_replay_cases_rejects_duplicate_ids(tmp_path: Path):
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"cases":[{"id":"same"},{"id":"same"}]}',
        encoding="utf-8",
    )

    try:
        load_replay_cases(path)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate replay ids should be rejected")


def test_evaluate_expectations_checks_route_brief_window_and_reply():
    result = {
        "route": {
            "action": "stay",
            "intent": "brief_building",
            "target_agent": "brief_agent",
        },
        "brief_fields": {
            "budget": "待定",
            "site_photos": "已上传图片素材：化妆品.png",
        },
        "window": [
            {"content": "没有"},
            {"content": "预算大概是多少？"},
            {"content": "没有"},
        ],
        "reply": "收到，我们继续确认投放目标。",
    }
    expected = {
        "route": {
            "target_agent": "brief_agent",
            "intent": "brief_building",
        },
        "brief_fields": {
            "budget": "待定",
            "site_photos": "已上传图片素材：化妆品.png",
        },
        "window_content_counts": {"没有": 2},
        "reply_forbidden_regex": ["预算.{0,8}(多少|范围)"],
    }

    assert evaluate_expectations(result, expected) == []


def test_evaluate_expectations_reports_human_readable_failures():
    failures = evaluate_expectations(
        {
            "route": {"target_agent": "brief_agent"},
            "brief_fields": {"budget": ""},
            "window": [{"content": "没有"}],
            "reply": "项目制作预算大概在什么范围？",
        },
        {
            "route": {"target_agent": "creative_direction_agent"},
            "brief_fields": {"budget": "待定"},
            "window_content_counts": {"没有": 2},
            "reply_forbidden_regex": ["预算.{0,16}(范围|多少|大概)"],
        },
    )

    assert any("route.target_agent" in item for item in failures)
    assert any("brief_fields.budget" in item for item in failures)
    assert any("window count" in item for item in failures)
    assert any("forbidden pattern" in item for item in failures)
