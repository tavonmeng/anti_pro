import pytest
from starlette.requests import Request
from types import SimpleNamespace

from app.api import ai as ai_module


@pytest.fixture(autouse=True)
def _isolate_ai_agent_state(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_module.settings, "LOG_DIR", str(tmp_path))


def _request_without_auth() -> Request:
    return Request({"type": "http", "headers": []})


class _FakeUser:
    id = "user-test"
    username = "测试用户"


def _fake_user() -> _FakeUser:
    return _FakeUser()


def test_requirement_prompt_keeps_goal_on_brief_form_and_order_confirmation():
    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="这个创意方向可以吗？",
            history=[],
            business_type="ai_3d_custom",
        )
    )
    system_prompt = messages[0]["content"]

    assert "创意提案总监" in system_prompt
    assert "Brief" in system_prompt
    assert "表单" in system_prompt
    assert "确认下单" in system_prompt
    assert "创意评估" in system_prompt
    assert "评估完成后" in system_prompt
    assert "Brief 固定围绕三大类收集：基础信息、创意方向以及技术与交付" in system_prompt
    assert "总体顺序是基础信息 → 创意方向 → 技术与交付" in system_prompt
    assert "不要按固定字段逐项盘问" in system_prompt
    assert "按信息复杂度" in system_prompt
    assert "关键 Brief 信息" in system_prompt
    assert "不要为了显得专业而写成小报告" in system_prompt
    assert "1-2 句" not in system_prompt
    assert "专业判断" in system_prompt
    assert "不是每轮必须" in system_prompt
    assert "不要只做机械确认" in system_prompt
    assert "承接必须优先回应用户最新输入" in system_prompt
    assert "不要复述上一轮 assistant 的专业判断" in system_prompt
    assert "避免连续使用同一种过渡句式" in system_prompt
    assert "信息密度较高" in system_prompt
    assert "至少两个短段落" in system_prompt
    assert "最后一个问题单独成段" in system_prompt
    assert "每轮最多推进一个需要用户回答的任务" in system_prompt
    assert "不按句子数或问号数判断" in system_prompt
    assert "分别提供两类信息、作出两个决定" in system_prompt
    assert "按用户需要完成的回答动作判断" in system_prompt
    assert "用户读完后是否只需要决定、确认或说明一件事" in system_prompt
    assert "只保留与当前上下文最相关、优先级最高的一问" in system_prompt
    assert "同一轮追加第二个独立追问" in system_prompt
    assert "少量加粗关键事实或关键判断" in system_prompt
    assert "凡是会进入 Brief 的内容信息都属于重点信息" in system_prompt
    assert "只加粗具体 Brief 内容" in system_prompt
    assert "不加粗模板词" in system_prompt
    assert "如果只是短答确认或简单追问，可以不加粗" not in system_prompt
    assert "只有纯确认或一句话短追问可以不加粗" in system_prompt
    assert "同时承担解释、判断和引导" in system_prompt
    assert "阅读锚点" in system_prompt
    assert "每轮最多加粗 1 处" not in system_prompt
    assert "不要每轮都使用固定标题" in system_prompt
    assert "可以偶尔用" not in system_prompt
    assert "不要每轮都说" not in system_prompt


