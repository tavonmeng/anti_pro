import pytest

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
