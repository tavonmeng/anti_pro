import pytest

from app.api import ai_intro_agent as intro_module


def test_order_entry_reply_for_ai_custom_uses_opening_question():
    reply = intro_module._build_order_entry_reply("ai_3d_custom", "意向AI驱动3D OOH内容定制")

    assert "这次大概想做什么样的内容" in reply
    assert "品牌或项目名称" not in reply
    assert "项目基础信息开始" not in reply


def test_order_entry_reply_for_orderable_businesses_do_not_force_first_field():
    for business_type in ["ai_3d_custom", "video_purchase", "digital_art"]:
        reply = intro_module._build_order_entry_reply(business_type)
        assert "品牌或项目名称" not in reply
        assert "请先告诉我" not in reply
        assert "这次" in reply


def test_case_request_uses_consultant_reply():
    reply = intro_module._build_case_consultant_reply()

    assert "线上暂不展示公开案例" in reply
    assert "咨询顾问" in reply


@pytest.mark.asyncio
async def test_business_intro_case_request_returns_no_cases(monkeypatch):
    monkeypatch.setattr(intro_module.settings, "AI_API_KEY", "")

    response = await intro_module.ai_business_intro(
        intro_module.BusinessIntroRequest(message="想看看你们之前做过的案例", history=[])
    )

    assert response["cases"] == []
    assert "咨询顾问" in response["message"]
