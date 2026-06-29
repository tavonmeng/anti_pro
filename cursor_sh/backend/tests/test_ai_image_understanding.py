import base64
import json

import pytest

from app.api import ai as ai_module
from app.services import ai_image_understanding as image_module


def _request_without_auth():
    from starlette.requests import Request

    return Request({"type": "http", "headers": []})


class _FakeUser:
    id = "user-test"
    username = "测试用户"


async def _no_existing_handoff(**_):
    return None


@pytest.mark.asyncio
async def test_summarize_uploaded_images_calls_multimodal_model(monkeypatch, tmp_path):
    upload_root = tmp_path / "uploads"
    image_path = upload_root / "site_photos" / "user-test" / "scene.png"
    image_path.parent.mkdir(parents=True)
    image_bytes = b"fake-png-bytes"
    image_path.write_bytes(image_bytes)
    monkeypatch.setattr(image_module.settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(image_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(image_module.settings, "AI_MODEL_NAME", "qwen3.7-plus")

    captured = {}

    async def fake_post_chat_completion(payload, *, timeout=None, attempts=None):
        captured["payload"] = payload
        captured["timeout"] = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                                {
                                    "image_kind": "reference_design",
                                    "visible_summary": "画面里有一只毛绒质感熊猫，适合作为角色参考。",
                                    "project_clues": ["可作为本次裸眼3D主视觉参考"],
                                    "creative_or_style_clues": ["毛绒材质", "治愈萌宠方向"],
                                "media_or_scene_clues": ["未看到明确屏幕尺寸"],
                                "uncertain_or_missing": ["无法从图片确认城市、预算或上刊时间"],
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(image_module, "post_chat_completion", fake_post_chat_completion)

    summary = await image_module.summarize_uploaded_images(
        message="参考这张图做一个创意方向",
        attachments=[
            image_module.UploadedAttachment(
                name="scene.png",
                url="/uploads/site_photos/user-test/scene.png",
                type="image/png",
                isImage=True,
                size=len(image_bytes),
            )
        ],
    )

    assert image_module.IMAGE_CONTEXT_MARKER in summary
    assert "图片类型：参考设计/风格图" in summary
    assert "毛绒质感熊猫" in summary
    assert "无法从图片确认城市、预算或上刊时间" in summary
    assert "不确定或需确认" not in summary
    assert "识别边界" in summary

    payload = captured["payload"]
    assert payload["model"] == "qwen3.7-plus"
    content = payload["messages"][0]["content"]
    image_part = next(part for part in content if part["type"] == "image_url")
    expected_data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
    assert image_part["image_url"]["url"] == expected_data_url
    assert any(
        part["type"] == "text" and "不要推断城市、预算、上刊时间或屏幕尺寸" in part["text"]
        for part in content
    )
    assert any(
        part["type"] == "text" and "image_kind" in part["text"] and "site_screen_photo" in part["text"]
        for part in content
    )


@pytest.mark.asyncio
async def test_ai_chat_augments_image_context_before_state_update(monkeypatch, tmp_path):
    upload_root = tmp_path / "uploads"
    image_path = upload_root / "site_photos" / "user-test" / "scene.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"fake-png-bytes")
    monkeypatch.setattr(image_module.settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(ai_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.settings, "AI_MODEL_NAME", "qwen3.7-plus")
    monkeypatch.setattr(ai_module, "_save_session_file", lambda **_: None)
    monkeypatch.setattr(ai_module, "_append_handoff_message", _no_existing_handoff)

    async def fake_image_summary(*_, **__):
        return (
            f"{image_module.IMAGE_CONTEXT_MARKER}\n"
            "文件：scene.png\n"
            "视觉摘要：图中是一只毛绒质感熊猫参考图。\n"
            "可用于 Brief 的线索：主视觉角色、毛绒材质。"
        )

    captured_state = {}

    async def fake_update_agent_state(**kwargs):
        captured_state["message"] = kwargs["message"]
        return {"brief_state": {"fields": {}}}

    async def fake_main_completion(payload, *, timeout=None, attempts=None):
        captured_state["llm_message"] = payload["messages"][-1]["content"]
        return {"choices": [{"message": {"content": "我看到了这张参考图的毛绒熊猫方向。"}}]}

    monkeypatch.setattr(ai_module, "summarize_uploaded_images", fake_image_summary)
    monkeypatch.setattr(ai_module, "update_agent_state_from_message", fake_update_agent_state)
    monkeypatch.setattr(ai_module, "post_chat_completion", fake_main_completion)

    response = await ai_module.ai_chat(
        ai_module.ChatRequest(
            session_id="test-session",
            message="[已上传文件: scene.png]",
            history=[],
            attachments=[
                image_module.UploadedAttachment(
                    name="scene.png",
                    url="/uploads/site_photos/user-test/scene.png",
                    type="image/png",
                    isImage=True,
                    size=14,
                )
            ],
        ),
        _request_without_auth(),
        _FakeUser(),
    )

    assert "毛绒熊猫方向" in response["message"]
    assert image_module.IMAGE_CONTEXT_MARKER in captured_state["message"]
    assert "主视觉角色、毛绒材质" in captured_state["llm_message"]


def test_upload_reply_sanitizer_allows_visual_claims_when_image_summary_exists():
    message = (
        "[已上传文件: scene.png]\n\n"
        f"{image_module.IMAGE_CONTEXT_MARKER}\n"
        "视觉摘要：图中是一只毛绒质感熊猫参考图。"
    )
    reply = "从图片可见，这个毛绒质感熊猫适合做成裸眼3D主视觉。"

    assert ai_module._sanitize_upload_reply(message, reply) == reply


def test_requirement_prompt_requires_visible_feedback_when_image_context_exists():
    messages = ai_module._build_requirement_llm_messages(
        ai_module.ChatRequest(
            session_id="test-session",
            message=(
                "[已上传文件: screen.png]\n\n"
                f"{image_module.IMAGE_CONTEXT_MARKER}\n"
                "图片类型：实拍屏幕/现场图\n"
                "视觉摘要：图中是一块商圈转角大屏。"
            ),
            history=[],
        )
    )

    system_prompt = messages[0]["content"]
    assert "图片上传后的用户可见反馈" in system_prompt
    assert "我先看了一下这张现场图" in system_prompt
    assert "实拍屏幕/现场图" in system_prompt
    assert "参考设计/风格图" in system_prompt
    assert "不要直接暴露[图片理解摘要]" in system_prompt
    image_feedback_prompt = system_prompt.split("【图片上传后的用户可见反馈】", 1)[1]
    assert "需要确认项" not in image_feedback_prompt
    assert "还需要确认" not in image_feedback_prompt
    assert "参数" not in image_feedback_prompt
