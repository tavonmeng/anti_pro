"""Shared uploaded-material understanding for creative sub-agents."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.services.ai_brief_document_service import (
    BriefDocumentExtraction,
    extract_uploaded_brief_documents,
    merge_brief_material_extraction,
)
from app.services.ai_image_understanding import (
    ImageUnderstandingResult,
    UploadedAttachment,
    append_image_context_to_message,
    understand_uploaded_images,
)


@dataclass
class UploadedMaterialContext:
    message: str
    image: ImageUnderstandingResult = field(default_factory=ImageUnderstandingResult)
    document: BriefDocumentExtraction = field(default_factory=BriefDocumentExtraction)


async def enrich_message_with_uploaded_materials(
    *,
    message: str,
    attachments: list[UploadedAttachment] | None,
    user_id: str,
) -> UploadedMaterialContext:
    """Understand images and PDF/DOC/DOCX files, then append grounded context."""
    if not attachments:
        return UploadedMaterialContext(message=message)

    image_task = understand_uploaded_images(message=message, attachments=attachments)
    if user_id:
        document_task = extract_uploaded_brief_documents(attachments, user_id=user_id)
        image_result, document = await asyncio.gather(image_task, document_task)
    else:
        image_result = await image_task
        document = BriefDocumentExtraction()

    if image_result.brief_updates:
        merge_brief_material_extraction(
            document,
            image_result.brief_updates,
            filenames=image_result.brief_filenames,
        )

    enriched_message = append_image_context_to_message(message, image_result.context)
    if document.context:
        enriched_message = f"{enriched_message}\n\n{document.context}".strip()

    return UploadedMaterialContext(
        message=enriched_message,
        image=image_result,
        document=document,
    )
