import pytest
import json

from app.api import ai_creative_diagnosis_agent as diagnosis_module
from app.services.ai_image_understanding import IMAGE_CONTEXT_MARKER


@pytest.mark.asyncio
async def test_creative_diagnosis_fallback_evaluates_then_returns_to_brief(monkeypatch):
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
    assert response["return_to_brief"] is True
    assert "阶段性创意评估" in message
    assert "成立点" in message
    assert "风险点" in message
    assert "优化方向" in message
    assert "回到 Brief" not in message
    assert "Brief 附件" not in message
    assert "我先记录下来" not in message
    assert "【需求收集完成】" not in message


def test_creative_diagnosis_prompt_bans_fixed_brief_return_phrasing():
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


def test_creative_diagnosis_gate_uses_agent_context_window_when_available():
    raw_long_history = "原始超长创意方向内容。" * 80
    messages = diagnosis_module.build_creative_diagnosis_gate_messages(
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
                            '{"is_evaluable":false,'
                            '"status":"awaiting_evaluation_target",'
                            '"reason":"用户只是在要求评估，但没有给出具体创意对象",'
                            '"missing_aspects":["创意主体","关键动作或互动机制"],'
                            '"followup_question":"可以再补充一下这个创意的主体、动作或想呈现的画面吗？"}'
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
async def test_creative_diagnosis_keeps_pending_when_given_sparse_concept(monkeypatch):
    async def _mock_completion(payload, *, timeout=None):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"is_evaluable":false,'
                            '"status":"not_evaluable_concept",'
                            '"reason":"只有主体和材质，没有动作机制或场景关系",'
                            '"missing_aspects":["关键动作机制","屏幕或现场关系"],'
                            '"followup_question":"这只毛绒熊猫会在画面里做什么，和屏幕或现场有什么互动？"}'
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
async def test_creative_diagnosis_gate_parse_failure_does_not_fallback_to_evaluation(monkeypatch):
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
    assert len(calls) == 1
    assert "可以" in message
    assert "可行性" in message
    assert "暂时还不能做创意评估" not in message
    assert "阶段性创意评估" not in message
    assert response["agent_state"]["pending_evaluation"]["status"] == "awaiting_target"


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
