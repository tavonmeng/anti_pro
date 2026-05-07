"""Schemas for homepage marketing bar configuration."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HomepageBarUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    button_text: Optional[str] = Field(None, max_length=60)
    pdf_url: Optional[str] = None
    pdf_name: Optional[str] = Field(None, max_length=255)
    pdf_object_key: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = None
    image_object_key: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class HomepageBarResponse(BaseModel):
    id: str
    title: str
    button_text: str
    pdf_url: Optional[str] = None
    pdf_name: Optional[str] = None
    pdf_object_key: Optional[str] = None
    image_url: Optional[str] = None
    image_object_key: Optional[str] = None
    is_active: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
