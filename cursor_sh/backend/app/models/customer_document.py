"""客户资料模型 — 用于 Agent Memory 知识导入"""

from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, ForeignKey
from app.database import Base
from app.utils.timezone import beijing_now


class CustomerDocument(Base):
    """管理员上传的客户资料文件。"""

    __tablename__ = "customer_documents"

    id = Column(String(50), primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_path = Column(String(500))
    file_url = Column(String(500))
    object_key = Column(String(500))
    size = Column(Integer, default=0)
    mime_type = Column(String(100))
    status = Column(String(30), default="uploaded", index=True)
    processing_error = Column(Text)
    uploaded_by = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)

    def __repr__(self):
        return f"<CustomerDocument(id={self.id}, user_id={self.user_id}, filename={self.original_filename})>"


class CustomerDocumentExtraction(Base):
    """客户资料抽取结果与审核结果。"""

    __tablename__ = "customer_document_extractions"

    id = Column(String(50), primary_key=True, index=True)
    document_id = Column(String(50), ForeignKey("customer_documents.id"), nullable=False, unique=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    extracted_data = Column(JSON, default=dict)
    reviewed_data = Column(JSON, default=dict)
    status = Column(String(30), default="pending_review", index=True)
    summary = Column(Text)
    review_note = Column(Text)
    reviewed_by = Column(String(50))
    reviewed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=beijing_now)
    updated_at = Column(DateTime(timezone=True), default=beijing_now, onupdate=beijing_now)

    def __repr__(self):
        return f"<CustomerDocumentExtraction(document_id={self.document_id}, status={self.status})>"
