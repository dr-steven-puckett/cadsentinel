# app/api/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional,Any, Dict, List, Optional

from pydantic import BaseModel, Field

LogLevel = Literal["info", "warning", "error"]


class PipelineEvent(BaseModel):
    """
    One user-facing pipeline event/log message to show in the UI.
    These will eventually drive a scrolling log window in Vercel.
    """
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this event occurred (UTC).",
    )
    level: LogLevel = Field(
        default="info",
        description="Severity level: info, warning, or error.",
    )
    step: str = Field(
        ...,
        description="Logical pipeline step name (e.g., 'dwg_to_dxf', 'render_png').",
    )
    message: str = Field(
        ...,
        description="Human-readable message for the UI."
    )


class IngestArtifacts(BaseModel):
    """
    Paths or URLs for all artifacts. For now we use local paths;
    later the frontend can map these to signed URLs, etc.
    """
    dwg_path: Optional[str] = None
    dxf_path: Optional[str] = None
    pdf_path: Optional[str] = None
    png_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    json_path: Optional[str] = None


class IngestResponse(BaseModel):
    """
    Standard response for /ingest/dwg that the frontend can use
    to show overall status AND a scrolling pipeline log.
    """
    success: bool = Field(
        ...,
        description="True if ingestion finished without a fatal error."
    )
    document_id: Optional[str] = Field(
        None,
        description="SHA256 document_id for this DWG, if known.",
    )
    message: str = Field(
        ...,
        description="Top-level success or error message.",
    )
    events: list[PipelineEvent] = Field(
        default_factory=list,
        description="Timeline of pipeline events for the UI."
    )
    artifacts: Optional[IngestArtifacts] = Field(
        None,
        description="Locations of created artifacts (if any).",
    )

class TitleBlockSummary(BaseModel):
    part_name: Optional[str] = None
    drawing_number: Optional[str] = None
    revision: Optional[str] = None
    scale: Optional[str] = None
    units: Optional[str] = None
    projection: Optional[str] = None
    material: Optional[str] = None
    standard_references: List[str] = []  # <-- list, not string


class SummarizeDrawingRequest(BaseModel):
    document_id: str = Field(..., description="Stable SHA256 document ID for the drawing")
    json_path: str = Field(..., description="Filesystem path to the DWG→JSON file")
    pdf_path: str = Field(..., description="Filesystem path to the DXF→PDF file")

class SummarizeDrawingResponse(BaseModel):
    document_id: str
    structured_summary: DrawingStructuredSummary
    long_form_description: str
    raw_model_output: Optional[str] = Field(
        None, description="Raw LLM response text (for debugging/inspection)."
    )

class DrawingStructuredSummary(BaseModel):
    drawing_id: str
    title_block: TitleBlockSummary  # <-- use the new submodel
    part_type: Optional[str] = None
    overall_description: Optional[str] = None
    key_features: List[str] = []
    critical_dimensions: List[str] = []
    gdandt_summary: List[str] = []
    manufacturing_notes: List[str] = []
    known_gaps_or_ambiguities: List[str] = []

