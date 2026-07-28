import pytest
import json

from app.api import ai_creative_diagnosis_agent as diagnosis_module
from app.services.ai_image_understanding import IMAGE_CONTEXT_MARKER
from app.services.ai_upload_context import BRIEF_DOCUMENT_CONTEXT_MARKER


@pytest.mark.asyncio
async def test_creative_diagnosis_fallback_evaluates_and_keeps_diagnosis_context(monkeypatch):
    monkeypatch.setattr(diagnosis_module.settings, "AI_API_KEY", "")

    response = await diagnosis_module.ai_creative_diagnosis(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="我们想做一只巨型猫从商场L型转角屏探出来，帮我评估一下",
            history=[
                {"role": "user", "content": "成都核心商圈，年轻消费者和周末逛街人群"},
            ],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {
                    "fields": {
                        "city_location": {"value": "成都核心商圈"},
                        "audience_scene": {"value": "年轻消费者和周末逛街人群"},
                        "theme_concept": {"value": "巨型猫从商场L型转角屏探出来"},
                    },
                    "readiness": {"level": "provisional", "score_confidence": "medium"},
                    "missing_fields": ["viewing_path", "media_specs", "content_review"],
                }
            },
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is False
    assert response["agent_state"]["current_agent"] == "creative_diagnosis_agent"
    assert response["agent_state"]["stage"] == "creative_diagnosis_review"
    assert response["agent_state"]["pending_evaluation"]["status"] == "awaiting_feedback"
    assert response["agent_state"]["pending_evaluation"]["iteration_count"] == 1
    assert "阶段性创意评估" in message
    assert "成立点" in message
    assert "风险点" in message
    assert "优化方向" in message
    assert "回到 Brief" not in message
    assert "Brief 附件" not in message
    assert "我先记录下来" not in message
    assert "【需求收集完成】" not in message
    assert "为了把这个创意判断落到现场" not in message


def test_creative_diagnosis_prompt_bans_fixed_brief_return_and_question():
    messages = diagnosis_module.build_creative_diagnosis_messages(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="评估一下这个方案",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {"theme_concept": {"value": "毛绒大熊猫破屏互动"}}}},
        )
    )

    system_prompt = messages[0]["content"]
    assert "回到 Brief" not in system_prompt
    assert "Brief 附件" not in system_prompt
    assert "我先记录下来" not in system_prompt
    assert "不要为了推进需求梳理而固定追加问题" in system_prompt
    assert "next_brief_question 只是一条可选参考" in system_prompt


def test_creative_diagnosis_uses_agent_context_window_when_available():
    raw_long_history = "原始超长创意方向内容。" * 80
    messages = diagnosis_module.build_creative_diagnosis_messages(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="评估一下刚才这版",
            history=[{"role": "assistant", "content": raw_long_history}],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {"fields": {}},
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


@pytest.mark.asyncio
async def test_creative_diagnosis_requests_more_detail_when_idea_is_not_evaluable(monkeypatch):
    calls = []

    async def _mock_completion(payload, *, timeout=None):
        calls.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"status":"awaiting_target",'
                            '"message":"可以，我会从可行性、裸眼3D适配、传播价值和优化空间几个角度帮您看。'
                            '可以补充一下这个创意的主体和动作吗？"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(diagnosis_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(diagnosis_module, "post_chat_completion", _mock_completion)

    response = await diagnosis_module.ai_creative_diagnosis(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="评估一下这个方案",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}}},
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is False
    assert len(calls) == 1
    assert "可以" in message
    assert "可行性" in message
    assert "裸眼3D适配" in message
    assert "暂时还不能做创意评估" not in message
    assert "主体" in message
    assert "动作" in message
    assert "阶段性创意评估" not in message
    assert response["agent_state"]["pending_evaluation"]["status"] == "awaiting_target"
    assert response["agent_state"]["current_agent"] == "creative_diagnosis_agent"


@pytest.mark.asyncio
async def test_creative_diagnosis_evaluates_referenced_multi_direction_history_in_one_call(monkeypatch):
    calls = []

    async def _mock_completion(payload, *, timeout=None):
        calls.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"status":"evaluated","message":"**阶段性创意评估**\\n\\n'
                            '**成立点**\\n方向一和方向二都具备清晰的裸眼3D机制。\\n\\n'
                            '**风险点**\\n需要结合现场参数校准。\\n\\n'
                            '**优化方向**\\n建议比较两条路径的品牌适配度。"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(diagnosis_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(diagnosis_module, "post_chat_completion", _mock_completion)

    target = "**创意方向草案**：方向一是车辆破界，方向二是霓虹光轨重塑车身。"
    response = await diagnosis_module.ai_creative_diagnosis(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="能不能评估一下这个创意方向",
            history=[{"role": "assistant", "content": target}],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}}},
        )
    )

    assert len(calls) == 1
    payload = json.loads(calls[0]["messages"][1]["content"])
    assert payload["recent_history"] == [{"role": "assistant", "content": target}]
    assert "evaluation_target" not in payload
    assert "多个备选方向" in calls[0]["messages"][0]["content"]
    assert "阶段性创意评估" in response["message"]
    assert "您先把创意方向简单说一下" not in response["message"]
    assert response["return_to_brief"] is False
    assert response["agent_state"]["current_agent"] == "creative_diagnosis_agent"
    assert response["agent_state"]["pending_evaluation"]["status"] == "awaiting_feedback"
    assert response["agent_state"]["pending_evaluation"]["iteration_count"] == 1