@pytest.mark.asyncio
async def test_requirement_reply_generation_uses_same_latest_budget_window(monkeypatch):
    long_previous_user_message = "此前的项目补充。" + ("这是一段较早的详细上下文。" * 100) + "此前补充结束。"
    long_budget_question = (
        "已确认收到化妆品.png。" + ("这是与项目预算相关的专业分析。" * 100)
        + "项目制作预算大概在什么范围？"
    )

    async def _mock_context_compactor(payload, *, timeout=None, attempts=None):
        return {"choices": [{"message": {"content": "压缩的较早上下文"}}]}

    monkeypatch.setattr("app.services.ai_context.settings.AI_API_KEY", "test-key")
    monkeypatch.setattr("app.services.ai_context.post_chat_completion", _mock_context_compactor)
    history = [
        {"client_message_id": "user-earlier", "role": "user", "content": long_previous_user_message},
        {"client_message_id": "assistant-photo", "role": "assistant", "content": "您手头有现场实拍图吗？"},
        {"client_message_id": "user-photo", "role": "user", "content": "没有"},
        {
            "client_message_id": "assistant-budget",
            "role": "assistant",
            "content": long_budget_question,
        },
    ]
    state = await ai_module.sync_agent_context_window_from_history({}, history)
    state, _ = await ai_module.append_agent_context_message(
        state,
        role="user",
        content="没有",
        source_message_id="user-budget",
    )
    state["brief_state"] = {
        "fields": {
            "budget": {"value": "没有"},
            "site_photos": {"value": "已上传图片素材"},
        },
        "filled_fields": ["budget", "site_photos"],
        "readiness": {"level": "insufficient"},
    }

    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="session-budget-window",
            message="没有",
            history=history,
            business_type="ai_3d_custom",
            user_message_id="user-budget",
        ),
        agent_state=state,
    )

    assert messages[-2] == {"role": "assistant", "content": long_budget_question}
    assert messages[-1] == {"role": "user", "content": "没有"}
    assert {"role": "user", "content": "压缩的较早上下文"} in messages
    assert "项目制作预算：没有" in messages[0]["content"]
    assert "现场实拍图：已上传图片素材" in messages[0]["content"]


def test_requirement_prompt_uses_state_projection_instead_of_raw_memory_context():
    brief_state = {
        "fields": {},
        "pending_confirmation": {
            "id": "pending-city-location",
            "field": "city_location",
            "label": "投放城市与媒体位置",
            "candidate_value": "杭州巨屏（湖滨银泰in77 L型地标大屏）",
            "source": "memory_candidate",
            "status": "pending",
        },
    }

    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我想做毛绒质感的大熊猫",
            history=[],
            business_type="ai_3d_custom",
        ),
        memory_context="RAW_MEMORY_CONTEXT_SHOULD_NOT_ENTER_PROMPT：杭州巨屏",
        agent_state={"brief_state": brief_state},
    )

    system_prompt = messages[0]["content"]
    assert "RAW_MEMORY_CONTEXT_SHOULD_NOT_ENTER_PROMPT" not in system_prompt
    assert "待用户确认" in system_prompt
    assert "杭州巨屏" in system_prompt


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
async def test_ai_chat_mock_completion_returns_structured_finish_action(monkeypatch):
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

    assert "【需求收集完成】" not in response["message"]
    assert response["control_action"] == "finish_brief_now"


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
    assert response["control_action"] == "handoff_requested"
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
    assert "裸眼3D视频" in response["reply"]
    assert "普通平面视频" in response["reply"]
    assert "屏幕结构" in response["reply"]
    assert "观看动线" in response["reply"]
    assert "Brief" in response["reply"]
    assert "不需要您一次准备完整资料" in response["reply"]
    assert "三个维度" in response["reply"]
    assert "基础信息、创意方向以及技术与交付" in response["reply"]
    assert "项目背景" in response["reply"]
    assert "投放场景" in response["reply"]
    assert "**裸眼3D视频**" in response["reply"]
    assert "**屏幕结构、观看动线、现场空间，以及出屏/入屏视觉机制**" in response["reply"]
    assert "**基础信息、创意方向以及技术与交付**" in response["reply"]
    assert "北京" not in response["reply"]
    assert "请先告诉我品牌或项目名称" not in response["reply"]
    assert "请先告诉我项目名称" not in response["reply"]


