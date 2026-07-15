from types import SimpleNamespace

import pytest

from app.services import ai_brief_document_service as document_module
from app.services.document_parser_service import ParsedSection


def test_pdf_confirmation_reply_lists_extracted_fields_without_saving_them():
    reply = document_module.build_brief_document_confirmation_reply(
        document_module.BriefDocumentExtraction(
            updates={
                "project_name": "春季发布会",
                "city_location": "杭州湖滨银泰",
            },
            filenames=["brief.pdf"],
        )
    )

    assert "项目名称**：春季发布会" in reply
    assert "投放城市与媒体位置**：杭州湖滨银泰" in reply
    assert "并纳入本次 Brief" in reply
    assert "未提及的内容将保持" in reply


def test_pdf_revision_reply_lists_only_corrected_fields():
    reply = document_module.build_brief_document_revision_reply(
        {"city_location": "上海南京东路"}
    )

    assert "投放城市与媒体位置**：上海南京东路" in reply
    assert "项目名称" not in reply


@pytest.mark.asyncio
async def test_extract_uploaded_pdf_brief_fields(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    pdf_dir = upload_dir / "site_photos" / "user-test"
    pdf_dir.mkdir(parents=True)
    pdf_path = pdf_dir / "brief.pdf"
    pdf_path.write_bytes(b"%PDF-test")

    monkeypatch.setattr(document_module.settings, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(document_module.settings, "OSS_ENABLED", False)
    monkeypatch.setattr(document_module.settings, "AI_API_KEY", "test-key")
    monkeypatch.setattr(
        document_module,
        "parse_document",
        lambda *_: [ParsedSection(label="第1页", page=1, text="项目名称：春季发布会；投放城市：杭州湖滨银泰")],
    )

    async def _mock_completion(payload, *, timeout=None, attempts=None):
        assert "杭州湖滨银泰" in payload["messages"][1]["content"]
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"project_name":"春季发布会","city_location":"杭州湖滨银泰",'
                            '"theme_concept":"","remarks":""}'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(document_module, "post_chat_completion", _mock_completion)
    result = await document_module.extract_uploaded_brief_documents(
        [
            SimpleNamespace(
                name="brief.pdf",
                url="/uploads/site_photos/user-test/brief.pdf",
                type="application/pdf",
                object_key="",
            )
        ],
        user_id="user-test",
    )

    assert result.updates == {
        "project_name": "春季发布会",
        "city_location": "杭州湖滨银泰",
    }
    assert document_module.PDF_BRIEF_CONTEXT_MARKER in result.context
    assert "项目名称：春季发布会" in result.context


@pytest.mark.asyncio
async def test_extract_uploaded_pdf_rejects_other_user_path(monkeypatch, tmp_path):
    monkeypatch.setattr(document_module.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(document_module.settings, "OSS_ENABLED", False)
    monkeypatch.setattr(document_module.settings, "AI_API_KEY", "test-key")

    result = await document_module.extract_uploaded_brief_documents(
        [
            SimpleNamespace(
                name="brief.pdf",
                url="/uploads/site_photos/another-user/brief.pdf",
                type="application/pdf",
                object_key="",
            )
        ],
        user_id="user-test",
    )

    assert not result.updates
    assert result.failures == ["brief.pdf：无法访问文件"]


@pytest.mark.asyncio
async def test_document_updates_require_confirmation_before_writing_brief_state(monkeypatch, tmp_path):
    from app.services.ai_brief_state import update_agent_state_from_message

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")

    async def _mock_confirmation(payload, **_kwargs):
        assert "pending_pdf_brief" in payload["messages"][1]["content"]
        return {"choices": [{"message": {"content": '{"action":"confirmed","updates":{}}'}}]}

    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_confirmation)

    state = await update_agent_state_from_message(
        session_id="pdf-session",
        user_id="pdf-user",
        business_type="ai_3d_custom",
        message=(
            "[已上传文件: brief.pdf]\n\n"
            "[PDF Brief解析内容]\n"
            "文件：brief.pdf\n"
            "已从 PDF 提取的 Brief 内容：\n"
            "- 投放城市与媒体位置：杭州湖滨银泰"
        ),
        history=[],
        source_message_id="pdf-message",
        memory_hints={},
        document_updates={"city_location": "杭州湖滨银泰"},
    )

    field = state["brief_state"]["fields"]["city_location"]
    assert field["value"] == "杭州湖滨银泰"
    assert state["brief_state"]["fields"]["site_photos"]["value"] == ""
    assert state["pending_document_brief"]["updates"] == {"city_location": "杭州湖滨银泰"}
    context_message = state["agent_context_window"]["messages"][-1]["content"]
    assert "用户上传了 PDF 资料" in context_message
    assert "杭州湖滨银泰" not in context_message

    reviewed = await update_agent_state_from_message(
        session_id="pdf-session",
        user_id="pdf-user",
        business_type="ai_3d_custom",
        message="确认",
        history=[],
        source_message_id="pdf-confirmation",
        memory_hints={},
    )

    reviewed_field = reviewed["brief_state"]["fields"]["city_location"]
    assert reviewed_field["value"] == "杭州湖滨银泰"
    assert reviewed["pending_document_brief"] is None
    assert reviewed["document_brief_confirmation"]["status"] == "reviewed_no_changes"


@pytest.mark.asyncio
async def test_document_revision_updates_candidate_and_waits_for_new_confirmation(monkeypatch, tmp_path):
    from app.services.ai_brief_state import update_agent_state_from_message

    monkeypatch.setattr("app.services.ai_brief_state.settings.LOG_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.ai_brief_state.settings.AI_API_KEY", "test-key")

    async def _mock_completion(payload, **_kwargs):
        input_payload = payload["messages"][1]["content"]
        if "投放地应为上海南京东路" not in input_payload:
            return {"choices": [{"message": {"content": '{"action":"confirmed","updates":{}}'}}]}
        assert "杭州湖滨银泰" in input_payload
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"action":"revised","updates":{"city_location":"上海南京东路"}}'
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.ai_brief_state.post_chat_completion", _mock_completion)

    await update_agent_state_from_message(
        session_id="revision-session",
        user_id="pdf-user",
        business_type="ai_3d_custom",
        message="[已上传文件: brief.pdf]",
        source_message_id="pdf-message",
        document_updates={"city_location": "杭州湖滨银泰", "project_name": "春季发布会"},
        document_filenames=["brief.pdf"],
    )

    revised = await update_agent_state_from_message(
        session_id="revision-session",
        user_id="pdf-user",
        business_type="ai_3d_custom",
        message="投放地应为上海南京东路",
        source_message_id="revision-message",
    )

    assert revised["brief_state"]["fields"]["city_location"]["value"] == "上海南京东路"
    assert revised["brief_state"]["fields"]["project_name"]["value"] == "春季发布会"
    assert revised["pending_document_brief"] is None
    assert revised["document_brief_confirmation"]["status"] == "revised"
