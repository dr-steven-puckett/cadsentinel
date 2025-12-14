from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    contact_info: Optional[str] = Field(default=None, max_length=1024)


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    code: Optional[str] = Field(default=None, max_length=64)
    contact_info: Optional[str] = Field(default=None, max_length=1024)
    active: Optional[bool] = None


class CustomerItem(BaseModel):
    id: UUID
    name: str
    code: Optional[str] = None
    contact_info: Optional[str] = None
    created_at: datetime
    active: bool

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: list[CustomerItem]
    total: int
