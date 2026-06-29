import pytest
from fastapi import HTTPException

from app.api import ai_creative_direction_agent as direction_module
from app.services.ai_image_understanding import IMAGE_CONTEXT_MARKER


@pytest.mark.asyncio
async def test_creative_direction_fallback_generates_draft_then_returns_to_brief(monkeypatch):
    monkeypatch.setattr(direction_module.settings, "AI_API_KEY", "")

    response = await direction_module.ai_creative_direction(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="根据上面的信息帮我生成一个创意方案",
            history=[
                {"role": "user", "content": "杭州核心商圈天幕，想做西湖主题裸眼3D内容，面向游客和年轻消费者"},
            ],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {
                    "fields": {
                        "city_location": {"value": "杭州核心商圈天幕"},
                        "audience_scene": {"value": "游客和年轻消费者"},
                        "theme_concept": {"value": "西湖主题裸眼3D内容"},
                    },
                    "readiness": {"level": "provisional", "score_confidence": "medium"},
                    "missing_fields": ["viewing_path", "media_specs", "content_review"],
                }
            },
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is True
    assert "创意方向草案" in message
    assert "创意方向名称" in message
    assert "计划概括" in message
    assert "适合的原因" in message
    assert "传播价值" in message
    assert "不是完整创意方案" in message
    assert "策划专家" in message
    assert "回到 Brief" not in message
    assert "Brief 附件" not in message
    assert "我先记录下来" not in message
    assert "【需求收集完成】" not in message


@pytest.mark.asyncio
async def test_creative_direction_agent_enables_thinking_with_long_timeout_and_strips_completion_marker(monkeypatch):
    captured_payload = {}
    captured_options = {}

    async def fake_post_chat_completion(payload, timeout, attempts=None):
        captured_payload.update(payload)
        captured_options["timeout"] = timeout
        captured_options["attempts"] = attempts
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "**创意方向草案**\n\n"
                            "- **创意方向名称**：未来折境\n\n"
                            "如果这个方向继续推进，预计上刊或交付时间大概是什么时候？\n\n"
                            "【需求收集完成】"
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(direction_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(direction_module.settings, "AI_HTTP_TIMEOUT", 30)
    monkeypatch.setattr(direction_module.settings, "AI_CREATIVE_DIRECTION_TIMEOUT", 120)
    monkeypatch.setattr(direction_module.settings, "AI_CREATIVE_DIRECTION_RETRY_ATTEMPTS", 1)
    monkeypatch.setattr(direction_module, "post_chat_completion", fake_post_chat_completion)

    response = await direction_module.ai_creative_direction(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="帮我生成一个创意方案",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {"theme_concept": {"value": "未来科技"}}}},
        )
    )

    assert captured_payload["enable_thinking"] is True
    assert captured_options["timeout"] == 120
    assert captured_options["attempts"] == 1
    assert captured_payload["messages"][0]["role"] == "system"
    assert response["return_to_brief"] is True
    assert "创意方向草案" in response["message"]
    assert "不是完整创意方案" in response["message"]
    assert "策划专家" in response["message"]
    assert response["message"].index("策划专家") < response["message"].index("预计上刊")
    assert "【需求收集完成】" not in response["message"]


@pytest.mark.asyncio
async def test_creative_direction_provider_timeout_returns_fallback(monkeypatch):
    async def fake_post_chat_completion(payload, timeout, attempts=None):
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后再试")

    monkeypatch.setattr(direction_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(direction_module, "post_chat_completion", fake_post_chat_completion)

    response = await direction_module.ai_creative_direction(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="靠着这个，你帮我生成一个创意方案",
            history=[],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {
                    "fields": {
                        "city_location": {"value": "杭州巨屏"},
                        "theme_concept": {"value": "毛绒质感的大熊猫，慵懒，与环境互动"},
                        "audience_scene": {"value": "商圈人流"},
                    }
                }
            },
        )
    )

    assert response["return_to_brief"] is True
    assert "创意方向草案" in response["message"]
    assert "熊猫" in response["message"]
    assert "不是完整创意方案" in response["message"]
    assert "策划专家" in response["message"]
    assert "回到 Brief" not in response["message"]
    assert "Brief 附件" not in response["message"]
    assert "我先记录下来" not in response["message"]


def test_creative_direction_prompt_bans_fixed_brief_return_phrasing():
    messages = direction_module.build_creative_direction_messages(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="帮我出个创意方案",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {"theme_concept": {"value": "毛绒大熊猫"}}}},
        )
    )

    system_prompt = messages[0]["content"]
    assert "回到 Brief" not in system_prompt
    assert "Brief 附件" not in system_prompt
    assert "我先记录下来" not in system_prompt


def test_creative_direction_prompt_requires_image_feedback_before_draft():
    messages = direction_module.build_creative_direction_messages(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message=(
                "就这个图片做创意\n\n"
                f"{IMAGE_CONTEXT_MARKER}\n"
                "图片类型：参考设计/风格图\n"
                "视觉摘要：画面是一只毛绒质感大熊猫。"
            ),
            history=[],
            business_type="ai_3d_custom",
        )
    )

    system_prompt = messages[0]["content"]
    assert "图片上传后的用户可见反馈" in system_prompt
    assert "创意方向草案" in system_prompt
    assert "先从这张参考图里抓到几个方向" in system_prompt