@pytest.mark.asyncio
async def test_ai_start_uses_creative_director_identity(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    response = await ai_module.ai_start("test-session", None)

    assert "您好，我是 Unique Vision AI 的创意提案总监。" in response["reply"]
    assert "我们是国内裸眼3D视觉内容与数字艺术创意领域的头部服务商，已为众多媒体方客户提供过高品质的裸眼3D视觉内容解决方案。" in response["reply"]
    assert "核心团队深耕行业多年" not in response["reply"]
    assert "创意提案总监型项目顾问" not in response["reply"]


def test_media_3d_prompt_requires_opening_brief_dimensions():
    assert "一句预期说明" in ai_module._PROMPT_MEDIA_3D
    assert "必须包含这句" in ai_module._PROMPT_MEDIA_3D
    assert "围绕三个维度慢慢收拢：基础信息、创意方向以及技术与交付" in ai_module._PROMPT_MEDIA_3D
    assert "第一轮必须分成 3 个短段落" in ai_module._PROMPT_MEDIA_3D
    assert "每段之间用空行分隔" in ai_module._PROMPT_MEDIA_3D
    assert "不要把所有信息压成一个长段落" in ai_module._PROMPT_MEDIA_3D
    assert "第一轮需要加粗 2-3 个真正帮助用户抓重点的信息" in ai_module._PROMPT_MEDIA_3D
    assert "**裸眼3D视频**" in ai_module._PROMPT_MEDIA_3D
    assert "**基础信息、创意方向以及技术与交付**" in ai_module._PROMPT_MEDIA_3D


def test_media_brief_prompt_delegates_control_markers_to_backend():
    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我想做一个裸眼3D项目",
            history=[],
            business_type="ai_3d_custom",
        )
    )
    system_prompt = messages[0]["content"]

    assert "【需求收集完成】" not in system_prompt
    assert "【转人工】" not in system_prompt
    assert "输出完成标记" not in system_prompt
    assert "回复末尾输出" not in system_prompt
    assert "控制动作" in system_prompt
    assert "后端" in system_prompt


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
async def test_ai_chat_requirement_completion_uses_stable_temperature(monkeypatch):
    captured_payload = {}

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {"choices": [{"message": {"content": "我先记下这个方向。"}}]}

    async def _mock_state_update(**_):
        return {}

    async def _mock_memory_hints(_user_id):
        return {}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module.settings, "AI_MODEL_NAME", "qwen3.7-plus")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_state_update)
    monkeypatch.setattr(ai_module, "_build_memory_hints", _mock_memory_hints)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我想做一个毛绒质感的大熊猫3D视频",
            history=[],
            business_type="ai_3d_custom",
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert response["message"] == "我先记下这个方向。"
    assert captured_payload["temperature"] == 0.3


