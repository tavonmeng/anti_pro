"""客户资料导入 — 管理员 API。

管理员上传客户资料，Pipeline 抽取客户知识，审核后写入 Agent Memory。
"""

import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.customer_document import CustomerDocument, CustomerDocumentExtraction
from app.models.user import User
from app.models.user_memory import UserMemory
from app.utils.dependencies import require_admin
from app.services.document_extract_service import empty_extraction
from app.services.document_pipeline_service import process_document, approve_document_extraction
from app.services.memory_sanitizer import sanitize_document_memory_data
from app.utils.timezone import beijing_iso, beijing_now

router = APIRouter(prefix="/admin/documents", tags=["管理员 — 客户资料导入"])

ALLOWED_EXT = {".pdf", ".docx", ".pptx"}
UPLOAD_CHUNK_SIZE = 1024 * 1024
MAX_SIZE = 200 * 1024 * 1024
MAX_SIZE_MESSAGE = "文件大小不能超过200MB"


class ApproveRequest(BaseModel):
    reviewed_data: dict


@router.get("/user/{user_id}")
async def list_customer_documents(
    user_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取某个客户的资料列表。"""
    result = await db.execute(
        select(CustomerDocument)
        .where(CustomerDocument.user_id == user_id)
        .order_by(desc(CustomerDocument.created_at))
    )
    docs = result.scalars().all()
    return {"code": 200, "data": [await _serialize_document(db, doc) for doc in docs]}


@router.get("/{document_id}")
async def get_customer_document(
    document_id: str,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取资料详情和抽取结果。"""
    doc = await _get_document_or_404(db, document_id)
    return {"code": 200, "data": await _serialize_document(db, doc)}


@router.post("/{user_id}/upload")
async def upload_customer_document(
    user_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传客户资料，并触发后台抽取。"""
    if not await _customer_exists(db, user_id):
        raise HTTPException(status_code=404, detail="客户不存在")

    original_filename = os.path.basename(file.filename or "customer_document")
    ext = os.path.splitext(original_filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 PDF / Word(docx) / PPT(pptx)")

    tmp_path, size = await _stream_upload_to_temp(file, MAX_SIZE, MAX_SIZE_MESSAGE)
    doc_id = str(uuid.uuid4())
    safe_original = _safe_filename(original_filename)
    stored_filename = f"{beijing_now().strftime('%Y%m%d_%H%M%S')}_{doc_id[:8]}_{safe_original}"
    file_path = None
    file_url = ""
    object_key = ""
    try:
        if settings.OSS_ENABLED:
            from app.services.oss_service import upload_file
            object_key = f"customer_documents/{user_id}/{stored_filename}"
            upload_file(object_key, tmp_path, file.content_type or "")
            file_url = object_key
            _cleanup_temp_file(tmp_path)
        else:
            upload_dir = os.path.join(settings.UPLOAD_DIR, "customer_documents", user_id)
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, stored_filename)
            os.replace(tmp_path, file_path)
            file_url = f"/uploads/customer_documents/{user_id}/{stored_filename}"
    except HTTPException:
        _cleanup_temp_file(tmp_path)
        raise
    except Exception as exc:
        _cleanup_temp_file(tmp_path)
        raise HTTPException(status_code=500, detail="资料上传失败，请稍后重试") from exc

    document = CustomerDocument(
        id=doc_id,
        user_id=user_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_type=ext.lstrip("."),
        file_path=file_path,
        file_url=file_url,
        object_key=object_key,
        size=size,
        mime_type=file.content_type or "",
        status="uploaded",
        uploaded_by=getattr(current_admin, "id", ""),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    background_tasks.add_task(process_document, document.id)
    return {"code": 200, "data": await _serialize_document(db, document), "message": "资料已上传，正在抽取客户知识"}


@router.post("/{document_id}/reprocess")
async def reprocess_customer_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重新处理客户资料。"""
    document = await _get_document_or_404(db, document_id)
    document.status = "uploaded"
    document.processing_error = None
    await db.commit()
    background_tasks.add_task(process_document, document.id)
    return {"code": 200, "data": await _serialize_document(db, document), "message": "已重新触发资料抽取"}


@router.post("/{document_id}/approve")
async def approve_customer_document(
    document_id: str,
    request: ApproveRequest,
    current_admin=Depends(require_admin),
):
    """审核通过，将资料抽取结果写入 UserMemory。"""
    try:
        result = await approve_document_extraction(
            document_id=document_id,
            reviewed_data=request.reviewed_data or empty_extraction(),
            admin_id=getattr(current_admin, "id", ""),
        )
        return {"code": 200, "data": result, "message": "已写入客户 Memory"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="写入 Memory 失败，请稍后重试") from exc


async def _get_document_or_404(db: AsyncSession, document_id: str) -> CustomerDocument:
    result = await db.execute(
        select(CustomerDocument).where(CustomerDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="资料不存在")
    return doc


async def _customer_exists(db: AsyncSession, user_id: str) -> bool:
    user_result = await db.execute(select(User.id).where(User.id == user_id))
    if user_result.scalar_one_or_none():
        return True

    memory_result = await db.execute(select(UserMemory.id).where(UserMemory.user_id == user_id))
    return memory_result.scalar_one_or_none() is not None


async def _stream_upload_to_temp(file: UploadFile, max_size: int, limit_message: str) -> tuple[str, int]:
    """将上传文件分块写入临时文件，并在读取过程中做大小限制。"""
    tmp_dir = os.path.join(settings.UPLOAD_DIR, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}{ext}.part")
    size = 0

    try:
        async with aiofiles.open(tmp_path, "wb") as out:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size:
                    raise HTTPException(status_code=413, detail=limit_message)
                await out.write(chunk)
        return tmp_path, size
    except Exception:
        _cleanup_temp_file(tmp_path)
        raise


def _cleanup_temp_file(tmp_path: str):
    if not tmp_path:
        return
    try:
        os.remove(tmp_path)
    except OSError:
        pass


async def _serialize_document(db: AsyncSession, doc: CustomerDocument) -> dict:
    result = await db.execute(
        select(CustomerDocumentExtraction).where(CustomerDocumentExtraction.document_id == doc.id)
    )
    extraction = result.scalar_one_or_none()
    extracted_data = sanitize_document_memory_data(extraction.extracted_data or empty_extraction()) if extraction else None
    reviewed_data = sanitize_document_memory_data(
        extraction.reviewed_data or extraction.extracted_data or empty_extraction()
    ) if extraction else None

    return {
        "id": doc.id,
        "user_id": doc.user_id,
        "original_filename": doc.original_filename,
        "stored_filename": doc.stored_filename,
        "file_type": doc.file_type,
        "file_url": _document_file_url(doc),
        "object_key": doc.object_key,
        "size": doc.size,
        "mime_type": doc.mime_type,
        "status": doc.status,
        "processing_error": doc.processing_error,
        "uploaded_by": doc.uploaded_by,
        "created_at": beijing_iso(doc.created_at),
        "updated_at": beijing_iso(doc.updated_at),
        "extraction": {
            "id": extraction.id,
            "status": extraction.status,
            "summary": extraction.summary,
            "extracted_data": extracted_data or empty_extraction(),
            "reviewed_data": reviewed_data or empty_extraction(),
            "reviewed_by": extraction.reviewed_by,
            "reviewed_at": beijing_iso(extraction.reviewed_at),
        } if extraction else None,
    }


def _safe_filename(filename: str) -> str:
    filename = filename.replace("/", "_").replace("\\", "_").strip()
    return "".join(ch if ch.isalnum() or ch in "._-()（）[]【】 " else "_" for ch in filename)[:160]


def _document_file_url(doc: CustomerDocument) -> str:
    if settings.OSS_ENABLED and doc.object_key:
        try:
            from app.services.oss_service import get_signed_url
            return get_signed_url(doc.object_key, expires=3600)
        except Exception:
            return doc.object_key
    if settings.OSS_ENABLED and doc.file_url:
        try:
            from app.services.oss_service import maybe_sign_url
            return maybe_sign_url(doc.file_url, expires=3600)
        except Exception:
            return doc.file_url
    return doc.file_url or ""
