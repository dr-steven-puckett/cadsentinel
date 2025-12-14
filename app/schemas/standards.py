from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StandardsUploadResponse(BaseModel):
    standard_id: UUID
    filename: str
    name: str
    summary: Optional[str] = None
    extracted_rules: dict[str, Any] = Field(default_factory=dict)
    embedding_stats: dict[str, Any] = Field(default_factory=dict)
    file_url: str


class StandardListItem(BaseModel):
    id: UUID
    name: str
    filename: str
    created_at: datetime
    summary: Optional[str] = None
    file_url: str

    model_config = {"from_attributes": True}


class StandardsListResponse(BaseModel):
    items: list[StandardListItem]
    total: int


class StandardDetailResponse(BaseModel):
    id: UUID
    name: str
    filename: str
    created_at: datetime
    updated_at: datetime
    storage_path: str
    summary: Optional[str] = None
    extracted_rules: dict[str, Any] = Field(default_factory=dict)
    embedding_stats: dict[str, Any] = Field(default_factory=dict)
    file_url: str

    model_config = {"from_attributes": True}