@pytest.mark.asyncio
async def test_ai_chat_marks_non_blocking_creative_evaluation_hint_as_shown(monkeypatch):
    captured_payload = {}
    saved_states = []

    async def _mock_completion(payload, *, timeout=None):
        captured_payload.update(payload)
        return {"choices": [{"message": {"content": "我先把这个创意方向接住。接下来想确认一下现场观看关系。"}}]}

    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "theme_concept": "毛绒质感大熊猫与商场环境互动",
                "art_direction": "治愈、柔软、有互动感",
                "city_location": "杭州湖滨银泰in77 L型地标大屏",
            },
        )
        return {
            "current_agent": "brief_agent",
            "stage": "brief_building",
            "business_type": "ai_3d_custom",
            "brief_state": brief_state,
        }

    def _mock_save_state(_session_id, _user_id, state):
        saved_states.append(dict(state))

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "_build_memory_hints", lambda _user_id: {})
    monkeypatch.setattr(ai_module, "_save_agent_state", _mock_save_state)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="治愈风格",
            history=[],
            business_type="ai_3d_custom",
        ),
        _request_without_auth(),
        _fake_user(),
    )

    system_prompt = captured_payload["messages"][0]["content"]
    assert "非阻塞创意评估提醒" in system_prompt
    assert "不要要求用户回答“有/没有”" in system_prompt
    assert response["message"] == "我先把这个创意方向接住。接下来想确认一下现场观看关系。"
    assert response["agent_state"]["creative_evaluation_hint"]["status"] == "shown"
    assert saved_states[-1]["creative_evaluation_hint"]["status"] == "shown"


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
    assert "观看" in response["message"] or "动线" in response["message"]


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
    assert any(keyword in response["message"] for keyword in ("观看", "动线", "哪类人群或观看场景"))


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
async def test_media_ai_chat_observes_redundant_specs_followup_without_rewriting_reply(monkeypatch):
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
    assert "投放点位或屏幕规格" in response["message"]
    assert "需求确认清单" in response["message"]
    assert "若后续有现场实拍图或更具体的审核规范，可随时补充" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_does_not_rewrite_model_reply_when_brief_state_has_specs(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "收到已上传的参考文件。\n\n"
                            "结合您提供的素材和之前的沟通，目前项目核心要素已明确："
                            "杭州湖滨银泰in77 L型大屏、毛绒质感熊猫、慵懒趴姿、4K规格、下个月上刊、预算20w。\n\n"
                            "我还需要再补充一个关键信息：这次项目对应的投放点位或屏幕规格目前方便确认吗？"
                            "如果暂时没有完整参数，先说城市、屏幕位置或已有规格也可以。"
                        )
                    }
                }
            ]
        }

    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "city_location": "杭州湖滨银泰in77 L型大屏",
                "media_specs": "L型大屏，4K规格",
                "theme_concept": "毛绒质感熊猫，慵懒趴姿，与周围环境互动并冲出屏幕",
                "art_direction": "毛绒质感",
                "audience_scene": "商圈年轻消费者和游客",
                "budget": "20w",
                "online_time": "下个月上刊",
                "site_photos": "已上传参考文件",
            },
        )
        return {"current_agent": "brief_agent", "stage": "brief_building", "business_type": "ai_3d_custom", "brief_state": brief_state}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="[已上传文件: reference.png]",
            history=[
                {"role": "user", "content": "杭州湖滨银泰in77 L型大屏，4K规格，想做毛绒质感熊猫，预算20w，下个月上刊"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "杭州湖滨银泰in77 L型大屏" in response["message"]
    assert "投放点位或屏幕规格" in response["message"]
    assert "城市、屏幕位置或已有规格" in response["message"]
    assert "毛绒质感熊猫" in response["message"]
    assert "下个月上刊" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_uses_memory_city_hint_for_next_question(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "这个方向我先记下。我们了解到您这边常用的投放城市线索是杭州，这次也是基于杭州来做吗？如果不是，也可以直接说新的城市或屏幕。"
                    }
                }
            ]
        }

    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "theme_concept": "毛绒质感的大熊猫",
                "art_direction": "毛绒质感",
            },
        )
        brief_state["pending_confirmation"] = {
            "id": "pending-city",
            "field": "city_location",
            "label": "投放城市与媒体位置",
            "candidate_value": "杭州",
            "source": "memory_candidate",
            "status": "pending",
        }
        return {"current_agent": "brief_agent", "stage": "brief_building", "business_type": "ai_3d_custom", "brief_state": brief_state}

    async def _mock_memory(_user_id):
        return SimpleNamespace(
            company_info={},
            screen_resources=[],
            project_preferences={"common_cities": ["杭州"]},
            past_projects=[],
            agent_notes="",
        )

    async def _mock_update_stats(_user_id):
        return None

    import app.services.memory_service as memory_service

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)
    monkeypatch.setattr(memory_service, "get_or_create_memory", _mock_memory)
    monkeypatch.setattr(memory_service, "update_interaction_stats", _mock_update_stats)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="我想做毛绒质感的大熊猫",
            history=[
                {"role": "assistant", "content": "您可以先简单说说，这次大概想做什么样的内容？"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "杭州" in response["message"]
    assert "常用的投放城市线索是杭州" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_preserves_pending_memory_specs_after_upload_reply(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "收到，已保存参考素材 hero.jpeg。\n\n"
                            "点位方向我先记录。我们了解到这块屏幕大致是 L 型地标大屏，"
                            "尺寸约 100m x 70m；这次先按这个规格来适配吗？如果参数有更新，也可以直接告诉我。"
                        )
                    }
                }
            ]
        }

    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "theme_concept": "毛绒质感的大熊猫",
                "city_location": "杭州湖滨银泰in77 L型地标大屏",
                "art_direction": "毛绒质感",
            },
        )
        brief_state["pending_confirmation"] = {
            "id": "pending-specs",
            "field": "media_specs",
            "label": "屏幕规格",
            "candidate_value": "L型屏，100m x 70m，L型，L型结构，约100m x 70m，L型地标大屏，约宽100m x 高70m",
            "source": "memory_candidate",
            "status": "pending",
        }
        return {"current_agent": "brief_agent", "stage": "brief_building", "business_type": "ai_3d_custom", "brief_state": brief_state}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _mock_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "_build_memory_hints", lambda _user_id: {})
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="[已上传文件: hero.jpeg]",
            history=[
                {"role": "user", "content": "想做毛绒质感的大熊猫"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "hero.jpeg" in response["message"]
    assert "有一组可参考规格" not in response["message"]
    assert "100m x 70m" in response["message"]
    assert "L 型地标大屏" in response["message"]


@pytest.mark.asyncio
async def test_media_ai_chat_offers_creative_direction_when_brief_is_ready(monkeypatch):
    async def _unexpected_completion(*_, **__):
        raise AssertionError("ready brief should offer creative direction before calling main LLM")

    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "theme_concept": "毛绒质感大熊猫，与现场环境互动并冲出屏幕",
                "city_location": "杭州湖滨银泰in77 L型地标大屏",
                "audience_scene": "商圈年轻消费者和游客",
                "resource_background": "核心商圈地标屏，适合城市打卡传播",
            },
        )
        return {"current_agent": "brief_agent", "stage": "brief_building", "business_type": "ai_3d_custom", "brief_state": brief_state}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _unexpected_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda *_: None)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="核心信息就是这些",
            history=[
                {"role": "user", "content": "杭州湖滨银泰in77，想做毛绒大熊猫，面向年轻游客"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "AI 创意方向" in response["message"]
    assert "基于目前这些信息" in response["message"]
    assert "这几个信息已经能支撑" in response["message"]
    assert "不是完整创意方案" in response["message"]
    assert "【需求收集完成】" not in response["message"]
    assert response["agent_state"]["creative_direction_offer"]["status"] == "offered"


@pytest.mark.asyncio
async def test_media_ai_chat_accepts_creative_direction_offer_and_calls_subagent(monkeypatch):
    captured_request = {}

    async def _unexpected_completion(*_, **__):
        raise AssertionError("accepted creative offer should call creative direction subagent")

    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "theme_concept": "毛绒质感大熊猫，与现场环境互动并冲出屏幕",
                "city_location": "杭州湖滨银泰in77 L型地标大屏",
                "audience_scene": "商圈年轻消费者和游客",
                "resource_background": "核心商圈地标屏，适合城市打卡传播",
            },
        )
        return {
            "current_agent": "brief_agent",
            "stage": "brief_building",
            "business_type": "ai_3d_custom",
            "brief_state": brief_state,
            "creative_direction_offer": {"status": "offered", "brief_version": brief_state["version"]},
        }

    async def _mock_direction(request):
        captured_request["message"] = request.message
        captured_request["agent_state"] = request.agent_state
        return {
            "message": (
                "**创意方向草案**\n\n"
                "- **创意方向名称**：云绒熊猫探屏\n"
                "- **计划概括**：基于当前点位做一版轻量方向。\n\n"
                "为了继续推进，想确认一下观众主要从哪个方向观看？"
            ),
            "return_to_brief": False,
        }

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "post_chat_completion", _unexpected_completion)
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "ai_creative_direction", _mock_direction)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda *_: None)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="可以，先做一次AI创意",
            history=[
                {"role": "user", "content": "杭州湖滨银泰in77，想做毛绒大熊猫，面向年轻游客"},
                {"role": "assistant", "content": "基于目前这些信息，要不要我先做一次 AI 创意方向？"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "创意方向草案" in response["message"]
    assert captured_request["message"] == "可以，先做一次AI创意"
    assert captured_request["agent_state"]["brief_state"]["readiness"]["level"] == "provisional"
    assert response["agent_state"]["creative_direction_offer"]["status"] == "completed"
    assert response["return_to_brief"] is False
    assert response["agent_state"]["current_agent"] == "creative_direction_agent"
    assert response["agent_state"]["stage"] == "creative_direction_review"
    assert response["agent_state"]["pending_creative_direction"]["status"] == "awaiting_feedback"


def test_creative_direction_offer_does_not_accept_attachment_only_upload():
    message = (
        "[已上传文件: 可以生成创意方向.png]\n\n"
        "[图片理解摘要]\n"
        "文件：可以生成创意方向.png\n"
        "视觉摘要：这是一张参考图，可用于后续生成创意方向。"
    )
    state = {"creative_direction_offer": {"status": "offered"}}

    assert ai_module._is_creative_direction_offer_acceptance(message, state) is False


def test_creative_direction_route_state_keeps_pending_during_feedback_and_clears_on_exit():
    state = {
        "current_agent": "creative_direction_agent",
        "stage": "creative_direction_review",
        "pending_creative_direction": {"status": "awaiting_feedback"},
    }
    stay_route = ai_module.RouteDecision(
        action="stay",
        intent="creative_direction",
        target_agent="creative_direction_agent",
        stage="creative_direction_review",
    )
    exit_route = ai_module.RouteDecision(
        action="switch",
        intent="brief_building",
        target_agent="brief_agent",
        stage="brief_building",
    )

    active_state = ai_module._apply_creative_direction_route_state(state, stay_route)
    exited_state = ai_module._apply_creative_direction_route_state(active_state, exit_route)

    assert active_state["pending_creative_direction"]["status"] == "awaiting_feedback"
    assert active_state["current_agent"] == "creative_direction_agent"
    assert active_state["stage"] == "creative_direction_review"
    assert exited_state["pending_creative_direction"] is None
    assert exited_state["current_agent"] == "brief_agent"
    assert exited_state["stage"] == "brief_building"


def test_creative_direction_route_state_keeps_exit_recommendation_when_user_continues():
    state = {
        "current_agent": "creative_direction_agent",
        "stage": "creative_direction_exit_recommended",
        "pending_creative_direction": {
            "status": "exit_recommended",
            "iteration_count": 5,
            "exit_recommended": True,
        },
    }
    route = ai_module.RouteDecision(
        action="stay",
        intent="creative_direction",
        target_agent="creative_direction_agent",
        stage="creative_direction_exit_recommended",
    )

    next_state = ai_module._apply_creative_direction_route_state(state, route)

    assert next_state["pending_creative_direction"]["iteration_count"] == 5
    assert next_state["pending_creative_direction"]["status"] == "exit_recommended"
    assert next_state["stage"] == "creative_direction_exit_recommended"


def test_creative_diagnosis_route_state_keeps_review_and_clears_it_on_exit():
    state = {
        "current_agent": "creative_diagnosis_agent",
        "stage": "creative_diagnosis_review",
        "pending_evaluation": {
            "status": "awaiting_feedback",
            "iteration_count": 2,
            "iteration_limit": 5,
        },
    }
    stay_route = ai_module.RouteDecision(
        action="stay",
        intent="creative_diagnosis",
        target_agent="creative_diagnosis_agent",
        stage="creative_diagnosis_review",
    )
    exit_route = ai_module.RouteDecision(
        action="switch",
        intent="brief_building",
        target_agent="brief_agent",
        stage="brief_building",
    )

    active_state = ai_module._apply_agent_route_state(state, stay_route)
    exited_state = ai_module._apply_agent_route_state(active_state, exit_route)

    assert active_state["pending_evaluation"]["status"] == "awaiting_feedback"
    assert active_state["current_agent"] == "creative_diagnosis_agent"
    assert active_state["stage"] == "creative_diagnosis_review"
    assert exited_state["pending_evaluation"] is None
    assert exited_state["current_agent"] == "brief_agent"
    assert exited_state["stage"] == "brief_building"


@pytest.mark.asyncio
async def test_media_ai_chat_stream_sends_thinking_for_accepted_creative_offer(monkeypatch):
    async def _mock_agent_state(**_):
        from app.services.ai_brief_state import create_empty_brief_state, merge_brief_updates

        brief_state = merge_brief_updates(
            create_empty_brief_state("ai_3d_custom"),
            {
                "theme_concept": "毛绒质感大熊猫，与现场环境互动并冲出屏幕",
                "city_location": "杭州湖滨银泰in77 L型地标大屏",
                "audience_scene": "商圈年轻消费者和游客",
                "resource_background": "核心商圈地标屏，适合城市打卡传播",
            },
        )
        return {
            "current_agent": "brief_agent",
            "stage": "brief_building",
            "business_type": "ai_3d_custom",
            "brief_state": brief_state,
            "creative_direction_offer": {"status": "offered", "brief_version": brief_state["version"]},
        }

    async def _mock_direction(request):
        return {"message": "**创意方向草案**\n\n- **创意方向名称**：云绒熊猫探屏", "return_to_brief": False}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")
    monkeypatch.setattr(ai_module, "_update_agent_state_for_message", _mock_agent_state)
    monkeypatch.setattr(ai_module, "ai_creative_direction", _mock_direction)
    monkeypatch.setattr(ai_module, "_save_agent_state", lambda *_: None)
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    response = await ai_module.ai_chat_stream(
        ai_module.ChatRequest(
            session_id="test-session",
            message="可以，先做一次AI创意",
            history=[
                {"role": "assistant", "content": "基于目前这些信息，要不要我先做一次 AI 创意方向？"},
            ],
        ),
        _request_without_auth(),
        _fake_user(),
    )

    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    body = "".join(chunks)

    assert "event: thinking" in body
    assert "AI 创意方向构思" in body
    assert "event: final" in body
    assert "创意方向草案" in body


@pytest.mark.asyncio
async def test_media_ai_chat_honors_router_finish_after_final_asset_question(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "好的，我按当前信息整理需求。"
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
            control_action="finish_brief_now",
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert response["control_action"] == "finish_brief_now"


@pytest.mark.asyncio
async def test_media_ai_chat_does_not_infer_completion_from_ambiguous_no_more_reply(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": "这个信息够用了。接下来想确认一下项目的审核边界。"
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
                    "role": "assistant",
                    "content": "还有更详细的屏幕尺寸吗？如果有现场实拍图或结构图，也可以提供。",
                },
            ],
            control_action="none",
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert response["control_action"] == "none"


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
            control_action="finish_brief_now",
        ),
        _request_without_auth(),
        _fake_user(),
    )

    assert "【需求收集完成】" not in response["message"]
    assert response["control_action"] == "finish_brief_now"


