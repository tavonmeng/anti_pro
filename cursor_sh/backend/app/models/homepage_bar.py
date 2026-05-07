"""Homepage marketing bar configuration."""

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.sql import func
from app.database import Base


class HomepageBar(Base):
    """Single configurable marketing bar shown on the public homepage."""

    __tablename__ = "homepage_bars"

    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    button_text = Column(String(60), nullable=False, default="下载 PDF")
    pdf_url = Column(String(800), nullable=True)
    pdf_name = Column(String(255), nullable=True)
    pdf_object_key = Column(String(500), nullable=True)
    image_url = Column(String(800), nullable=True)
    image_object_key = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<HomepageBar(id={self.id}, active={self.is_active})>"
