from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AnnouncementCreate(BaseModel):
    title: str = Field(..., max_length=200, description="公告标题")
    content: str = Field(..., description="公告内容")
    is_active: bool = Field(True, description="是否发布展示")

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="公告标题")
    content: Optional[str] = Field(None, description="公告内容")
    is_active: Optional[bool] = Field(None, description="是否发布展示")

class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        from_attributes = True