@pytest.mark.asyncio
async def test_creative_diagnosis_five_round_conversation_reaches_soft_exit(monkeypatch):
    monkeypatch.setattr(diagnosis_module.settings, "AI_API_KEY", "")
    state = {
        "brief_state": {
            "fields": {
                "city_location": {"value": "杭州湖滨银泰in77 L型大屏"},
                "audience_scene": {"value": "游客和年轻消费者"},
                "theme_concept": {"value": "熊猫与自然元素的裸眼3D互动"},
            }
        }
    }

    responses = []
    for round_index in range(1, 6):
        response = await diagnosis_module.ai_creative_diagnosis(
            diagnosis_module.CreativeDiagnosisRequest(
                session_id="session-five-diagnosis-rounds",
                message=f"第{round_index}轮：继续评估当前方向",
                history=[],
                business_type="ai_3d_custom",
                agent_state=state,
            )
        )
        state = response["agent_state"]
        responses.append(response)
        assert state["pending_evaluation"]["iteration_count"] == round_index

    for response in responses[:4]:
        assert response["agent_state"]["pending_evaluation"]["status"] == "awaiting_feedback"
        assert "这轮评估经过几次推演" not in response["message"]

    fifth_response = responses[4]
    pending = fifth_response["agent_state"]["pending_evaluation"]
    assert pending["status"] == "exit_recommended"
    assert pending["iteration_limit"] == 5
    assert pending["exit_recommended"] is True
    assert pending["exit_recommended_at"]
    assert fifth_response["agent_state"]["stage"] == "creative_diagnosis_exit_recommended"
    assert fifth_response["message"].count("这轮评估经过几次推演") == 1
    assert "具体方案还需要策划专家结合品牌目标、屏幕参数、现场观看动线" in fifth_response["message"]
    assert "回到需求梳理" in fifth_response["message"]
    assert "5 轮迭代" not in fifth_response["message"]


@pytest.mark.asyncio
async def test_creative_diagnosis_keeps_pending_when_given_sparse_concept(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"status":"awaiting_target",'
                            '"message":"这个方向我可以先接住。为了评估得更准，'
                            '这只毛绒熊猫会在画面里做什么，和屏幕或现场有什么互动？"}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(diagnosis_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(diagnosis_module, "post_chat_completion", _mock_completion)

    response = await diagnosis_module.ai_creative_diagnosis(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="毛绒质感的大熊猫",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"pending_evaluation": {"status": "awaiting_target"}},
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is False
    assert "为了评估得更准" in message
    assert "暂时还不能做创意评估" not in message
    assert response["agent_state"]["pending_evaluation"]["status"] == "awaiting_target"


@pytest.mark.asyncio
async def test_creative_diagnosis_parse_failure_uses_safe_fallback(monkeypatch):
    calls = []

    async def _mock_completion(payload, *, timeout=None):
        calls.append(payload)
        return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(diagnosis_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(diagnosis_module, "post_chat_completion", _mock_completion)

    response = await diagnosis_module.ai_creative_diagnosis(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message="评估一下这个方案",
            history=[],
            business_type="ai_3d_custom",
            agent_state={"brief_state": {"fields": {}}},
        )
    )

    message = response["message"]
    assert response["return_to_brief"] is False
    assert response["agent_state"]["current_agent"] == "creative_diagnosis_agent"
    assert len(calls) == 1
    assert "阶段性创意评估" in message


def test_creative_diagnosis_prompt_requires_image_feedback_before_evaluation():
    messages = diagnosis_module.build_creative_diagnosis_messages(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message=(
                "评估一下这个现场能不能做\n\n"
                f"{IMAGE_CONTEXT_MARKER}\n"
                "图片类型：实拍屏幕/现场图\n"
                "视觉摘要：图中是一块商圈户外转角屏。"
            ),
            history=[],
            business_type="ai_3d_custom",
        )
    )

    system_prompt = messages[0]["content"]
    assert "图片上传后的用户可见反馈" in system_prompt
    assert "阶段性创意评估" in system_prompt
    assert "我先看了一下这张现场图" in system_prompt


def test_creative_diagnosis_prompt_reads_pdf_context_for_evaluation():
    messages = diagnosis_module.build_creative_diagnosis_messages(
        diagnosis_module.CreativeDiagnosisRequest(
            session_id="session-test",
            message=(
                "评估一下PDF里的方向\n\n"
                f"{BRIEF_DOCUMENT_CONTEXT_MARKER}\n"
                "文件：brief.pdf\n"
                "- 内容主题 & 核心表达：鲸鱼从L型转角跃出"
            ),
            history=[],
            business_type="ai_3d_custom",
            agent_state={
                "brief_state": {"fields": {}},
                "agent_context_window": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "评估一下PDF里的方向\n[用户上传了文档资料]",
                        }
                    ]
                },
            },
        )
    )

    payload = json.loads(messages[1]["content"])
    assert BRIEF_DOCUMENT_CONTEXT_MARKER in payload["current_user_message"]
    assert "鲸鱼从L型转角跃出" in payload["current_user_message"]
    assert "必须读取 current_user_message 中的文档解析内容" in messages[0]["content"]
