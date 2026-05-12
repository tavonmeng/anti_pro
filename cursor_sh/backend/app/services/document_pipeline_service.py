"""客户资料处理 Pipeline。"""

import os
import tempfile
import uuid
from datetime import datetime
from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models.customer_document import CustomerDocument, CustomerDocumentExtraction
from app.services.document_parser_service import parse_document, build_llm_text
from app.services.document_extract_service import extract_customer_knowledge, empty_extraction
from app.services.memory_service import get_or_create_memory
from app.services.memory_merge_service import merge_document_knowledge


async def process_document(document_id: str):
    """解析资料、抽取客户知识，并生成待审核结果。"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerDocument).where(CustomerDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return
        document.status = "processing"
        document.processing_error = None
        await session.commit()

    extracted = empty_extraction()
    summary = ""
    error = None
    temp_file_path = None
    try:
        parse_file_path = _prepare_parse_file(document)
        if parse_file_path != document.file_path:
            temp_file_path = parse_file_path
        sections = parse_document(parse_file_path, document.original_filename)
        document_text = build_llm_text(sections)
        if not document_text.strip():
            raise ValueError("资料没有可提取文本，可能是扫描件或图片版文件")
        extracted = await extract_customer_knowledge(document_text, document.original_filename)
        summary = _build_summary(extracted)
    except Exception as exc:
        error = str(exc)
        summary = "抽取失败，已生成空白审核模板，可由管理员手动填写。"
        print(f"[DocumentPipeline] 处理失败 document={document_id}: {exc}")
    finally:
        if temp_file_path:
            try:
                os.remove(temp_file_path)
            except OSError:
                pass

    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerDocument).where(CustomerDocument.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return
        document.status = "pending_review"
        document.processing_error = error

        result = await session.execute(
            select(CustomerDocumentExtraction).where(CustomerDocumentExtraction.document_id == document_id)
        )
        extraction = result.scalar_one_or_none()
        if not extraction:
            extraction = CustomerDocumentExtraction(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=document.user_id,
            )
            session.add(extraction)

        extraction.extracted_data = extracted
        extraction.reviewed_data = extracted
        extraction.status = "pending_review"
        extraction.summary = summary
        extraction.review_note = None
        await session.commit()


async def approve_document_extraction(document_id: str, reviewed_data: dict, admin_id: str = "") -> dict:
    """审核通过并写入 UserMemory。"""
    async with async_session_maker() as session:
        doc_result = await session.execute(
            select(CustomerDocument).where(CustomerDocument.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise ValueError("资料不存在")

        ext_result = await session.execute(
            select(CustomerDocumentExtraction).where(CustomerDocumentExtraction.document_id == document_id)
        )
        extraction = ext_result.scalar_one_or_none()
        if not extraction:
            extraction = CustomerDocumentExtraction(
                id=str(uuid.uuid4()),
                document_id=document.id,
                user_id=document.user_id,
                extracted_data=empty_extraction(),
            )
            session.add(extraction)

        memory = await get_or_create_memory(document.user_id, db=session)
        updates = merge_document_knowledge(
            memory,
            reviewed_data,
            {
                "document_id": document.id,
                "filename": document.original_filename,
            },
        )
        for key, value in updates.items():
            setattr(memory, key, value)

        document.status = "approved"
        extraction.status = "approved"
        extraction.reviewed_data = reviewed_data
        extraction.reviewed_by = admin_id
        extraction.reviewed_at = datetime.now()
        extraction.summary = _build_summary(reviewed_data)
        await session.commit()

        return {
            "document_id": document.id,
            "memory_updated": True,
            "summary": extraction.summary,
        }


def _build_summary(data: dict) -> str:
    company = data.get("company_info") or {}
    screens = data.get("screen_resources") or []
    cases = data.get("past_cases") or []
    notes = data.get("important_notes") or []
    parts = []
    if company.get("description"):
        parts.append("公司介绍 1 条")
    if screens:
        parts.append(f"屏幕资源 {len(screens)} 条")
    if cases:
        parts.append(f"案例 {len(cases)} 条")
    if notes:
        parts.append(f"重要备注 {len(notes)} 条")
    return "，".join(parts) if parts else "未抽取到结构化信息，可手动填写。"


def _prepare_parse_file(document: CustomerDocument) -> str:
    """获取可供解析的本地文件路径。

    生产 OSS 模式下，原文件只长期保存在 OSS；这里下载到临时文件，解析后删除。
    """
    if settings.OSS_ENABLED:
        if not document.object_key:
            raise FileNotFoundError("资料缺少 OSS object_key，无法解析")
        suffix = "." + (document.file_type or "tmp").lstrip(".")
        fd, temp_path = tempfile.mkstemp(prefix="customer_doc_", suffix=suffix)
        os.close(fd)
        from app.services.oss_service import download_object_to_file
        download_object_to_file(document.object_key, temp_path)
        return temp_path

    if not document.file_path or not os.path.exists(document.file_path):
        raise FileNotFoundError("资料文件不存在，无法解析")
    return document.file_path
