from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DrawingFlags(BaseModel):
    has_notes: bool = False
    has_dims: bool = False
    has_summary: bool = False


class DrawingSummaryInfo(BaseModel):
    type: str
    title: Optional[str] = None
    length_chars: Optional[int] = None
    created_at: Optional[datetime] = None


class DrawingSummarySelection(BaseModel):
    selected_type: Optional[str] = None
    available_summaries: List[DrawingSummaryInfo] = Field(default_factory=list)


class DrawingSummary(BaseModel):
    type: str
    text: str
    created_at: Optional[datetime] = None


class DrawingContextInfo(BaseModel):
    source: str  # e.g., "dimensions", "notes", "json", "manual"
    token_count: int
    last_used_at: Optional[datetime] = None


class DrawingBase(BaseModel):
    document_id: str
    drawing_version_id: str
    filename: str
    ingest_timestamp: datetime
    thumbnail_url: str
    pdf_url: str
    png_url: str
    page_count: Optional[int] = None
    flags: DrawingFlags


class DrawingDetail(DrawingBase):
    metadata: dict = Field(default_factory=dict)  # arbitrary metadata from ingestion
    summary_selection: DrawingSummarySelection
    counts: dict = Field(
        default_factory=lambda: {
            "dimensions": 0,
            "notes": 0,
            "views": 0,
        }
    )
    contexts: List[DrawingContextInfo] = Field(default_factory=list)
    open_in_documents_url: str


class DrawingListResponse(BaseModel):
    items: List[DrawingBase]
    total: int
    page: int
    page_size: int


class DrawingFilterParams(BaseModel):
    customer_id: Optional[str] = None
    project_id: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 25
