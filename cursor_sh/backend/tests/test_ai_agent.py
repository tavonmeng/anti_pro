import pytest
from starlette.requests import Request

from app.api import ai as ai_module


def _request_without_auth() -> Request:
    return Request({"type": "http", "headers": []})


class _FakeUser:
    id = "user-test"
    username = "测试用户"


def _fake_user() -> _FakeUser:
    return _FakeUser()


async def _no_existing_handoff(**_):
    return None


async def _mock_record_handoff(**_):
    return {"handoff_id": "handoff-test", "draft_order_id": "order-test", "is_new": True}


async def _mock_existing_handoff(**_):
    return {"handoff_id": "handoff-test", "draft_order_id": "order-test", "is_new": False}


@pytest.mark.asyncio
async def test_ai_chat_returns_mock_reply_without_ai_key(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我们想做一个成都太古里的裸眼3D项目",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "message" in response
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_mock_completion_uses_frontend_completion_marker(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="没问题，需求已经完成",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_mock_completion_ignores_negative_completion_text(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="还没完成，预算和上线时间还不确定",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_handoff_request_stops_requirement_collection(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)
    monkeypatch.setattr(ai_module, "_record_handoff", _mock_record_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我不想用 AI 智能体了，帮我转人工顾问",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert response["handoff"] is True
    assert response["draft_order_id"] == "order-test"
    assert "专属顾问" in response["message"]
    assert "【需求收集完成】" not in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_handoff_negative_phrase_does_not_trigger(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="先不转人工，我继续补充需求",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert response.get("handoff") is not True
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_start_media_ai_3d_custom_uses_opening_question(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    response = await ai_module.ai_start("test-session", "ai_3d_custom")

    assert "这次大概想做什么样的内容" in response["reply"]
    assert "请先告诉我品牌或项目名称" not in response["reply"]
    assert "请先告诉我项目名称" not in response["reply"]


@pytest.mark.asyncio
async def test_ai_start_orderable_businesses_do_not_force_first_field(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    for business_type in ["ai_3d_custom", "video_purchase", "digital_art"]:
        response = await ai_module.ai_start("test-session", business_type)
        assert "请先告诉我" not in response["reply"]
        assert "这次" in response["reply"]


@pytest.mark.asyncio
async def test_ai_chat_handoff_does_not_match_artificial_intelligence(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我们想做人工智能主题的裸眼3D内容",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert response.get("handoff") is not True
    assert "收到您的反馈" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_existing_handoff_appends_followup(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _mock_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="补充一下，我们预算大概50万",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert response["handoff"] is True
    assert response["is_new"] is False
    assert "追加到人工对接记录" in response["message"]
    assert "【需求收集完成】" not in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_strips_early_completion_without_upload_wrapup(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        assert timeout == 120
        return {
            "choices": [
                {
                    "message": {
                        "content": "需求已经足够，我来整理。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module.settings, "AI_HTTP_TIMEOUT", 120)
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="下个月月底",
            history=[
                {"role": "user", "content": "我想在杭州天幕巨屏投放3D视频"},
                {"role": "assistant", "content": "面向什么受众？"},
                {"role": "user", "content": "面向游客宣传"},
                {"role": "assistant", "content": "主题是什么？"},
                {"role": "user", "content": "杭州西湖美景"},
                {"role": "assistant", "content": "风格怎么呈现？"},
                {"role": "user", "content": "写意的传统意境"},
                {"role": "assistant", "content": "需要哪些元素？"},
                {"role": "user", "content": "西湖标志性景观"},
                {"role": "assistant", "content": "时长多少？"},
                {"role": "user", "content": "30s"},
                {"role": "assistant", "content": "技术要求？"},
                {"role": "user", "content": "没有特定要求"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "现场实拍图" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_strips_completion_when_signal_coverage_is_too_low(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "信息已经足够，我来整理。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="都可以",
            history=[
                {"role": "user", "content": "想做一个项目"},
                {"role": "assistant", "content": "大概是什么内容？"},
                {"role": "user", "content": "宣传一下"},
                {"role": "assistant", "content": "投放在哪里？"},
                {"role": "user", "content": "还没定"},
                {"role": "assistant", "content": "受众是谁？"},
                {"role": "user", "content": "大众"},
                {"role": "assistant", "content": "创意方向呢？"},
                {"role": "user", "content": "好看就行"},
                {"role": "assistant", "content": "规格有吗？"},
                {"role": "user", "content": "不清楚"},
                {"role": "assistant", "content": "上线时间呢？"},
                {"role": "user", "content": "之后再说"},
                {"role": "assistant", "content": "有素材吗？"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "投放点位或屏幕规格" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_does_not_repeat_answered_fallback_after_user_answer(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "我先按当前信息整理。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="杭州",
            history=[
                {"role": "user", "content": "想做一个项目"},
                {"role": "assistant", "content": "大概是什么内容？"},
                {"role": "user", "content": "宣传一下"},
                {
                    "role": "assistant",
                    "content": (
                        "我还需要再补充一个关键信息：这次项目对应的投放点位或屏幕规格目前方便确认吗？"
                        "如果暂时没有完整参数，先说城市、屏幕位置或已有规格也可以。"
                    ),
                },
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert response["message"].count("投放点位或屏幕规格") == 0


@pytest.mark.asyncio
async def test_media_ai_chat_does_not_repeat_answered_theme_fallback(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "我先按当前信息整理。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="还没确定",
            history=[
                {"role": "user", "content": "杭州大屏，规格大概 3000x1000，想做个项目"},
                {
                    "role": "assistant",
                    "content": "这项我先记录为待确认。为了继续推进，想再确认这次主要想做什么内容或主题？",
                },
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "主要想做什么内容或主题" not in response["message"]
    assert "哪类人群或观看场景" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_dense_summary_asks_assets_instead_of_repeating_specs(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "好的，核心信息已基本梳理完整。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    dense_summary = (
        "项目需求汇总\n\n"
        "媒体点位：杭州湖滨银泰in77 L型巨屏\n"
        "物理规格：宽 100m x 高 70m，L型结构，4K分辨率\n"
        "内容主题：西湖美景，以雷峰塔为核心视觉主体\n"
        "艺术风格：写实细腻的3D渲染，强调地标质感与空间纵深\n"
        "创意方向：利用L型转角构建透视，展现雷峰塔破屏而出的视觉冲击\n"
        "目标受众：年轻群体、游客及商圈人流\n"
        "技术交付：MP4/MOV，30fps，Rec.709/sRGB，预留安全区\n"
        "项目预算：20万左右\n"
        "时间节点：下个月底交付，预计上刊时间为下月15号左右"
    )

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="杭州",
            history=[
                {"role": "assistant", "content": dense_summary},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert "现场实拍图" in response["message"]
    assert "投放点位或屏幕规格" not in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_removes_redundant_specs_followup_from_same_reply(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "好的，结合我们之前的沟通，这次项目是针对杭州湖滨银泰in77的L型巨屏。"
                            "目前核心信息已基本梳理完毕：\n\n"
                            "需求确认清单\n\n"
                            "媒体点位：杭州湖滨银泰in77 L型巨屏（100m x 70m）\n"
                            "内容主题：西湖美景，雷峰塔为核心视觉\n"
                            "艺术风格：写实细腻3D，强调破屏纵深与沉浸感\n"
                            "预算范围：20万左右\n"
                            "交付时间：下个月底\n"
                            "视频时长：30秒\n"
                            "若后续有现场实拍图或更具体的审核规范，可随时补充。我们将按此方向推进方案深化。\n\n"
                            "我还需要再补充一个关键信息：这次项目对应的投放点位或屏幕规格目前方便确认吗？"
                            "如果暂时没有完整参数，先说城市、屏幕位置或已有规格也可以。"
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="屏幕在杭州",
            history=[
                {"role": "user", "content": "杭州湖滨银泰in77 L型巨屏，100m x 70m，想做西湖雷峰塔裸眼3D。"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "杭州湖滨银泰in77 L型巨屏" in response["message"]
    assert "投放点位或屏幕规格" not in response["message"]
    assert "现场实拍图" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_allows_no_more_assets_to_complete(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "好的，我按当前信息整理需求。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="没有了",
            history=[
                {
                    "role": "user",
                    "content": (
                        "杭州湖滨银泰in77 L型巨屏，100m x 70m，4K，做西湖雷峰塔破屏裸眼3D，"
                        "面向游客和年轻人，预算20万，下个月底交付，MP4/MOV，30fps，Rec.709。"
                    ),
                },
                {
                    "role": "assistant",
                    "content": "核心信息已基本收集完毕。您这边是否有现场实拍图、屏幕照片或其他参考素材可以上传？",
                },
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_allows_user_driven_early_wrap_up(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "我先按当前信息整理，缺失项后续可补充。【需求收集完成】"
                    }
                }
            ]
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="先这样，直接帮我整理吧",
            history=[
                {"role": "user", "content": "杭州天幕屏，想做西湖主题裸眼3D内容"},
                {"role": "assistant", "content": "大概面向谁？"},
                {"role": "user", "content": "游客和商场客流"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" in response["message"]


@pytest.mark.asyncio
async def test_ai_chat_stream_qwen_uses_chat_completions_without_responses_probe(monkeypatch):
    async def _unexpected_responses_stream(*_, **__):
        raise AssertionError("Qwen stream should not probe the Responses API")
        yield ""

    async def _mock_chat_stream_events(payload, *, timeout=None):
        assert payload["model"] == "qwen3.6-plus"
        assert payload["messages"][-1]["content"] == "我想做一个裸眼3D项目"
        assert timeout == 120
        yield {"type": "content", "content": "好的"}
        yield {"type": "content", "content": "，请问计划投放在哪个城市？"}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(ai_module.settings, "AI_RESPONSES_BASE_URL", "")
    monkeypatch.setattr(ai_module.settings, "AI_PREFER_RESPONSES_API", False)
    monkeypatch.setattr(ai_module.settings, "AI_MODEL_NAME", "qwen3.6-plus")
    monkeypatch.setattr(ai_module.settings, "AI_HTTP_TIMEOUT", 120)
    monkeypatch.setattr(ai_module, "stream_responses_completion", _unexpected_responses_stream)
    monkeypatch.setattr(ai_module, "stream_chat_completion_events", _mock_chat_stream_events)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat_stream(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我想做一个裸眼3D项目",
            history=[],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    body = "".join(chunks)

    assert "event: delta" in body
    assert "chat_completions" in body
    assert "请问计划投放在哪个城市" in body


@pytest.mark.asyncio
async def test_qwen_chat_payload_disables_thinking_by_default(monkeypatch):
    from app.services import ai_client

    monkeypatch.setattr(ai_client.settings, "AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(ai_client.settings, "AI_MODEL_NAME", "qwen3.6-plus")
    monkeypatch.setattr(ai_client.settings, "AI_ENABLE_THINKING", False)

    payload = ai_client._prepare_chat_payload({"model": "qwen3.6-plus", "messages": []})

    assert payload["enable_thinking"] is False


def test_design_thinking_only_for_creative_plan_requests():
    assert ai_module._should_enable_design_thinking("帮我生成一个设计方案")
    assert ai_module._should_enable_design_thinking("根据上面的信息写一版策划方案")
    assert ai_module._should_enable_design_thinking("出个创意方案给客户看")
    assert ai_module._should_enable_design_thinking("能不能给我出一个方案")
    assert ai_module._should_enable_design_thinking("帮我做一版方案")

    assert not ai_module._should_enable_design_thinking("这个能不能做")
    assert not ai_module._should_enable_design_thinking("排期多久")
    assert not ai_module._should_enable_design_thinking("报价方案大概怎么定")
    assert not ai_module._should_enable_design_thinking("怎么落地执行")


def test_design_thinking_for_creative_draft_revision_requests():
    history = [
        {"role": "user", "content": "根据上面的信息帮我生成一个创意方案"},
        {
            "role": "assistant",
            "content": "创意方向名称：西湖未来折叠\n\n计划概括：...\n\n适合的原因：...\n\n传播价值：...",
        },
    ]

    assert ai_module._should_enable_design_thinking("不太满意，能不能更科技一点", history)
    assert ai_module._should_enable_design_thinking("换一个更年轻的方向", history)


def test_revision_words_without_recent_creative_draft_do_not_enable_thinking():
    assert not ai_module._should_enable_design_thinking("不太满意，能不能更科技一点", [])


def test_creative_plan_request_injects_direction_draft_rules(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="根据上面的信息帮我生成一个创意方案",
            history=[{"role": "user", "content": "我们想做杭州西湖主题的裸眼3D内容"}],
        )
    )

    system_prompt = messages[0]["content"]
    assert "创意方向草案" in system_prompt
    assert "创意方向名称" in system_prompt
    assert "计划概括" in system_prompt
    assert "适合的原因" in system_prompt
    assert "传播价值" in system_prompt
    assert "不要输出完整分镜脚本" in system_prompt
    assert "0-5s/5-15s/15-25s" in system_prompt
    assert "完整创意方案需要结合屏幕参数" in system_prompt
    assert "项目顾问和策划团队继续深化" in system_prompt
    assert "转入当前需求梳理" in system_prompt


def test_creative_revision_request_injects_direction_draft_rules(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="不满意，换一个更科技的方向",
            history=[
                {"role": "user", "content": "帮我生成一个创意方案"},
                {"role": "assistant", "content": "创意方向名称：水墨西湖\n\n计划概括：...\n\n传播价值：..."},
            ],
        )
    )

    system_prompt = messages[0]["content"]
    assert "修订方向草案" in system_prompt
    assert "项目顾问和策划团队继续深化" in system_prompt


def test_non_creative_plan_request_does_not_inject_direction_draft_rules(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="这个项目排期多久",
            history=[],
        )
    )

    assert "创意方向草案" not in messages[0]["content"]
