# app/api/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, Any, Dict, List
import typing as t

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared / Pipeline Schemas
# ---------------------------------------------------------------------------

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
        description="Human-readable message for the UI.",
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
        description="True if ingestion finished without a fatal error.",
    )
    document_id: Optional[str] = Field(
        None,
        description="SHA256 document_id for this DWG, if known.",
    )
    message: str = Field(
        ...,
        description="Top-level success or error message.",
    )
    events: List[PipelineEvent] = Field(
        default_factory=list,
        description="Timeline of pipeline events for the UI.",
    )
    artifacts: Optional[IngestArtifacts] = Field(
        None,
        description="Locations of created artifacts (if any).",
    )


# ---------------------------------------------------------------------------
# Drawing Summarization Schemas
# ---------------------------------------------------------------------------

class TitleBlockSummary(BaseModel):
    part_name: Optional[str] = None
    drawing_number: Optional[str] = None
    revision: Optional[str] = None
    scale: Optional[str] = None
    units: Optional[str] = None
    projection: Optional[str] = None
    material: Optional[str] = None
    standard_references: List[str] = []  # list of standard references


class DrawingStructuredSummary(BaseModel):
    drawing_id: str
    title_block: TitleBlockSummary
    part_type: Optional[str] = None
    overall_description: Optional[str] = None
    views: List[str] = []
    key_features: List[str] = []
    critical_dimensions: List[str] = []
    gdandt_summary: List[str] = []
    manufacturing_notes: List[str] = []
    known_gaps_or_ambiguities: List[str] = []


class SummarizeDrawingRequest(BaseModel):
    document_id: str = Field(..., description="Stable SHA256 document ID for the drawing")
    json_path: str = Field(..., description="Filesystem path to the DWG→JSON file")
    pdf_path: str = Field(..., description="Filesystem path to the DXF→PDF file")


class SummarizeDrawingResponse(BaseModel):
    document_id: str
    structured_summary: DrawingStructuredSummary
    long_form_description: str
    raw_model_output: Optional[str] = Field(
        None,
        description="Raw LLM response text (for debugging/inspection).",
    )


# ---------------------------------------------------------------------------
# Retrieval / Search Schemas (for /search/vector and /search/hybrid)
# ---------------------------------------------------------------------------

class ChunkSearchFilters(BaseModel):
    """
    Optional filters for narrowing vector/hybrid search.
    - drawing_version_id: only search within a specific version
    - source_types: list of embedding.source_type values
      e.g. ["summary", "note", "dimension"]
    """
    drawing_version_id: int | None = None
    source_types: List[str] | None = None


class VectorSearchRequest(BaseModel):
    """
    Request body for POST /search/vector
    """
    query_text: str = Field(..., min_length=1)
    filters: ChunkSearchFilters | None = None
    top_k: int = Field(20, ge=1, le=200)
    score_threshold: float | None = Field(
        None,
        description="Filter out matches below this score (0..1).",
        ge=-1.0,
        le=1.0,
    )


class HybridSearchRequest(BaseModel):
    """
    Request body for POST /search/hybrid

    alpha controls fusion:
        fused = alpha * vector_score + (1 - alpha) * keyword_score
    """
    query_text: str = Field(..., min_length=1)
    filters: ChunkSearchFilters | None = None
    top_k: int = Field(20, ge=1, le=200)
    score_threshold: float | None = Field(
        None,
        description="Filter on fused score (0..1).",
        ge=-1.0,
        le=1.0,
    )
    alpha: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Weight for vector vs keyword similarity (alpha * vector + (1-alpha) * keyword).",
    )


class ChunkSearchResult(BaseModel):
    """
    Single hit returned from vector/hybrid search.

    - id: embeddings.id
    - source_type: embeddings.source_type (e.g., 'note', 'dimension', 'summary')
    - source_ref_id: the linked Dimension/Note/Summary id (if available)
    - geometry_index: geometry + json_index info so the UI can highlight it
    - thumbnail_url: quick drawing preview
    """
    id: int
    matched_text: str
    source_type: str
    drawing_version_id: int
    source_ref_id: int | None = None

    similarity_score: float
    thumbnail_url: str | None = None

    geometry_index: Dict[str, Any] | None = None
    metadata: Dict[str, Any] | None = None


class ChunkSearchResponse(BaseModel):
    """
    Response envelope for vector/hybrid search.
    """
    results: List[ChunkSearchResult]
    total_returned: int
    mode: t.Literal["vector", "hybrid"]

# ---------------------------------------------------------------------------
# Chat-with-the-drawing Schemas
# ---------------------------------------------------------------------------

class RetrievedContextItem(BaseModel):
    """
    One retrieved chunk (summary, note, dimension) used as context for chat.
    Also used so the UI can highlight / deep-link the source.
    """
    chunk_id: int
    source_type: str
    drawing_version_id: int
    source_ref_id: int | None = None

    matched_text: str
    similarity_score: float

    geometry_index: Dict[str, Any] | None = None
    thumbnail_url: str | None = None


class ChatDrawingRequest(BaseModel):
    """
    Request body for POST /chat/drawing.
    You can supply either drawing_version_id directly or a document_id hash
    (then we resolve to the latest version).
    """
    user_message: str = Field(..., description="User's question about the drawing.")

    document_id: str | None = Field(
        None,
        description="Stable DWG document hash. If provided, server will resolve to a drawing_version_id.",
    )
    drawing_version_id: int | None = Field(
        None,
        description="Specific drawing version to chat with.",
    )

    max_summary_chunks: int = Field(3, ge=0, le=20)
    max_note_chunks: int = Field(8, ge=0, le=50)
    max_dimension_chunks: int = Field(12, ge=0, le=100)


class ChatDrawingResponse(BaseModel):
    """
    Response from POST /chat/drawing.
    Contains the assistant's reply plus backreferences to retrieved chunks.
    """
    assistant_reply: str
    drawing_version_id: int
    document_id: str | None = None

    contexts: List[RetrievedContextItem] = Field(
        default_factory=list,
        description="Chunks (summaries, notes, dimensions) used as context.",
    )

    open_in_documents_url: str | None = Field(
        None,
        description="Deep link for the frontend Documents tab, e.g. /documents/{drawing_version_id}.",
    )
