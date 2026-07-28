import pytest

from app.services import ai_material_understanding as material_module
from app.services.ai_brief_document_service import BriefDocumentExtraction
from app.services.ai_image_understanding import (
    IMAGE_CONTEXT_MARKER,
    ImageUnderstandingResult,
    UploadedAttachment,
)
from app.services.ai_upload_context import BRIEF_DOCUMENT_CONTEXT_MARKER


@pytest.mark.asyncio
async def test_uploaded_material_context_combines_image_and_pdf_understanding(monkeypatch):
    async def fake_image_understanding(**_):
        return ImageUnderstandingResult(
            context=(
                f"{IMAGE_CONTEXT_MARKER}\n"
                "文件：reference.png\n"
                "视觉摘要：一只写实熊猫从L型屏转角探出。"
            ),
            brief_updates={"art_direction": "写实毛发质感"},
            brief_filenames=["reference.png"],
        )

    async def fake_document_extraction(*_, **__):
        return BriefDocumentExtraction(
            updates={"theme_concept": "熊猫与酸奶瓶互动"},
            context=(
                f"{BRIEF_DOCUMENT_CONTEXT_MARKER}\n"
                "文件：campaign.pdf\n"
                "- 内容主题 & 核心表达：熊猫与酸奶瓶互动"
            ),
            filenames=["campaign.pdf"],
        )

    monkeypatch.setattr(material_module, "understand_uploaded_images", fake_image_understanding)
    monkeypatch.setattr(material_module, "extract_uploaded_brief_documents", fake_document_extraction)

    result = await material_module.enrich_message_with_uploaded_materials(
        message="请结合附件出一版创意方向",
        user_id="user-test",
        attachments=[
            UploadedAttachment(
                name="reference.png",
                url="/uploads/site_photos/user-test/reference.png",
                type="image/png",
                isImage=True,
            ),
            UploadedAttachment(
                name="campaign.pdf",
                url="/uploads/site_photos/user-test/campaign.pdf",
                type="application/pdf",
                isImage=False,
            ),
        ],
    )

    assert IMAGE_CONTEXT_MARKER in result.message
    assert "写实熊猫从L型屏转角探出" in result.message
    assert BRIEF_DOCUMENT_CONTEXT_MARKER in result.message
    assert result.document.updates["theme_concept"] == "熊猫与酸奶瓶互动"
    assert result.document.updates["art_direction"] == "写实毛发质感"
    assert result.document.filenames == ["campaign.pdf", "reference.png"]
