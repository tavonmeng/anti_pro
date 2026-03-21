"""文件模型"""

from sqlalchemy import Column, String, BigInteger, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class FileType(str, enum.Enum):
    """文件类型枚举"""
    SCENE_PHOTO = "scene_photo"    # 现场照片
    MATERIAL = "material"          # 素材文件
    PREVIEW = "preview"            # 预览文件


class File(Base):
    """文件模型"""
    __tablename__ = "files"
    
    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    file_type = Column(Enum(FileType), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系（使用 selectin 加载策略，兼容异步上下文）
    order = relationship("Order", back_populates="files", lazy="selectin")
    
    def __repr__(self):
        return f"<File(id={self.id}, name={self.name}, type={self.file_type})>"