@pytest.mark.asyncio
async def test_ai_chat_stream_qwen_uses_chat_completions_without_responses_probe(monkeypatch):
    async def _unexpected_responses_stream(*_, **__):
        raise AssertionError("Qwen stream should not probe the Responses API")
        yield ""

    async def _mock_chat_stream_events(payload, *, timeout=None):
        assert payload["model"] == "qwen3.7-plus"
        assert payload["messages"][-1]["content"] == "我想做一个裸眼3D项目"
        assert payload["temperature"] == 0.3
        assert timeout == 120
        yield {"type": "content", "content": "好的"}
        yield {"type": "content", "content": "，请问计划投放在哪个城市？"}

    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(ai_module.settings, "AI_RESPONSES_BASE_URL", "")
    monkeypatch.setattr(ai_module.settings, "AI_PREFER_RESPONSES_API", False)
    monkeypatch.setattr(ai_module.settings, "AI_MODEL_NAME", "qwen3.7-plus")
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
    monkeypatch.setattr(ai_client.settings, "AI_MODEL_NAME", "qwen3.7-plus")
    monkeypatch.setattr(ai_client.settings, "AI_ENABLE_THINKING", False)

    payload = ai_client._prepare_chat_payload({"model": "qwen3.7-plus", "messages": []})

    assert payload["enable_thinking"] is False


def test_creative_plan_request_no_longer_injects_direction_draft_rules(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "AGENT_MODE", "media")

    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message="根据上面的信息帮我生成一个创意方案",
            history=[{"role": "user", "content": "我们想做杭州西湖主题的裸眼3D内容"}],
        )
    )

    system_prompt = messages[0]["content"]
    assert "创意方向草案" not in system_prompt
    assert "创意方向名称" not in system_prompt


def test_creative_revision_request_no_longer_injects_direction_draft_rules(monkeypatch):
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
    assert "修订方向草案" not in system_prompt
    assert "创意方向草案" not in system_prompt


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
