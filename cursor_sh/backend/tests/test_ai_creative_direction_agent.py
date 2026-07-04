import pytest
import json
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
            agent_state={
                "brief_state": {
                    "fields": {
                        "city_location": {"value": "杭州核心商圈L型大屏"},
                        "audience_scene": {"value": "年轻消费者和游客"},
                        "theme_concept": {"value": "未来科技"},
                    },
                    "readiness": {"level": "provisional"},
                }
            },
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
async def test_creative_direction_outputs_low_confidence_draft_when_brief_is_sparse(monkeypatch):
    monkeypatch.setattr(direction_module.settings, "AI_API_KEY", "")

    response = await direction_module.ai_creative_direction(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="想做一个3D视频，先帮我梳理一下大概方向。",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}, "readiness": {"level": "insufficient"}}},
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is True
    assert response.get("needs_brief") is not True
    assert "创意方向草案" in message
    assert "低置信度" in message
    assert "信息不足" in message
    assert "不是完整创意方案" in message
    assert "当前点位" not in message
    assert "本次主题" not in message


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


@pytest.mark.asyncio
async def test_creative_direction_image_based_request_without_image_context_does_not_invent(monkeypatch):
    async def fake_image_summary(*_, **__):
        return ""

    async def fake_post_chat_completion(*_, **__):
        raise AssertionError("image-based creative direction should not call text LLM without image context")

    monkeypatch.setattr(direction_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(direction_module, "summarize_uploaded_images", fake_image_summary)
    monkeypatch.setattr(direction_module, "post_chat_completion", fake_post_chat_completion)

    response = await direction_module.ai_creative_direction(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}, "readiness": {"level": "insufficient"}}},
            attachments=[
                direction_module.UploadedAttachment(
                    name="reference.png",
                    url="/uploads/site_photos/user-test/reference.png",
                    type="image/png",
                    isImage=True,
                    size=128,
                )
            ],
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is False
    assert response["agent_state"]["pending_creative_direction"]["status"] == "awaiting_image_context"
    assert "没有稳定拿到图片内容" in message
    assert "不先基于文件名" in message
    assert "创意方向草案" not in message


@pytest.mark.asyncio
async def test_creative_direction_image_based_request_without_attachment_does_not_claim_received(monkeypatch):
    async def fake_post_chat_completion(*_, **__):
        raise AssertionError("image-based request without an attachment should not call text LLM")

    monkeypatch.setattr(direction_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(direction_module, "post_chat_completion", fake_post_chat_completion)

    response = await direction_module.ai_creative_direction(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="我想基于上传的图片做一些创意延展，请先告诉我可以从哪些方向展开。",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}, "readiness": {"level": "insufficient"}}},
            attachments=[],
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is False
    assert response["agent_state"]["pending_creative_direction"]["status"] == "awaiting_image"
    assert response["agent_state"]["current_agent"] == "creative_direction_agent"
    assert "还没有看到这轮消息里有图片附件" in message
    assert "我已经收到" not in message
    assert "创意方向草案" not in message


def test_creative_direction_boundary_note_not_duplicated_for_equivalent_llm_boundary():
    message = (
        "**创意方向草案**\n\n"
        "边界说明：当前内容仅为初步的创意方向草案，并非完整的创意方案。"
        "具体方案还需要策划专家结合屏幕参数、现场观看动线和审核规范继续深化。"
    )

    result = direction_module._ensure_boundary_note(message)

    assert result.count("边界说明") == 1
    assert result.count("创意方向草案") == 2


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


def test_creative_direction_prompt_supports_low_confidence_output_when_brief_is_sparse():
    messages = direction_module.build_creative_direction_messages(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="帮我出一个创意方向",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}, "readiness": {"level": "insufficient"}}},
        )
    )

    system_prompt = messages[0]["content"]
    payload = json.loads(messages[1]["content"])
    assert payload["creative_direction_confidence"] == "low"
    assert "低置信度" in system_prompt
    assert "不要编造具体点位、角色、预算或上刊时间" in system_prompt


def test_creative_direction_prompt_uses_agent_context_window_when_available():
    raw_long_history = "原始超长创意方向内容。" * 80
    messages = direction_module.build_creative_direction_messages(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="基于刚才那版再出一个方向",
            history=[{"role": "assistant", "content": raw_long_history}],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {"fields": {}, "readiness": {"level": "insufficient"}},
                "agent_context_window": {
                    "messages": [
                        {"role": "assistant", "content": "压缩摘要：毛绒大熊猫从L型屏探出，与路人互动。"}
                    ]
                },
            },
        )
    )

    payload = json.loads(messages[1]["content"])
    history_text = json.dumps(payload["recent_history"], ensure_ascii=False)
    assert "压缩摘要：毛绒大熊猫从L型屏探出" in history_text
    assert "原始超长创意方向内容" not in history_text


def test_creative_direction_prompt_supports_revision_after_evaluation():
    messages = direction_module.build_creative_direction_messages(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message="你能不能优化一下",
            history=[
                {"role": "user", "content": "创意概念：水滴凝结成瓶，冰晶沿L型屏曲面飞散。"},
                {"role": "assistant", "content": "阶段性创意评估：风险点是品牌识别滞后，优化方向是前置品牌资产。"},
            ],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {
                    "fields": {
                        "theme_concept": {"value": "水滴凝结成怡宝瓶"},
                        "city_location": {"value": "杭州湖滨银泰 in77 L型地标大屏"},
                    },
                    "readiness": {"level": "provisional"},
                }
            },
        )
    )

    system_prompt = messages[0]["content"]
    assert "不要把优化请求回答成创意评估" in system_prompt
    assert "创意方向优化稿" in system_prompt
    assert "优先解决评估中指出的风险点" in system_prompt
    assert "不是完整创意方案" in system_prompt


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
    assert "必须直接围绕图片理解摘要里的可见主体、风格质感、场景关系做延展" in system_prompt
    assert "不要按平台业务类型分类" in system_prompt


def test_creative_direction_prompt_prefers_current_image_message_over_router_context():
    messages = direction_module.build_creative_direction_messages(
        direction_module.CreativeDirectionRequest(
            session_id="session-test",
            message=(
                "基于这张图做创意延展\n\n"
                f"{IMAGE_CONTEXT_MARKER}\n"
                "图片类型：参考设计/风格图\n"
                "视觉摘要：画面是一只毛绒质感大熊猫。"
            ),
            history=[],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {"fields": {}, "readiness": {"level": "insufficient"}},
                "agent_context_window": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "基于这张图做创意延展",
                            "source_message_id": "user-msg-1",
                        }
                    ]
                },
            },
        )
    )

    payload = json.loads(messages[1]["content"])
    assert IMAGE_CONTEXT_MARKER in payload["current_user_message"]
    assert "毛绒质感大熊猫" in payload["current_user_message"]
