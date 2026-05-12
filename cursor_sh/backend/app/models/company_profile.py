"""公司资料库模型 — 支持客户未注册前先 ingest 公司资料。"""

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class CompanyProfile(Base):
    """按公司名称归档的客户资料画像。"""
    __tablename__ = "company_profiles"

    id = Column(String(50), primary_key=True, index=True)
    company_key = Column(String(200), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False, index=True)
    profile_data = Column(JSON, default=dict)
    screen_resources = Column(JSON, default=list)
    documents = Column(JSON, default=list)
    notes = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CompanyProfile(company_name={self.company_name})>"


class CompanyProfileIngestJob(Base):
    """管理员上传公司资料后的后台解析任务。"""
    __tablename__ = "company_profile_ingest_jobs"

    id = Column(String(50), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    source = Column(String(80), default="company_profile_upload")
    status = Column(String(30), nullable=False, default="queued", index=True)
    error = Column(Text, default="")
    company_key = Column(String(200), default="", index=True)
    company_name = Column(String(255), default="", index=True)
    file_size = Column(String(40), default="")
    mime_type = Column(String(120), default="")
    page_count = Column(String(20), default="")
    text_chars = Column(String(20), default="")
    result = Column(JSON, default=dict)

    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CompanyProfileIngestJob(filename={self.filename}, status={self.status})>"


class CompanyLibraryDocument(Base):
    """公司资料库中的单份资料资产。"""
    __tablename__ = "company_library_documents"

    id = Column(String(50), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    source = Column(String(80), default="company_profile_upload")
    status = Column(String(30), nullable=False, default="queued", index=True)
    error = Column(Text, default="")
    company_key = Column(String(200), default="", index=True)
    company_name = Column(String(255), default="", index=True)
    file_size = Column(String(40), default="")
    mime_type = Column(String(120), default="")
    page_count = Column(String(20), default="")
    text_chars = Column(String(20), default="")
    raw_file = Column(JSON, default=dict)
    extracted_text = Column(JSON, default=dict)
    structured_memory = Column(JSON, default=dict)
    text_preview = Column(Text, default="")
    notes = Column(Text, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CompanyLibraryDocument(filename={self.filename}, status={self.status})>"
