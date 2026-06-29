import pytest

from app.api import ai_intro_agent as intro_module


def test_order_entry_reply_for_ai_custom_uses_opening_question():
    reply = intro_module._build_order_entry_reply("ai_3d_custom", "意向AI驱动3D OOH内容定制")

    assert "这次大概想做什么样的内容" in reply
    assert "品牌或项目名称" not in reply
    assert "项目基础信息开始" not in reply


def test_order_entry_reply_with_requirement_summary_continues_to_next_gap():
    reply = intro_module._build_order_entry_reply("ai_3d_custom", "毛绒质感动物，与环境互动并冲出屏幕")

    assert "毛绒质感动物，与环境互动并冲出屏幕" in reply
    assert "这次大概想做什么样的内容" not in reply
    assert "大概想做成什么样" not in reply
    assert "屏幕或场景" in reply


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


@pytest.mark.asyncio
async def test_first_3d_custom_intro_reply_is_soft_single_question(monkeypatch):
    monkeypatch.setattr(intro_module.settings, "AI_API_KEY", "")

    response = await intro_module.ai_business_intro(
        intro_module.BusinessIntroRequest(message="我想了解一下3D视频定制需求", history=[])
    )

    message = response["message"]
    assert "先简单聊聊" in message
    assert "大概想做成什么样" in message
    assert message.count("？") <= 1
    assert "AI-Based Creative Development" not in message
    assert "品牌名称" not in message
    assert "投放城市" not in message
    assert "屏幕位置" not in message
    assert "风格偏好" not in message


@pytest.mark.asyncio
async def test_llm_intro_prompt_keeps_first_3d_custom_reply_low_pressure(monkeypatch):
    captured_messages = []

    async def fake_post_chat_completion(payload, timeout):
        captured_messages.extend(payload["messages"])
        return {"choices": [{"message": {"content": "可以，先简单聊聊。您这次大概想做成什么样的3D视频？"}}]}

    monkeypatch.setattr(intro_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(intro_module, "post_chat_completion", fake_post_chat_completion)

    await intro_module.ai_business_intro(
        intro_module.BusinessIntroRequest(message="针对3D视频定制需求", history=[])
    )

    system_prompt = captured_messages[0]["content"]
    assert "第一次回答" in system_prompt
    assert "只问一个" in system_prompt
    assert "不要一次性索要品牌名称、投放城市、屏幕位置、视频主题或风格偏好" in system_prompt


@pytest.mark.asyncio
async def test_business_intro_guide_reply_does_not_restart_opening_question(monkeypatch):
    async def fake_post_chat_completion(payload, timeout):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "这个方向适合继续梳理。\n"
                            "【引导下单:ai_3d_custom:毛绒质感动物，与环境互动并冲出屏幕】"
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(intro_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(intro_module, "post_chat_completion", fake_post_chat_completion)

    response = await intro_module.ai_business_intro(
        intro_module.BusinessIntroRequest(
            message="与周围环境进行互动，然后冲出屏幕",
            history=[
                {"role": "user", "content": "2"},
                {"role": "assistant", "content": "可以，先简单聊聊。您这次大概想做成什么样的3D视频？"},
                {"role": "user", "content": "想做一个毛绒质感的动物"},
                {"role": "assistant", "content": "希望这只动物呈现什么样的动态或互动情节？"},
            ],
        )
    )

    assert response["guide"]["should_guide"] is True
    assert response["guide"]["business_type"] == "ai_3d_custom"
    assert response["guide"]["requirement_summary"] == "毛绒质感动物，与环境互动并冲出屏幕"
    assert "这次大概想做什么样的内容" not in response["message"]
    assert "屏幕或场景" in response["message"]
